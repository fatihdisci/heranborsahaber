import json,time
import pytest
from habnews.db import DB,encode
from habnews.normalizer import digest
from habnews.approval import Approval

@pytest.fixture
def db(tmp_path):
    store=DB(tmp_path/'habnews.sqlite');store.set_state('enabled','true');return store

@pytest.fixture
def prepared(db):
    now=time.time();eid='event-fixture'
    item={'title':'TEST TCMB politika faizi','summary':'TEST karar yüzde 40','url':'https://www.tcmb.gov.tr/test','published_at':now,'time_precision':'second','first_seen_at':now}
    db.conn.execute('INSERT INTO habnews_event VALUES(?,?,?,?,?,?,?)',(eid,'test:rate:2026',1,'verification_pending','P0',now,now))
    db.conn.execute('INSERT INTO habnews_event_version VALUES(?,?,?,?,?)',(eid,1,digest('40'),encode(item),now))
    passage='TCMB politika faizini yüzde 40 olarak belirledi. TCMB kararı TEST verisidir, gerçek haber değildir.'
    ev='evidence-1';db.conn.execute('INSERT INTO habnews_evidence VALUES(?,?,?,?,?,?,?,?,?,?,0)',(ev,eid,1,'central-bank','central-bank',1,item['url'],passage,digest(passage),now))
    fact={'text':'TCMB politika faizini yüzde 40 olarak belirledi.','source_ref':ev,'value_raw':'40','normalized_value':40,'unit':'yüzde','currency':None,'scale':None,'period':None,'scope':'politika','stage':'belirledi','actor':'TCMB','quote':None}
    result={'schema_version':'habnews-v1','event_id':eid,'event_version':1,'relevance_reason':'TEST — sentetik karar, gerçek haber değildir.','priority':'P0','verification_state':'official_primary','facts':[fact],'ambiguities':[],'headline':'TEST TCMB politika faizi','proposed_body':'TEST TCMB politika faizi\n\n'+fact['text'],'verified_tags':[],'image_candidates':[]}
    job={'event_id':eid,'event_version':1,'evidence_refs':[ev]}
    metadata={'requested_model':'gpt-6-luna','provider':'openai-codex','transport':'codex_responses','auth_source':'habnews_own_oauth','speed':'standard','server_model':None,'fixture':True}
    approval=Approval(db,123,123)
    return db,approval,job,result,metadata

def click(db,did,action='approve',user=123,chat=123,msg=101,update=1):
    nonce=db.conn.execute('SELECT nonce FROM habnews_callback WHERE draft_id=? AND action=?',(did,action)).fetchone()[0]
    db.conn.execute('UPDATE habnews_callback SET message_id=? WHERE draft_id=?',(msg,did))
    return {'update_id':update,'callback_query':{'id':'cb'+str(update),'data':nonce,'from':{'id':user},'message':{'message_id':msg,'chat':{'id':chat,'type':'private'}}}}
