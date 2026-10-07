"""Explicit operator-only private Telegram acceptance. No collector/model call.
Run while habnews is paused. Fixture label is visible in both draft and card.
"""
import json,sys,time
from pathlib import Path
sys.path.insert(0,'/app')
from habnews.db import DB,uid,encode
from habnews.normalizer import digest
from habnews.approval import Approval
from habnews.telegram import Telegram
if not Path('/.dockerenv').exists():raise SystemExit('New isolated approval container required')
db=DB('/data/habnews.sqlite')
if db.enabled():raise SystemExit('Pause habnews before acceptance fixture')
config=json.loads(Path('/run/secrets/telegram.json').read_text());tg=Telegram(config['token']);tg.preflight(config['bot_id'])
eid='TEST'+uid();ev='TEST'+uid();now=time.time();sentence='TEST: TCMB politika faizini yüzde 40 olarak belirledi; bu sentetik testtir, gerçek haber değildir.'
item={'title':'TEST TCMB politika faizi','summary':sentence,'url':'https://fixture.invalid/test','published_at':now,'time_precision':'second','first_seen_at':now}
with db.transaction() as c:
    c.execute('INSERT INTO habnews_event VALUES(?,?,?,?,?,?,?)',(eid,eid,1,'verification_pending','P0',now,now))
    c.execute('INSERT INTO habnews_event_version VALUES(?,?,?,?,?)',(eid,1,digest(sentence),encode(item),now))
    c.execute('INSERT INTO habnews_evidence VALUES(?,?,?,?,?,?,?,?,?,?,0)',(ev,eid,1,'TEST','TEST',1,item['url'],sentence,digest(sentence),now))
fact={'text':sentence,'source_ref':ev,'value_raw':'40','normalized_value':40,'unit':'yüzde','currency':None,'scale':None,'period':None,'scope':'politika','stage':'belirledi','actor':'TCMB','quote':None}
result={'schema_version':'habnews-v1','event_id':eid,'event_version':1,'relevance_reason':'TEST / SENTETİK — kaynak, teyit ve model sonucu simülasyondur; gerçek haber değildir.','priority':'P0','verification_state':'official_primary','facts':[fact],'ambiguities':[],'headline':'TEST TCMB politika faizi','proposed_body':'TEST TCMB politika faizi\n\n'+sentence,'verified_tags':[],'image_candidates':[]}
metadata={'requested_model':'gpt-6-luna','provider':'openai-codex','transport':'codex_responses','auth_source':'habnews_own_oauth','speed':'standard','server_model':None,'fixture':True,'real_llm_called':False}
class TestStore:
    # Only this explicitly invoked script can deliver a labelled admin test while paused.
    def require_enabled(self):pass
    def __getattr__(self,name):return getattr(db,name)
did=Approval(TestStore(),config['user_id'],config['chat_id']).create({'event_id':eid,'event_version':1,'evidence_refs':[ev]},result,metadata)
for row in db.conn.execute('SELECT * FROM habnews_outbox WHERE draft_id=? ORDER BY part',(did,)).fetchall():
    db.conn.execute("UPDATE habnews_outbox SET status='uncertain' WHERE id=?",(row['id'],))
    sent=tg.call(row['method'],json.loads(row['payload']))
    with db.transaction() as c:
        c.execute("UPDATE habnews_outbox SET status='sent',message_id=? WHERE id=?",(sent['message_id'],row['id']))
        if 'reply_markup' in json.loads(row['payload']):c.execute('UPDATE habnews_callback SET message_id=? WHERE draft_id=?',(sent['message_id'],did))
db.set_state('acceptance_test_draft',did);db.audit('explicit_labelled_test',did,{'real_llm_called':False})
print('TEST paketi yalnız yeni botun sahibine gönderildi. Kartı onaylayarak callback kabulünü tamamlayın. Gerçek model smoke ayrı zorunludur.')
