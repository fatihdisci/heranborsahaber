import contextlib, json, sqlite3, time, uuid, os
from pathlib import Path


def uid(): return uuid.uuid4().hex

def encode(value): return json.dumps(value, ensure_ascii=False, sort_keys=True)

class DB:
    def __init__(self, path):
        self.path = Path(path).resolve()
        if self.path.name!='habnews.sqlite' or any(x in self.path.parts for x in ('.hermes','.codex','.ssh','heranborsacode')):raise ValueError('database_namespace_denied')
        existed=self.path.exists() and self.path.stat().st_size>0
        if existed:
            probe=sqlite3.connect('file:'+str(self.path)+'?mode=ro',uri=True)
            marker=probe.execute('PRAGMA application_id').fetchone()[0];probe.close()
            if marker!=0x4841424E:raise ValueError('not_a_habnews_database')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.conn = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA application_id='+str(0x4841424E))
        self.conn.executescript(Path(__file__).with_name('migration.sql').read_text())
        self.path.chmod(0o600)
    @contextlib.contextmanager
    def transaction(self):
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            yield self.conn
            self.conn.execute('COMMIT')
        except BaseException:
            self.conn.execute('ROLLBACK'); raise
    def state(self, key, default=None):
        row = self.conn.execute('SELECT value FROM habnews_runtime_state WHERE key=?',(key,)).fetchone()
        return row[0] if row else default
    def set_state(self, key, value):
        self.conn.execute('INSERT INTO habnews_runtime_state VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value)))
        if key=='enabled' and os.getenv('HABNEWS_SWITCH_FILE'):
            switch=Path(os.environ['HABNEWS_SWITCH_FILE'])
            if switch!=Path('/control/runtime-state.json'):raise ValueError('switch_namespace')
            temp=switch.with_suffix('.tmp-'+uid());temp.write_text(encode({'enabled':str(value)=='true','updated_at':time.time()}));temp.chmod(0o600);temp.replace(switch)
    def enabled(self): return self.state('enabled') == 'true'
    def require_enabled(self):
        if not self.enabled(): raise RuntimeError('paused')
    def audit(self, kind, subject, metadata=None):
        self.conn.execute('INSERT INTO habnews_audit(created,kind,subject,metadata) VALUES(?,?,?,?)',(time.time(),kind,subject,encode(metadata or {})))
    def incident(self, key, reason):
        self.conn.execute("INSERT INTO habnews_incident VALUES(?,'open',?,?,NULL) ON CONFLICT(id) DO UPDATE SET status='open',recovered=NULL,reason=excluded.reason WHERE habnews_incident.status='recovered'",(key,reason,time.time()))
    def recover(self, key):
        self.conn.execute("UPDATE habnews_incident SET status='recovered',recovered=? WHERE id=? AND status='open'",(time.time(),key))
    def enqueue(self, kind, identity, payload):
        self.conn.execute('INSERT OR IGNORE INTO habnews_queue(id,kind,identity,payload,next_at,created) VALUES(?,?,?,?,?,?)',(uid(),kind,identity,encode(payload),time.time(),time.time()))
    def claim(self, kind, now=None, ttl=200):
        now = now or time.time()
        with self.transaction() as c:
            # LLM started/uncertain jobs are never blindly retried after crash.
            c.execute("UPDATE habnews_queue SET status=CASE WHEN kind='llm' THEN 'uncertain' ELSE 'pending' END,lease=NULL WHERE status='leased' AND lease_until<?",(now,))
            row = c.execute("SELECT * FROM habnews_queue WHERE kind=? AND status='pending' AND next_at<=? ORDER BY created LIMIT 1",(kind,now)).fetchone()
            if not row: return None
            token = uid()
            c.execute("UPDATE habnews_queue SET status='leased',lease=?,lease_until=?,attempts=attempts+1 WHERE id=?",(token,now+ttl,row['id']))
            return dict(row) | {'lease':token,'attempts':row['attempts']+1}
    def finish(self, row, status='done', retry_after=0):
        updated = self.conn.execute('UPDATE habnews_queue SET status=?,next_at=?,lease=NULL,lease_until=NULL WHERE id=? AND lease=?',(status,time.time()+retry_after,row['id'],row['lease']))
        if updated.rowcount != 1: raise RuntimeError('lost_lease')
    def backup(self, target):
        dest = sqlite3.connect(target)
        self.conn.backup(dest); dest.close(); Path(target).chmod(0o600)
    def health(self):
        return {'enabled':self.enabled(),'llm_state':self.state('llm_state'),'real_account_quota':'bilinmiyor',
                'queues':[dict(r) for r in self.conn.execute('SELECT kind,status,count(*) AS count FROM habnews_queue GROUP BY kind,status')],
                'delivery':[dict(r) for r in self.conn.execute('SELECT status,count(*) AS count FROM habnews_outbox GROUP BY status')],
                'sources':[dict(r) for r in self.conn.execute('SELECT id,health,last_success,failures FROM habnews_source')],
                'incidents':[dict(r) for r in self.conn.execute("SELECT id,reason FROM habnews_incident WHERE status='open'")]}
