import copy,io,json,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from PIL import Image
from habnews.budget import Budget
from habnews.db import DB
from habnews.images import reusable,image_note,store_image
from habnews.maintenance import backup,restore,cleanup
from habnews.telegram import Telegram
from habnews.hermes import Runner

RECORD={'landing_page_url':'https://commons.wikimedia.org/wiki/File:Example.jpg','original_asset_url':'https://upload.wikimedia.org/example.jpg','publisher':'Wikimedia Commons','creator':'TEST author','license_name':'CC BY','license_version':'4.0','license_url':'https://creativecommons.org/licenses/by/4.0/','rights_evidence':'TEST fictional rights record, not a real licensed photograph','attribution_text':'TEST author / CC BY 4.0 / source file page','restrictions':[],'retrieved_at':time.time(),'photographed_at':None,'subject_match':True,'event_match':False,'archive_or_current':'archive','confidence_reason':'TEST synthetic fixture','rights_status':'verified_reusable'}

def test_budget_limit_and_critical_reserve(db):
    budget=Budget(db,daily=3,reserve_p0=1)
    for n in range(2):rid=budget.reserve('e'+str(n),'P1');budget.finish(rid,1)
    with pytest.raises(RuntimeError,match='quota_paused'):budget.reserve('e3','P1')
    rid=budget.reserve('p0','P0');budget.finish(rid,1)
    with pytest.raises(RuntimeError,match='quota_paused'):budget.reserve('p0-2','P0')

def test_event_six_turn_limit(db):
    budget=Budget(db)
    for _ in range(6):rid=budget.reserve('same','P0');budget.finish(rid,1)
    with pytest.raises(RuntimeError,match='quota_paused'):budget.reserve('same','P0')

def test_concurrent_quota_reservation_only_one(db):
    path=db.path
    def reserve(n):
        store=DB(path)
        try:return Budget(store).reserve(str(n),'P0')
        except RuntimeError:return None
        finally:store.conn.close()
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(reserve,range(2)))
    assert sum(x is not None for x in results)==1

def test_uncertain_usage_counted_no_paid_tool(db):
    budget=Budget(db);rid=budget.reserve('one','P0');budget.finish(rid,uncertain=True)
    assert db.conn.execute('SELECT reserved,status FROM habnews_budget').fetchone()[1]=='uncertain'
    with pytest.raises(RuntimeError,match='paid_tools_disabled'):budget.reserve_paid_tool('search',upper_usd=0.01)

@pytest.mark.parametrize('rights',['unknown','permission_required','prohibited'])
def test_unlicensed_photo_never_downloaded(tmp_path,rights,monkeypatch):
    record=RECORD|{'rights_status':rights}
    monkeypatch.setattr('habnews.images.Fetcher.get',lambda *args:pytest.fail('must not fetch'))
    assert not reusable(record)
    with pytest.raises(ValueError):store_image(record,tmp_path,['upload.wikimedia.org'])

def test_wrong_person_and_archive_label():
    assert not reusable(RECORD|{'subject_match':False})
    assert 'Arşiv fotoğrafı; bu açıklamanın görüntüsü değil' in image_note(RECORD)
    assert 'dosya verilmiyor' in image_note(RECORD|{'rights_status':'unknown'})

def test_cc_missing_attribution_blocked():assert not reusable(RECORD|{'attribution_text':''})

def test_image_magic_mime_spoof(tmp_path,monkeypatch):
    monkeypatch.setattr('habnews.images.Fetcher.get',lambda *args:(b'<html>bad</html>',{'content-type':'image/jpeg'},'url',200))
    with pytest.raises(ValueError,match='image_magic'):store_image(RECORD,tmp_path,['upload.wikimedia.org'])

def test_image_size_dimension_and_provenance(tmp_path,monkeypatch):
    im=Image.new('RGB',(200,200),'white');buf=io.BytesIO();im.save(buf,format='JPEG');blob=buf.getvalue()
    monkeypatch.setattr('habnews.images.Fetcher.get',lambda *args:(blob,{'content-type':'image/jpeg'},'url',200))
    path,provenance=store_image(RECORD,tmp_path,['upload.wikimedia.org'])
    assert path.read_bytes()==blob;assert provenance['dimensions']==[200,200]
    assert path.with_suffix('.attribution.txt').exists()
    assert path.stat().st_mode&0o777==0o600

def test_backup_restore_disabled_and_integrity(prepared,tmp_path):
    db,a,j,r,m=prepared;a.create(j,r,m);backup(db,tmp_path/'media',tmp_path/'backup')
    health=restore(tmp_path/'backup',tmp_path/'restored');assert not health['enabled']
    new=DB(tmp_path/'restored/habnews.sqlite');assert new.conn.execute('SELECT count(*) FROM habnews_draft').fetchone()[0]==1
    assert new.conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'

def test_restore_path_traversal(tmp_path,db):
    backup(db,tmp_path/'media',tmp_path/'backup');manifest=tmp_path/'backup/manifest.json';manifest.write_text('[{"path":"../../outside","sha256":"bad"}]')
    with pytest.raises(ValueError,match='backup_integrity'):restore(tmp_path/'backup',tmp_path/'restore')

def test_active_evidence_retention_protected(prepared,tmp_path):
    db,a,j,r,m=prepared;did=a.create(j,r,m);db.conn.execute('UPDATE habnews_evidence SET retrieved=?',(time.time()-40*86400,))
    cleanup(db,tmp_path/'media');assert db.conn.execute('SELECT tombstone FROM habnews_evidence').fetchone()[0]==0
    db.conn.execute("UPDATE habnews_draft SET status='rejected'");cleanup(db,tmp_path/'media');assert db.conn.execute('SELECT tombstone FROM habnews_evidence').fetchone()[0]==1

def test_audit_append_only(db):
    db.audit('test','fixture')
    with pytest.raises(Exception,match='append-only'):db.conn.execute("UPDATE habnews_audit SET kind='changed'")

def test_telegram_publisher_and_webhook_changes_not_allowed():
    t=Telegram('123:synthetic')
    for method in ('setWebhook','deleteWebhook','setMyCommands','sendMediaGroup','publish','retweet','like'):
        with pytest.raises(ValueError,match='method_denied'):t.call(method,{})

def test_runner_paused_no_import_or_call(tmp_path,monkeypatch):
    (tmp_path/'job.job.json').write_text('{}');(tmp_path/'runtime-state.json').write_text('{"enabled":false}')
    monkeypatch.setattr('habnews.hermes.run_job',lambda *a:pytest.fail('paused job called'))
    Runner(tmp_path).tick();assert (tmp_path/'job.job.json').exists()

def test_startup_missing_auth_not_fallback(tmp_path,monkeypatch):
    from habnews.hermes import runtime_credentials,HermesUnavailable
    monkeypatch.setattr('habnews.hermes.own_home',lambda:tmp_path)
    with pytest.raises(HermesUnavailable,match='auth_required'):runtime_credentials()


def test_offline_restore_does_not_touch_live_control(db,tmp_path,monkeypatch):
    backup(db,tmp_path/'media',tmp_path/'backup')
    control=tmp_path/'live-control.json'
    monkeypatch.setenv('HABNEWS_SWITCH_FILE',str(control))
    health=restore(tmp_path/'backup',tmp_path/'offline-restored')
    assert not health['enabled'] and db.enabled() and not control.exists()
