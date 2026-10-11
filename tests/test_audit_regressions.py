"""Offline regressions: no Telegram, model, or publisher network requests."""
import io
import json
import time
from types import SimpleNamespace

import pytest

from habnews.db import encode
from habnews.budget import Budget
from habnews.hermes import JobBroker
from habnews.maintenance import backup, cleanup, restore
from habnews.telegram import ApprovalService, TelegramError


@pytest.mark.parametrize('damage', ['extra', 'symlink', 'duplicate', 'missing_database', 'absolute'])
def test_restore_checks_entire_backup_before_copy(db, tmp_path, damage):
    source=tmp_path/'backup'
    backup(db,tmp_path/'media',source)
    manifest=json.loads((source/'manifest.json').read_text())
    if damage=='extra':(source/'unchecked.txt').write_text('unverified')
    elif damage=='symlink':
        (source/'alias.sqlite').symlink_to('habnews.sqlite')
        manifest.append(manifest[0]|{'path':'alias.sqlite'})
    elif damage=='duplicate':manifest.append(manifest[0])
    elif damage=='missing_database':
        (source/'habnews.sqlite').unlink();manifest=[]
    else:manifest[0]['path']=str(source/'habnews.sqlite')
    (source/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='backup_integrity'):restore(source,tmp_path/'restore')
    assert not (tmp_path/'restore').exists()


@pytest.mark.parametrize('protection', ['recent', 'active'])
def test_cleanup_keeps_shared_image_until_last_reference_expires(prepared,tmp_path,protection):
    db,approval,job,result,metadata=prepared
    approval.create(job,result,metadata)
    media=tmp_path/'media';media.mkdir();photo=media/'shared.jpg';photo.write_bytes(b'fixture')
    photo.with_suffix('.json').write_text('{}')
    now=time.time();old=now-40*86400
    for ident,event,created in [('old','expired-event',old),('keep',job['event_id'] if protection=='active' else 'recent-event',old if protection=='active' else now)]:
        db.conn.execute('INSERT INTO habnews_image_candidate VALUES(?,?,?,?,?,?,?,0)',(ident,event,1,'{}','unknown',created,str(photo)))
    cleanup(db,media,now)
    assert photo.exists() and photo.with_suffix('.json').exists()
    assert db.conn.execute("SELECT tombstone FROM habnews_image_candidate WHERE id='old'").fetchone()[0]==1
    db.conn.execute("UPDATE habnews_draft SET status='rejected'")
    db.conn.execute('UPDATE habnews_image_candidate SET created=?',(old,))
    cleanup(db,media,now)
    assert not photo.exists()


@pytest.mark.parametrize('content,running', [('{',None),('[]',None),('null',None),('{}','{')])
def test_malformed_model_output_releases_reservation(prepared,tmp_path,content,running):
    db,approval,job,result,metadata=prepared
    db.enqueue('llm','bad-output',job);row=db.claim('llm')
    reservation=Budget(db).reserve(job['event_id'],'P0')
    db.set_state('job:'+row['id'],encode({'lease':row['lease'],'reservation':reservation,'job':job}))
    path=tmp_path/(row['id']+'.result.json');path.write_text(content)
    if running is not None:(tmp_path/(row['id']+'.job.running')).write_text(running)
    JobBroker(db,tmp_path).consume(approval)
    assert not path.exists()
    assert db.state('job:'+row['id']) is None
    assert db.conn.execute('SELECT status FROM habnews_budget WHERE id=?',(reservation,)).fetchone()[0]=='uncertain'
    assert db.conn.execute('SELECT status FROM habnews_queue WHERE id=?',(row['id'],)).fetchone()[0]=='needs_review'
    assert Budget(db).reserve('next-event','P0')


@pytest.mark.parametrize('code', [400,429])
def test_expired_callback_ack_does_not_stall_updates(db,monkeypatch,code):
    monkeypatch.setattr('habnews.gpt_export.gpt_callback',lambda *args:'duplicate')
    monkeypatch.setattr('habnews.config.sources',lambda:[])
    monkeypatch.setattr('habnews.readiness.activate_requested_setup',lambda db:False)
    deliveries=[]
    monkeypatch.setattr('habnews.telegram.Outbox.send_one',lambda self:deliveries.append(True))
    def call(method,payload):
        if method=='getUpdates':return [{'update_id':123,'callback_query':{'id':'expired'}}]
        if method=='answerCallbackQuery':raise TelegramError(code)
        pytest.fail('Unexpected network method: '+method)
    service=ApprovalService(db,SimpleNamespace(chat_id=123),SimpleNamespace(call=call),1)
    if code==429:
        with pytest.raises(TelegramError):service.tick()
        assert not deliveries
    else:
        service.tick()
        assert db.state('telegram_offset')=='124'
        assert deliveries==[True]


@pytest.mark.parametrize('length,body', [(-1,b'{}'),(0,b''),(8193,b'{}'),(2,b'[]'),(17,b'{"max_bytes": -1}'),(52,b'{"url":"https://example.com","max_bytes":-1}')])
def test_egress_rejects_invalid_requests_without_fetch(monkeypatch,length,body):
    from habnews.egress import Handler
    class BoundedInput(io.BytesIO):
        def read(self,size=-1):
            assert size>=0, 'unbounded read'
            return super().read(size)
    handler=object.__new__(Handler)
    handler.path='/fetch';handler.headers={'Content-Length':str(length)}
    handler.rfile=BoundedInput(body);handler.wfile=io.BytesIO()
    handler.send_response=lambda *args:None
    handler.send_header=lambda *args:None
    handler.end_headers=lambda:None
    monkeypatch.setattr('habnews.egress.Fetcher',lambda *args,**kwargs:pytest.fail('invalid request reached fetch'))
    handler.do_POST()
    assert json.loads(handler.wfile.getvalue())['error']=='ValueError'


def test_broker_connect_failure_closes_socket(monkeypatch):
    from habnews.network import Fetcher
    class FailedSocket:
        closed=False
        def settimeout(self,value):pass
        def connect(self,path):raise OSError('broker unavailable')
        def close(self):self.closed=True
    sock=FailedSocket()
    monkeypatch.setenv('HABNEWS_FETCH_SOCKET','/broker/fetch.sock')
    monkeypatch.setattr('habnews.network.socket.socket',lambda *args:sock)
    with pytest.raises(OSError,match='broker unavailable'):Fetcher(['example.com']).get('https://example.com')
    assert sock.closed


def test_tls_setup_failure_closes_socket(monkeypatch):
    from habnews.network import PinnedHTTPS
    sock=SimpleNamespace(closed=False)
    sock.close=lambda:setattr(sock,'closed',True)
    monkeypatch.setattr('habnews.network.socket.create_connection',lambda *args:sock)
    connection=PinnedHTTPS('example.com','93.184.216.34',1)
    def fail(*args,**kwargs):raise OSError('TLS setup failed')
    connection._context=SimpleNamespace(wrap_socket=fail)
    with pytest.raises(OSError,match='TLS setup failed'):connection.connect()
    assert sock.closed


@pytest.mark.parametrize('tampered',[False,True])
def test_approved_export_checks_image_bytes_before_creating_package(prepared,tmp_path,monkeypatch,tampered):
    import hashlib
    from pathlib import Path
    from habnews.editorial import export_approved
    from test_budget_media_operations import RECORD
    from conftest import click
    db,approval,job,result,metadata=prepared
    did=approval.create(job,result,metadata)
    approval.callback(click(db,did))
    meta=json.loads(db.conn.execute('SELECT metadata FROM habnews_draft WHERE id=?',(did,)).fetchone()[0])
    raw=b'approved-image'
    meta['image']={'path':'/data/media/test.jpg','provenance':RECORD|{'sha256':hashlib.sha256(raw).hexdigest()}}
    db.conn.execute('UPDATE habnews_draft SET metadata=? WHERE id=?',(encode(meta),did))
    original_read=Path.read_bytes
    monkeypatch.setattr(Path,'read_bytes',lambda p: (b'changed' if tampered else raw) if str(p)=='/data/media/test.jpg' else original_read(p))
    target=tmp_path/'package'
    if tampered:
        with pytest.raises(ValueError,match='media_digest'):export_approved(db,did,target)
        assert not target.exists()
    else:
        export_approved(db,did,target)
        assert (target/'original.jpg').read_bytes()==raw
        assert (target/'draft.txt').read_text()


def test_egress_valid_request_preserves_response_contract(monkeypatch):
    from habnews.egress import Handler
    calls=[]
    class Fetch:
        def __init__(self,allowed,guard,max_bytes):calls.append((allowed,max_bytes))
        def get(self,url,headers):
            calls.append((url,headers))
            return b'article',{'content-type':'text/html'},url,200
    monkeypatch.setattr('habnews.egress.Fetcher',Fetch)
    monkeypatch.setattr('habnews.egress.sources',lambda:[{'enabled':True,'stable_id':'cnbce','allowed_hosts':['www.cnbce.com']}])
    body=json.dumps({'url':'https://www.cnbce.com/article','headers':{'If-None-Match':'etag'},'max_bytes':20_000_000}).encode()
    handler=object.__new__(Handler)
    handler.path='/fetch';handler.headers={'Content-Length':str(len(body))}
    handler.rfile=io.BytesIO(body);handler.wfile=io.BytesIO()
    handler.send_response=lambda *args:None
    handler.send_header=lambda *args:None
    handler.end_headers=lambda:None
    handler.do_POST()
    response=json.loads(handler.wfile.getvalue())
    assert response=={'body':'YXJ0aWNsZQ==','headers':{'content-type':'text/html'},'url':'https://www.cnbce.com/article','status':200}
    assert calls[0][1]==10_000_000
    assert calls[1][1]=={'If-None-Match':'etag'}


def test_incomplete_egress_body_times_out_instead_of_blocking_worker(monkeypatch):
    import socket
    import threading
    from habnews.egress import Handler
    monkeypatch.setattr(Handler,'timeout',0.05)
    server,client=socket.socketpair()
    client.settimeout(2)
    worker=threading.Thread(target=Handler,args=(server,('local',0),None),daemon=True)
    worker.start()
    try:
        client.sendall(b'POST /fetch HTTP/1.0\r\nContent-Length: 2\r\n\r\n{')
        result=b''
        while b'TimeoutError' not in result:
            part=client.recv(4096)
            if not part:break
            result+=part
        worker.join(1)
        assert not worker.is_alive()
        assert b'TimeoutError' in result
    finally:
        client.close();server.close();worker.join(1)
