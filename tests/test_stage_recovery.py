import json,time
import pytest
from habnews.failures import record_failure,retry_callback,source_failure
from habnews.live_feed import feed_callback,notify_manual_failures
from habnews.telegram import Outbox
from habnews.network import HTTPFailure
from test_live_feed_social import card,source


def failed(db,kind='research',code='source_denied'):
 a,click,tg=card(db);db.set_state('llm_state','ready');feed_callback(db,a,click,[source()])
 row=db.conn.execute("SELECT * FROM habnews_queue WHERE kind='research'").fetchone()
 db.conn.execute("UPDATE habnews_queue SET kind=?,status='dead_letter' WHERE id=?",(kind,row['id']))
 record_failure(db,row['id'],kind,code);notify_manual_failures(db,a);Outbox(db,tg).send_one()
 record=db.conn.execute('SELECT * FROM habnews_retry_callback').fetchone()
 update={'update_id':200,'callback_query':{'id':'retry200','data':record['nonce'],'from':{'id':123},'message':{'message_id':record['message_id'],'chat':{'id':123,'type':'private'}}}}
 return a,row,update,tg


def test_source_denied_notice_is_specific_and_retry_is_bound(db):
 a,row,up,tg=failed(db)
 assert 'erişimi engelledi' in tg.calls[-1][1]['text']
 assert 'kaydedildi' in retry_callback(db,a,up)
 assert retry_callback(db,a,up)=='duplicate'
 queued=db.conn.execute("SELECT * FROM habnews_queue WHERE identity LIKE 'retry:%'").fetchone()
 assert queued['kind']=='research'
 assert json.loads(queued['payload'])['llm_identity']!=json.loads(row['payload']).get('llm_identity')
 up['update_id']=201
 assert retry_callback(db,a,up)=='stale'


def test_model_timeout_retry_starts_at_model_queue(db):
 a,row,up,tg=failed(db,'llm','model_timeout')
 assert 'yanıt süresi' in tg.calls[-1][1]['text']
 retry_callback(db,a,up)
 assert db.conn.execute("SELECT kind FROM habnews_queue WHERE identity LIKE 'retry:%'").fetchone()[0]=='llm'

@pytest.mark.parametrize('change',['user','message','version','expired','paused'])
def test_retries_cannot_cross_authorization_version_or_freshness(db,change):
 a,row,up,tg=failed(db)
 if change=='user':up['callback_query']['from']['id']=999
 elif change=='message':up['callback_query']['message']['message_id']=999
 elif change=='version':db.conn.execute('UPDATE habnews_event SET version=2')
 elif change=='expired':
  item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0]);item['manual_requested_at']=time.time()-1900
  db.conn.execute('UPDATE habnews_event_version SET payload=?',(json.dumps(item),))
 else:db.set_state('enabled','false')
 if change=='user':
  with pytest.raises(PermissionError):retry_callback(db,a,up)
 else:assert 'kaydedildi' not in retry_callback(db,a,up)
 assert not db.conn.execute("SELECT 1 FROM habnews_queue WHERE identity LIKE 'retry:%'").fetchone()


def test_notice_deduplicates_same_failure(db):
 a,row,up,tg=failed(db);before=db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]
 notify_manual_failures(db,a)
 assert db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]==before


def test_source_diagnostics_do_not_leak_exception_text():
 assert source_failure(HTTPFailure(403))=='source_denied'
 assert source_failure(TimeoutError('secret-token'))=='source_timeout'
 assert source_failure(ValueError('secret-token'))=='source_parse'


def test_cached_model_repair_avoids_refetch_and_expires(prepared,tmp_path):
 from habnews.hermes import JobBroker,atomic_file
 from habnews.budget import Budget
 from habnews.db import encode
 from habnews.normalizer import digest
 from habnews.schema import ValidationError
 from habnews.maintenance import cleanup_maintext
 db,a,job,result,run=prepared
 item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0]);item.update(manual_requested_at=time.time(),source_id='foreks')
 db.conn.execute('UPDATE habnews_event_version SET payload=?',(encode(item),));db.set_state('llm_state','ready')
 ev=db.conn.execute('SELECT * FROM habnews_evidence').fetchone()
 root=db.path.parent/'maintext';root.mkdir()
 binding={'text':ev['passage'],'source_title':item['title'],'source_url':item['url']}
 atomic_file(root/(ev['id']+'.json'),binding|{'expires_at':time.time()+300,'digest':ev['digest'],'document_digest':digest(encode(binding)),'content_contract':'article-v2'})
 job.update(manual_attribution={'source_type':'article'},deadline=time.time()+180,editorial_options={'no_tags':True})
 db.enqueue('llm','first',{'event_id':job['event_id'],'event_version':1});row=db.claim('llm');reservation=Budget(db).reserve(job['event_id'],'P0')
 db.set_state('job:'+row['id'],encode({'lease':row['lease'],'reservation':reservation,'job':job}))
 broker=JobBroker(db,tmp_path/'jobs');atomic_file(broker.directory/(row['id']+'.result.json'),{'result':result,'run_metadata':run})
 class Reject:
  def create(self,*args,**kwargs):raise ValidationError('unsupported_headline')
 broker.consume(Reject());broker.submit_one()
 assert not db.conn.execute("SELECT 1 FROM habnews_queue WHERE kind='research'").fetchone()
 next_job=json.loads(next(broker.directory.glob('*.job.json')).read_text())
 assert next_job['evidence'][0]['full_text']==ev['passage']
 assert next_job['editorial_options']=={'no_tags':True}
 assert next_job['repair_attempt']==1
 cleanup_maintext(db,time.time()+301)
 assert not list(root.glob('*.json'))


def test_new_tables_migrate_an_existing_database_without_losing_state(db):
 from habnews.db import DB
 db.set_state('migration-marker','kept')
 for table in ('habnews_feed_group','habnews_retry_callback','habnews_job_failure'):
  db.conn.execute('DROP TABLE '+table)
 path=db.path;db.conn.close();reopened=DB(path)
 assert reopened.state('migration-marker')=='kept' and reopened.enabled()
 for table in ('habnews_feed_group','habnews_retry_callback','habnews_job_failure'):
  assert reopened.conn.execute('SELECT count(*) FROM '+table).fetchone()[0]==0
 reopened.conn.close()
