import json,time,copy
import pytest
from conftest import click
from habnews.editorial import process_draft_edit
from habnews.telegram import Outbox,TelegramError
from test_editorial_grounding import draft_case


def draft(prepared,**options):
 db,a,_,_,run=prepared
 sentence='TCMB, politika faizini yüzde 40 olarak belirlediğini açıkladı.'
 result,job,evidence=draft_case(prepared,sentence.rstrip('.'),sentence)
 job.update(quiet_delivery=True,edit_controls=True,editorial_options=options)
 item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0]);item.update(manual_requested_at=time.time(),source_id='tcmb')
 db.conn.execute('UPDATE habnews_event_version SET payload=?',(json.dumps(item),))
 db.conn.execute('UPDATE habnews_evidence SET passage=?',(next(iter(evidence.values()))['passage'],))
 return a.create(job,result,run)


def test_controls_are_bound_to_delivered_private_message(prepared):
 db,a,*_=prepared;did=draft(prepared)
 payload=json.loads(db.conn.execute('SELECT payload FROM habnews_outbox WHERE draft_id=?',(did,)).fetchone()[0])
 assert len(payload['reply_markup']['inline_keyboard'])==2
 assert db.conn.execute('SELECT count(*) FROM habnews_callback WHERE draft_id=?',(did,)).fetchone()[0]==4
 class TG:
  def call(self,*args):return {'message_id':202}
 Outbox(db,TG()).send_one()
 up=click(db,did,'shorten',msg=202)
 up['callback_query']['message']['message_id']=999
 assert a.callback(up)=='stale'

@pytest.mark.parametrize('mode',['no_tags','simplify','shorten'])
def test_edit_preserves_facts_and_uses_no_model_when_possible(prepared,mode):
 db,a,*_=prepared;did=draft(prepared)
 original=db.conn.execute('SELECT * FROM habnews_draft WHERE id=?',(did,)).fetchone()
 up=click(db,did,mode)
 assert 'kaydedildi' in a.callback(up)
 assert a.callback(up)=='duplicate'
 process_draft_edit(db,a)
 newest=db.conn.execute('SELECT * FROM habnews_draft ORDER BY version DESC LIMIT 1').fetchone()
 assert newest['id']!=did and newest['status']=='pending'
 assert json.loads(newest['metadata'])['validated_result']['facts']==json.loads(original['metadata'])['validated_result']['facts']
 if mode=='no_tags':assert '#' not in newest['body']
 else:assert len(newest['body'])<len(original['body']) and 'TCMB:' in newest['body']
 assert db.conn.execute("SELECT count(*) FROM habnews_queue WHERE kind='llm'").fetchone()[0]==0
 assert db.conn.execute('SELECT count(*) FROM habnews_budget').fetchone()[0]==0
 assert a.callback(click(db,did,mode,update=2))=='stale'


def test_headline_edit_uses_model_when_no_valid_alternative_exists(prepared):
 db,a,*_=prepared;did=draft(prepared);db.set_state('llm_state','ready')
 a.callback(click(db,did,'headline'));process_draft_edit(db,a)
 row=db.conn.execute("SELECT payload FROM habnews_queue WHERE kind='llm'").fetchone()
 assert 'önceki başlıktan farklı' in json.loads(row[0])['revision']['instruction']
 assert db.conn.execute('SELECT count(*) FROM habnews_draft').fetchone()[0]==1


def test_paused_edit_not_queued(prepared):
 db,a,*_=prepared;did=draft(prepared);db.set_state('enabled','false')
 assert 'durdurulmuş' in a.callback(click(db,did,'no_tags'))
 assert not db.conn.execute("SELECT 1 FROM habnews_queue WHERE kind='draft_edit'").fetchone()


def test_stale_version_cannot_create_a_new_edit(prepared):
 db,a,*_=prepared;did=draft(prepared);a.callback(click(db,did,'no_tags'))
 db.conn.execute('UPDATE habnews_event SET version=2')
 process_draft_edit(db,a)
 assert db.conn.execute('SELECT count(*) FROM habnews_draft').fetchone()[0]==1
 assert db.conn.execute("SELECT status FROM habnews_queue WHERE kind='draft_edit'").fetchone()[0]=='stale'


def test_model_edit_cannot_deliver_unchanged_or_longer_shortening(prepared):
 from habnews.schema import ValidationError
 db,a,_,_,run=prepared;did=draft(prepared)
 old=db.conn.execute('SELECT * FROM habnews_draft WHERE id=?',(did,)).fetchone();meta=json.loads(old['metadata'])
 job=meta['editorial_context']|{'event_id':old['event_id'],'event_version':1,'evidence_refs':['evidence-1'],
     'manual_attribution':meta['manual_attribution'],'quiet_delivery':True,
     'edit_request':{'draft_id':did,'hash':old['hash'],'mode':'shorten'}}
 with pytest.raises(ValidationError,match='edit_not_improved'):
  a.create(job,meta['validated_result'],run)
 assert db.conn.execute('SELECT count(*) FROM habnews_draft').fetchone()[0]==1


def test_active_revision_blocks_a_second_edit(prepared):
 db,a,*_=prepared;did=draft(prepared)
 db.enqueue('llm','already-editing',{'event_id':'event-fixture','event_version':1})
 assert 'zaten' in a.callback(click(db,did,'no_tags'))
 assert not db.conn.execute("SELECT 1 FROM habnews_queue WHERE kind='draft_edit'").fetchone()
