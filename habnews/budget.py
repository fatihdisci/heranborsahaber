import time,os
from datetime import datetime
from zoneinfo import ZoneInfo
from .db import uid,encode

class Budget:
    def __init__(self,db,daily=None,reserve_p0=None):
        self.db=db;self.daily=daily if daily is not None else int(os.getenv('HABNEWS_DAILY_LLM_REQUESTS','60'));self.reserve_p0=reserve_p0 if reserve_p0 is not None else int(os.getenv('HABNEWS_P0_CALL_RESERVE','6'))
        if self.daily<1 or not 0<=self.reserve_p0<self.daily:raise ValueError('budget_policy')
    def reserve(self,event_id,priority,requests=1):
        day=datetime.now(ZoneInfo('Europe/Istanbul')).date().isoformat()
        with self.db.transaction() as c:
            active=c.execute("SELECT count(*) FROM habnews_budget WHERE kind='llm' AND status='reserved'").fetchone()[0]
            if active: raise RuntimeError('llm_concurrency_limit')
            used=c.execute("SELECT coalesce(sum(reserved),0) FROM habnews_budget WHERE kind='llm' AND day=?",(day,)).fetchone()[0]
            event_used=c.execute("SELECT coalesce(sum(reserved),0) FROM habnews_budget WHERE kind='llm' AND event_id=?",(event_id,)).fetchone()[0]
            limit=self.daily if priority=='P0' else self.daily-self.reserve_p0
            if used+requests>limit or event_used+requests>6: raise RuntimeError('quota_paused')
            if used+requests>=self.daily*.8: self.db.incident('local_quota_80','Local call policy reached 80%; actual Pro quota unknown')
            rid=uid(); c.execute('INSERT INTO habnews_budget VALUES(?,?,?,?,?,?,?, ?,?)',(rid,day,event_id,'llm',requests,None,'reserved','{}',time.time()))
            return rid
    def finish(self,rid,actual=None,metadata=None,uncertain=False):
        if actual==0 and not uncertain:self.db.conn.execute('UPDATE habnews_budget SET reserved=0 WHERE id=?',(rid,))
        self.db.conn.execute('UPDATE habnews_budget SET actual=?,status=?,metadata=? WHERE id=?',(actual,'uncertain' if uncertain else 'complete',encode(metadata or {}),rid))
    def reserve_paid_tool(self,*args,**kwargs): raise RuntimeError('paid_tools_disabled_budget_zero')
