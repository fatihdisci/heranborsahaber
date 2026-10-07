import json,time,sqlite3
from pathlib import Path
import pytest
from habnews.hermes import Runner,atomic_file
from habnews.telegram import Outbox
from conftest import click
from test_approval_delivery import Mock


def test_receipt_write_failure_leaves_uncertain_after_crash(prepared):
    db,a,j,r,m=prepared;a.create(j,r,m)
    db.conn.execute("CREATE TRIGGER simulated_disk_full BEFORE UPDATE OF message_id ON habnews_outbox BEGIN SELECT RAISE(ABORT,'simulated disk full'); END;")
    transport=Mock();out=Outbox(db,transport)
    with pytest.raises(sqlite3.IntegrityError,match='disk full'):out.send_one()
    assert transport.calls==['sendMessage']
    db.conn.execute('DROP TRIGGER simulated_disk_full');db.conn.execute("UPDATE habnews_outbox SET lease_until=? WHERE status='sending'",(time.time()-1,))
    out.send_one();assert transport.calls==['sendMessage']
    assert db.conn.execute('SELECT status FROM habnews_outbox WHERE part=0').fetchone()[0]=='uncertain'

def test_atomic_spool_disk_failure_not_valid_job(tmp_path,monkeypatch):
    real=Path.write_text
    def fail(self,*a,**k):
        if self.suffix=='.tmp':raise OSError(28,'No space left on device')
        return real(self,*a,**k)
    monkeypatch.setattr(Path,'write_text',fail)
    with pytest.raises(OSError):atomic_file(tmp_path/'x.job.json',{'job_id':'x'})
    assert not (tmp_path/'x.job.json').exists()

def test_kill_during_call_does_not_create_new_draft(prepared,monkeypatch,tmp_path):
    from habnews.hermes import JobBroker
    from habnews.db import encode
    db,a,j,r,m=prepared
    db.enqueue('llm','fixture-job',j);row=db.claim('llm')
    from habnews.budget import Budget
    rid=Budget(db).reserve(j['event_id'],'P0')
    db.set_state('job:'+row['id'],encode({'lease':row['lease'],'reservation':rid,'job':j}))
    atomic_file(tmp_path/(row['id']+'.result.json'),{'result':r,'run_metadata':m})
    db.set_state('enabled','false');JobBroker(db,tmp_path).consume(a)
    assert db.conn.execute('SELECT count(*) FROM habnews_draft').fetchone()[0]==0
    assert db.conn.execute('SELECT status FROM habnews_queue').fetchone()[0]=='paused_result'

def test_unrelated_reply_cannot_revise(prepared):
    db,a,j,r,m=prepared;did=a.create(j,r,m)
    response=a.reply({'update_id':80,'message':{'from':{'id':123},'chat':{'id':123,'type':'private'},'reply_to_message':{'message_id':999},'text':'Başka olay'}})
    assert 'Önce ilgili kartta' in response
    assert db.conn.execute("SELECT count(*) FROM habnews_queue WHERE kind='revision'").fetchone()[0]==0

def test_main_text_not_snippet_html_rejected():
    from habnews.normalizer import extract_article
    with pytest.raises(ValueError):extract_article(b'<html><body><p>'+b'x'*1000+b'</p></body></html>','text/html')
