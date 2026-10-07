import json,time
import pytest
from habnews.collector import Collector
from habnews.db import DB
from habnews.normalizer import fresh,date_value,parse_feed,classify,event_key

SOURCE={'stable_id':'a','priority':'A','source_family':'a'}
def item(id='1',title='TCMB politika faiz kararı',summary='Faiz kararı yüzde 40',offset=0):
    return {'provider_id':id,'url':'https://www.tcmb.gov.tr/news/'+id,'title':title,'summary':summary,'published_at':time.time()+offset,'first_seen_at':time.time(),'time_precision':'second'}

def test_baseline_restart_and_new_source(db):
    c=Collector(db,[SOURCE]);c.observe(SOURCE,[item()]);assert db.conn.execute('SELECT count(*) FROM habnews_event').fetchone()[0]==0
    reopened=DB(db.path);c=Collector(reopened,[SOURCE]);c.observe(SOURCE,[item(),item('2')]);assert reopened.conn.execute('SELECT count(*) FROM habnews_event').fetchone()[0]==1
    c.observe(SOURCE|{'stable_id':'new'},[item('3')]);assert reopened.conn.execute('SELECT count(*) FROM habnews_event').fetchone()[0]==1

def test_same_event_three_sources_and_revision(db):
    c=Collector(db,[])
    for sid in ('a','b','c'):
        src=SOURCE|{'stable_id':sid,'source_family':sid};c.observe(src,[]);c.observe(src,[item()])
    assert db.conn.execute('SELECT count(*) FROM habnews_event').fetchone()[0]==1
    assert db.conn.execute('SELECT count(*) FROM habnews_event_observation').fetchone()[0]==3
    c.observe(SOURCE,[item(summary='Faiz kararı yüzde 39')])
    assert db.conn.execute('SELECT version FROM habnews_event').fetchone()[0]==2

def test_rejected_same_fact_not_requeued(db):
    c=Collector(db,[]);c.observe(SOURCE,[]);c.observe(SOURCE,[item()]);db.conn.execute("UPDATE habnews_event SET status='rejected'")
    count=db.conn.execute('SELECT count(*) FROM habnews_queue').fetchone()[0]
    other=SOURCE|{'stable_id':'b'};c.observe(other,[]);c.observe(other,[item()]);assert db.conn.execute('SELECT count(*) FROM habnews_queue').fetchone()[0]==count
    c.observe(other,[item(summary='Faiz kararı yüzde 38')]);assert db.conn.execute('SELECT version FROM habnews_event').fetchone()[0]==2

@pytest.mark.parametrize('offset,expected',[(-1900,'expired'),(-90000,'old_event'),(100,'future_quarantine')])
def test_freshness(offset,expected):assert fresh(item(offset=offset))[1]==expected

def test_date_only_no_midnight_claim():
    stamp,precision=date_value('2026-10-06');assert precision=='date';assert fresh(item()|{'published_at':stamp,'time_precision':precision},stamp+3600)[0]

def test_unknown_naive_time_not_assumed():assert date_value('2026-10-06T12:00:00')==(None,'unknown')

def test_year_transition():
    first,_=date_value('2026-12-31T23:59:00+03:00');second,_=date_value('2027-01-01T00:01:00+03:00');assert second-first==120

@pytest.mark.parametrize('title',['KAP şirket pay geri alım açıklaması',"Şirket pay satış işlemini KAP'a açıkladı",'KAP DKB fon dağılımı'])
def test_scope_excluded(title):assert classify(item(title=title))[0]=='scope_excluded'

@pytest.mark.parametrize('title',['Futbol maç sonucu','Magazin ünlü tatili','Hedef fiyat al tavsiyesi'])
def test_irrelevant_or_promotion(title):assert classify(item(title=title,summary=''))[0]=='filtered'

def test_different_company_not_collapsed():assert event_key(item(title='ABC yeni sözleşme'))!=event_key(item(title='DEF yeni sözleşme'))

def test_stale_lease_recovery(db):
    db.enqueue('research','one',{});claimed=db.claim('research',ttl=1);assert claimed;assert db.claim('research') is None
    recovered=db.claim('research',now=time.time()+2);assert recovered and recovered['lease']!=claimed['lease']
    with pytest.raises(RuntimeError,match='lost_lease'):db.finish(claimed)

def test_llm_crash_uncertain_not_replayed(db):
    db.enqueue('llm','x',{});db.claim('llm',ttl=1);assert db.claim('llm',now=time.time()+2) is None
    assert db.conn.execute('SELECT status FROM habnews_queue').fetchone()[0]=='uncertain'

def test_kill_switch_persists_restart(db):
    db.set_state('enabled','false');new=DB(db.path);assert not new.enabled()
    with pytest.raises(RuntimeError,match='paused'):Collector(new,[]).poll()

@pytest.mark.parametrize('data',[b'<html>blocked</html>',b'<rss><channel><item>',b'<!DOCTYPE x [<!ENTITY y SYSTEM "file:///etc/passwd">]><rss/>'])
def test_feed_parse_failures(data):
    with pytest.raises(Exception):parse_feed(data,'s')
