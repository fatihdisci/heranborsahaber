import json,time
import pytest
from conftest import click
from habnews.telegram import Outbox,TelegramError,ApprovalService
from habnews.editorial import export_approved

class Mock:
    def __init__(self,error=None):self.calls=[];self.error=error
    def call(self,method,payload):
        self.calls.append(method)
        if self.error:raise self.error
        return {'message_id':100+len(self.calls)}

@pytest.mark.parametrize('user,chat',[(99,123),(123,99)])
def test_unauthorized(prepared,user,chat):
    db,a,j,r,m=prepared;did=a.create(j,r,m)
    with pytest.raises(PermissionError):a.callback(click(db,did,user=user,chat=chat))

def test_group_and_forward_rejected(prepared):
    db,a,j,r,m=prepared;did=a.create(j,r,m);update=click(db,did);update['callback_query']['message']['chat']['type']='group'
    with pytest.raises(PermissionError):a.callback(update)
    update['callback_query']['message']['chat']['type']='private';update['callback_query']['message']['forward_origin']={}
    with pytest.raises(PermissionError):a.callback(update)

def test_exact_approval_dedup_no_publication(prepared,tmp_path):
    db,a,j,r,m=prepared;did=a.create(j,r,m);up=click(db,did)
    assert 'Yayınlanmadı' in a.callback(up);assert a.callback(up)=='duplicate'
    assert db.conn.execute('SELECT count(*) FROM habnews_decision').fetchone()[0]==1
    package=export_approved(db,did,tmp_path/'approved');assert package['published'] is False
    assert (tmp_path/'approved/draft.txt').read_text().endswith('#TCMB #faiz')

def test_changed_draft_and_event_callbacks_stale(prepared):
    db,a,j,r,m=prepared;did=a.create(j,r,m);up=click(db,did)
    new=a.create(j,r,m);assert new!=did;assert a.callback(up)=='stale'
    newup=click(db,new,update=2);db.conn.execute('UPDATE habnews_event SET version=2');assert a.callback(newup)=='stale'

def test_wrong_message_callback_stale(prepared):
    db,a,j,r,m=prepared;did=a.create(j,r,m);up=click(db,did);up['callback_query']['message']['message_id']=999
    assert a.callback(up)=='stale'

def test_revision_reply_scope_invalidates_approval(prepared):
    db,a,j,r,m=prepared;did=a.create(j,r,m)
    db.conn.execute('INSERT INTO habnews_revision VALUES(?,?,?,?)',(111,j['event_id'],did,123))
    message={'from':{'id':123},'chat':{'id':123,'type':'private'},'reply_to_message':{'message_id':111},'text':'Daha kısa yaz'}
    update={'update_id':8,'message':message}
    assert 'Revizyon' in a.reply(update);assert a.reply(update)=='duplicate'
    assert db.conn.execute('SELECT status FROM habnews_draft WHERE id=?',(did,)).fetchone()[0]=='stale'

def test_outbox_order_receipts(prepared):
    db,a,j,r,m=prepared;a.create(j,r,m);mock=Mock();out=Outbox(db,mock)
    out.send_one();out.send_one();out.send_one();assert mock.calls==['sendMessage','sendMessage']
    assert db.conn.execute("SELECT count(*) FROM habnews_outbox WHERE status='sent' AND message_id IS NOT NULL").fetchone()[0]==2

def test_network_uncertain_not_retried_or_followed(prepared):
    db,a,j,r,m=prepared;a.create(j,r,m);mock=Mock(TelegramError(0));out=Outbox(db,mock);out.send_one();out.send_one()
    assert len(mock.calls)==1
    assert db.conn.execute("SELECT count(*) FROM habnews_outbox WHERE status='uncertain'").fetchone()[0]==1

def test_crashed_send_lease_becomes_uncertain(prepared):
    db,a,j,r,m=prepared;did=a.create(j,r,m)
    db.conn.execute("UPDATE habnews_outbox SET status='sending',lease_until=? WHERE draft_id=? AND part=0",(time.time()-1,did))
    mock=Mock();Outbox(db,mock).send_one();assert mock.calls==[]
    assert db.conn.execute("SELECT status FROM habnews_outbox WHERE part=0").fetchone()[0]=='uncertain'

@pytest.mark.parametrize('code,status',[(429,'pending'),(400,'blocked'),(401,'blocked'),(403,'blocked'),(500,'uncertain')])
def test_telegram_error_state(prepared,code,status):
    db,a,j,r,m=prepared;a.create(j,r,m);Outbox(db,Mock(TelegramError(code,30))).send_one()
    assert db.conn.execute('SELECT status FROM habnews_outbox WHERE part=0').fetchone()[0]==status

def test_expired_before_delivery(prepared):
    db,a,j,r,m=prepared;a.create(j,r,m)
    row=db.conn.execute('SELECT payload FROM habnews_event_version').fetchone();item=json.loads(row[0]);item['published_at']=time.time()-1900
    db.conn.execute('UPDATE habnews_event_version SET payload=?',(json.dumps(item),))
    mock=Mock();Outbox(db,mock).send_one();assert not mock.calls
    assert db.conn.execute("SELECT count(*) FROM habnews_outbox WHERE status='expired'").fetchone()[0]==2

def test_stop_blocks_delivery_but_records_admin_decision(prepared):
    db,a,j,r,m=prepared;did=a.create(j,r,m);db.set_state('enabled','false')
    with pytest.raises(RuntimeError,match='paused'):Outbox(db,Mock()).send_one()
    assert 'Yayınlanmadı' in a.callback(click(db,did))

def test_start_requires_readiness(db):
    from habnews.approval import Approval
    svc=ApprovalService(db,Approval(db,123,123),Mock(),777)
    db.set_state('enabled','false')
    response=svc.command({'from':{'id':123},'chat':{'id':123,'type':'private'},'text':'/haber_baslat'})
    assert response.startswith('Başlatılmadı');assert not db.enabled()
