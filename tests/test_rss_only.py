import time
from habnews.collector import Collector

def item():
    now=time.time()
    return {'provider_id':'new1','url':'https://tr.investing.com/news/test','title':'TCMB faiz kararı açıklandı','summary':'TCMB politika faizini yüzde 40 olarak belirledi.','published_at':now,'first_seen_at':now,'time_precision':'second'}

def test_blocked_article_source_collects_metadata_without_research(db):
    source={'stable_id':'investing-test','article_access':'blocked_http_403'}
    collector=Collector(db,[source]);collector.observe(source,[]);collector.observe(source,[item()])
    assert db.conn.execute("SELECT stage FROM habnews_observation").fetchone()[0]=='article_access_blocked'
    assert db.conn.execute("SELECT count(*) FROM habnews_queue").fetchone()[0]==0
    assert db.conn.execute("SELECT count(*) FROM habnews_evidence").fetchone()[0]==0

def test_queued_research_stops_when_source_article_access_becomes_blocked(db):
    source={'stable_id':'investing-test'}
    collector=Collector(db,[source]);collector.observe(source,[]);collector.observe(source,[item()])
    source['article_access']='blocked_http_403'
    collector.research_one()
    assert db.conn.execute("SELECT status FROM habnews_queue").fetchone()[0]=='article_access_blocked'
    assert db.conn.execute("SELECT count(*) FROM habnews_evidence").fetchone()[0]==0
