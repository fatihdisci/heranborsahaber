import json,time
from email.utils import formatdate
import pytest
from habnews.collector import Collector
from habnews.config import sources
from habnews.live_feed import process_live_feed,feed_callback,enqueue_recent
from habnews.normalizer import classify,fresh
from habnews.social import parse_social_feed
from habnews.approval import Approval
from habnews.telegram import Outbox
from habnews.hermes import JobBroker,Runner

def source(account=None):
    return next(s for s in sources() if s['stable_id']==('x-'+account if account else 'foreks'))|{'enabled':True}

def item():
    return {'source_id':'foreks','provider_id':'TEST-NEWS','url':'https://www.foreks.com/test',
            'title':'TEST Fon kurulu yatırımcıları koruyacak','summary':"Türkiye'de fon kurulu yatırımcıların haklarını koruyacak.",
            'published_at':time.time(),'first_seen_at':time.time(),'time_precision':'second'}

class FakeTelegram:
    def __init__(self):self.calls=[]
    def call(self,method,payload):self.calls.append((method,payload));return {'message_id':101}

def card(db,src=None,post=None):
    src=src or source();c=Collector(db,[src]);c.observe(src,[]);c.observe(src,[post or item()])
    a=Approval(db,123,123);process_live_feed(db,a,[src]);tg=FakeTelegram();Outbox(db,tg).send_one()
    record=db.conn.execute('SELECT * FROM habnews_feed_callback').fetchone()
    click={'update_id':99,'callback_query':{'id':'cb99','data':record['nonce'],'from':{'id':123},'message':{'message_id':101,'chat':{'id':123,'type':'private'}}}}
    return a,click,tg

@pytest.mark.parametrize('title',['Türkiye üniversite açılışı','Aselsan gelirini artırdı','SPK yeni bülten yayımladı','Fon krizi TBMM gündeminde'])
def test_or_filter_and_spk_media_allowed(title):assert classify(item()|{'title':title,'summary':''})[0] in ('P0','P1')

@pytest.mark.parametrize('title',['Futbol maç sonucu','KAP bilanço duyurusu','Türkiye hisse için hedef fiyat','DKB duyurusu'])
def test_remaining_filter_exclusions(title):assert classify(item()|{'title':title,'summary':''})[0] not in ('P0','P1')

def test_card_arrives_without_evidence_or_model_and_click_is_bound(db):
    a,click,tg=card(db)
    assert 'Tweet oluştur'==tg.calls[0][1]['reply_markup']['inline_keyboard'][1][0]['text'].split(' ',1)[1]
    assert db.conn.execute('SELECT count(*) FROM habnews_event').fetchone()[0]==0
    assert db.conn.execute('SELECT count(*) FROM habnews_budget').fetchone()[0]==0
    assert db.conn.execute("SELECT count(*) FROM habnews_queue WHERE kind IN ('llm','research')").fetchone()[0]==0
    db.set_state('llm_state','ready');reply=feed_callback(db,a,click,[source()]);assert 'kaydedildi' in reply
    queued=db.conn.execute("SELECT payload FROM habnews_queue WHERE kind='research'").fetchone()
    assert json.loads(queued[0])['manual'] is True
    assert feed_callback(db,a,click,[source()])=='duplicate'
    click['update_id']=100;assert 'zaten' in feed_callback(db,a,click,[source()])

def test_card_rejects_wrong_user_and_message(db):
    a,click,_=card(db);click['callback_query']['from']['id']=456
    with pytest.raises(PermissionError):feed_callback(db,a,click,[source()])
    click['callback_query']['from']['id']=123;click['callback_query']['message']['message_id']=999
    assert feed_callback(db,a,click,[source()])=='stale'
    assert db.conn.execute('SELECT count(*) FROM habnews_event').fetchone()[0]==0

@pytest.mark.parametrize('outcome',['failed','rejected'])
def test_button_can_regenerate_failed_or_rejected_request(db,outcome):
    a,click,_=card(db);db.set_state('llm_state','ready');feed_callback(db,a,click,[source()])
    first=db.conn.execute("SELECT id,identity FROM habnews_queue WHERE kind='research'").fetchone()
    db.conn.execute("UPDATE habnews_queue SET status='needs_review' WHERE id=?",(first['id'],))
    if outcome=='rejected':db.conn.execute("UPDATE habnews_event SET status='rejected'")
    click['update_id']=100;assert 'kaydedildi' in feed_callback(db,a,click,[source()])
    assert db.conn.execute('SELECT version FROM habnews_event').fetchone()[0]==2
    assert db.conn.execute("SELECT count(DISTINCT identity) FROM habnews_queue WHERE kind='research'").fetchone()[0]==2
    assert db.conn.execute('SELECT count(*) FROM habnews_event').fetchone()[0]==1
    assert db.conn.execute('SELECT count(*) FROM habnews_budget').fetchone()[0]==0

def test_button_returns_existing_ready_draft_without_new_model_request(db):
    from habnews.db import encode
    a,click,_=card(db);db.set_state('llm_state','ready');feed_callback(db,a,click,[source()])
    eid=db.conn.execute('SELECT id FROM habnews_event').fetchone()[0]
    db.conn.execute("UPDATE habnews_queue SET status='done' WHERE kind='research'")
    db.conn.execute('INSERT INTO habnews_draft VALUES(?,?,?,?,?,?,?,?,?,?)',('TEST-READY',eid,1,1,0,'TEST-HASH','TEST hazır taslak',encode({'delivery_contract':'article-photo-v1','editorial_version':'source-grounded-v2'}),'pending',time.time()))
    click['update_id']=100;assert 'TEST hazır taslak' in feed_callback(db,a,click,[source()])
    assert db.conn.execute('SELECT version FROM habnews_event').fetchone()[0]==1
    assert db.conn.execute("SELECT count(*) FROM habnews_queue WHERE kind='research'").fetchone()[0]==1

def test_legacy_preview_draft_is_rebuilt_on_a_new_owner_click(db):
    from habnews.db import encode
    a,click,_=card(db);db.set_state('llm_state','ready');feed_callback(db,a,click,[source()])
    eid=db.conn.execute('SELECT id FROM habnews_event').fetchone()[0]
    db.conn.execute("UPDATE habnews_queue SET status='done' WHERE kind='research'")
    db.conn.execute('INSERT INTO habnews_draft VALUES(?,?,?,?,?,?,?,?,?,?)',('LEGACY',eid,1,1,0,'OLD','TEST eski link taslağı',encode({}),'pending',time.time()))
    click['update_id']=100;assert 'kaydedildi' in feed_callback(db,a,click,[source()])
    assert db.conn.execute('SELECT version FROM habnews_event').fetchone()[0]==2
    assert db.conn.execute("SELECT status FROM habnews_draft WHERE id='LEGACY'").fetchone()[0]=='stale'
    assert db.conn.execute("SELECT count(*) FROM habnews_queue WHERE kind='research'").fetchone()[0]==2

def test_photo_draft_repeated_click_does_not_send_a_plain_text_duplicate(db):
    from habnews.db import encode
    a,click,_=card(db);db.set_state('llm_state','ready');feed_callback(db,a,click,[source()])
    eid=db.conn.execute('SELECT id FROM habnews_event').fetchone()[0]
    db.conn.execute("UPDATE habnews_queue SET status='done' WHERE kind='research'")
    db.conn.execute('INSERT INTO habnews_draft VALUES(?,?,?,?,?,?,?,?,?,?)',('PHOTO',eid,1,1,1,'HASH','TEST fotoğraflı taslak',encode({'image':{'path':'private-fixture'},'delivery_contract':'article-photo-v1','editorial_version':'source-grounded-v2'}),'pending',time.time()))
    db.conn.execute("INSERT INTO habnews_outbox(id,draft_id,recipient,part,method,payload,status,next_at,message_id,created) VALUES(?,?,?,?,?,?,?,?,?,?)",('photo-receipt','PHOTO',123,0,'sendPhoto','{}','sent',time.time(),102,time.time()))
    click['update_id']=100;response=feed_callback(db,a,click,[source()])
    assert 'fotoğrafıyla' in response and not response.startswith('Hazırlanan taslak:')
    assert db.conn.execute('SELECT version FROM habnews_event').fetchone()[0]==1

def test_old_failure_does_not_notify_after_user_starts_new_version(db):
    from habnews.live_feed import notify_manual_failures
    a,click,_=card(db);db.set_state('llm_state','ready');feed_callback(db,a,click,[source()])
    db.conn.execute("UPDATE habnews_queue SET status='needs_review' WHERE kind='research'")
    click['update_id']=100;feed_callback(db,a,click,[source()]);before=db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]
    notify_manual_failures(db,a)
    assert db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]==before

def test_stop_prevents_manual_job_without_consuming_button(db):
    a,click,_=card(db);db.set_state('enabled','false')
    assert 'durdurulmuş' in feed_callback(db,a,click,[source()])
    assert db.conn.execute('SELECT used FROM habnews_feed_callback').fetchone()[0]==0

def test_rss_only_still_sends_live_card_but_no_article_job(db):
    src=source()|{'article_access':'blocked_http_403'};a,click,tg=card(db,src)
    db.set_state('llm_state','ready');assert '403' in feed_callback(db,a,click,[src])
    assert len(tg.calls)==1
    assert db.conn.execute('SELECT count(*) FROM habnews_event').fetchone()[0]==0

def test_card_expiration_at_send(db):
    src=source();c=Collector(db,[src]);c.observe(src,[]);post=item();c.observe(src,[post]);a=Approval(db,123,123);process_live_feed(db,a,[src])
    post['published_at']-=2000;db.conn.execute('UPDATE habnews_observation SET metadata=?',(json.dumps(post),))
    tg=FakeTelegram();Outbox(db,tg).send_one();assert tg.calls==[]
    assert db.conn.execute('SELECT status FROM habnews_outbox').fetchone()[0]=='expired'

def xml(account='haskologlu',body='TEST Türkiye fon kurulu yatırımcıların haklarını koruyacak.',link=None,title='TEST Türkiye fon kurulu',timestamp=None):
    return f'<rss><channel><title>TEST / @{account}</title><item><title>{title}</title><link>{link or "https://nitter.cf/"+account+"/status/2107473772898820563"}</link><pubDate>{timestamp or formatdate(time.time(),usegmt=True)}</pubDate><description><![CDATA[<p>{body}</p><blockquote><b>OTHER</b><p>Fon tasfiye edildi</p></blockquote>]]></description></item></channel></rss>'.encode()

def test_social_own_text_excludes_quote_and_reply():
    s=source('haskologlu');posts=parse_social_feed(xml(body='TEST Türkiye fon kurulu.<br>Yeni açıklama.'),s)
    assert posts[0]['full_post']=='TEST Türkiye fon kurulu.\nYeni açıklama.'
    assert posts[0]['url'].startswith('https://x.com/haskologlu/status/')
    for data in [xml(link='https://nitter.cf/other/status/2107473772898820563'),xml(title='RT TEST'),xml(title='R to @test')]:
        with pytest.raises(ValueError,match='social_no_owned_posts'):parse_social_feed(data,s)

@pytest.mark.parametrize('data',[b'<html>login</html>',b'<!DOCTYPE rss><rss/>',xml(account='other'),xml(body=''),xml(timestamp='tomorrow')])
def test_social_invalid_feed_never_establishes_baseline(db,data):
    with pytest.raises(ValueError):parse_social_feed(data,source('haskologlu'))
    assert db.conn.execute('SELECT count(*) FROM habnews_source').fetchone()[0]==0

def test_social_baseline_and_manual_research_never_fetch_x(db,monkeypatch):
    s=source('haskologlu');p=parse_social_feed(xml(),s)[0]
    c=Collector(db,[s]);c.observe(s,[p]);assert db.conn.execute('SELECT count(*) FROM habnews_queue').fetchone()[0]==0
    p['provider_id']='2107473772898820564';p['url']='https://x.com/haskologlu/status/'+p['provider_id']
    c.observe(s,[p]);a=Approval(db,123,123);process_live_feed(db,a,[s]);Outbox(db,FakeTelegram()).send_one()
    record=db.conn.execute('SELECT nonce FROM habnews_feed_callback').fetchone();db.set_state('llm_state','ready')
    click={'update_id':11,'callback_query':{'id':'x','data':record[0],'from':{'id':123},'message':{'message_id':101,'chat':{'id':123,'type':'private'}}}}
    feed_callback(db,a,click,[s])
    def forbidden(*a,**k):raise AssertionError('Social post must not fetch X')
    monkeypatch.setattr('habnews.collector.Fetcher.get',forbidden);c.research_one()
    assert db.conn.execute('SELECT family FROM habnews_evidence').fetchone()[0]=='social:haskologlu'
    assert db.conn.execute("SELECT count(*) FROM habnews_queue WHERE kind='llm'").fetchone()[0]==1

def test_manual_single_source_pipeline_and_attribution(db,tmp_path,monkeypatch):
    a,click,_=card(db);db.set_state('llm_state','ready');feed_callback(db,a,click,[source()])
    sentence='Fon kurulu yatırımcıların haklarını koruyacak.';main=sentence+' Bu içerik sentetik bir TEST haberi olup gerçek olay değildir.'*5
    html=('<article><p>'+main+'</p></article>').encode()
    monkeypatch.setattr('habnews.collector.Fetcher.get',lambda *a,**k:(html,{'content-type':'text/html'},item()['url'],200))
    Collector(db,[source()]).research_one();broker=JobBroker(db,tmp_path/'jobs');broker.submit_one()
    job=json.loads(next((tmp_path/'jobs').glob('*.job.json')).read_text());assert job['manual_attribution']['owner']=='Foreks'
    def run(job,reasoning):
        fact={'text':sentence,'source_ref':job['evidence_refs'][0],'value_raw':None,'normalized_value':None,'unit':None,'currency':None,'scale':None,'period':None,'scope':None,'stage':'koruyacak','actor':'Fon kurulu','quote':sentence}
        result={'schema_version':'habnews-v1','event_id':job['event_id'],'event_version':1,'relevance_reason':'TEST','priority':'P1','verification_state':'attributed_single_source','facts':[fact],'ambiguities':[],'headline':'Fon kurulu yatırımcıları koruyacak','proposed_body':'Fon kurulu yatırımcıları koruyacak\n\n'+sentence,'verified_tags':[],'image_candidates':[]}
        # Headline needs supported exact words too.
        result['headline']=sentence.rstrip('.');result['proposed_body']=result['headline']+'\n\n'+sentence
        meta={'requested_model':'gpt-6-luna','provider':'openai-codex','transport':'codex_responses','auth_source':'habnews_own_oauth','speed':'standard','server_model':None,'fixture':True}
        return {'result':result,'run_metadata':meta}
    monkeypatch.setattr('habnews.hermes.run_job',run);monkeypatch.setattr('habnews.images.CommonsCandidates.search',lambda *a:[])
    (tmp_path/'jobs/runtime-state.json').write_text('{"enabled":true}');Runner(tmp_path/'jobs').tick();broker.consume(a)
    draft=db.conn.execute('SELECT body,metadata FROM habnews_draft').fetchone()
    assert draft and draft['body'].startswith('📢 Fon kurulu')
    assert 'Kaynak: Foreks' in draft['body']
    assert json.loads(draft['metadata'])['verification']=='attributed_single_source'

def test_manual_request_preserves_original_publication_time():
    now=time.time();p=item()|{'published_at':now-3600,'manual_requested_at':now}
    assert fresh(p,now)[0];assert p['published_at']==now-3600
    assert not fresh(p,now+1900)[0]

def test_live_feed_readiness_does_not_require_model_or_daily_smoke(db,monkeypatch):
    from habnews.readiness import check_ready
    for key in ('isolation_verified','telegram_verified','sources_verified','output_cap_verified','live_acceptance_verified'):db.set_state(key,'true')
    db.set_state('llm_state','auth_required');monkeypatch.setattr('habnews.config.sources',lambda:[source()])
    assert check_ready(db,require_llm=False)==[]
    assert 'auth_required' in check_ready(db)

def test_social_draft_uses_explicit_author_quote_and_cannot_claim_official(prepared):
    from habnews.schema import ValidationError
    db,a,job,result,meta=prepared;url='https://x.com/haskologlu/status/2107473772898820563'
    payload=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0]);payload.update(url=url,source_id='x-haskologlu',manual_requested_at=time.time(),source_type='social_x',x_account='haskologlu')
    db.conn.execute('UPDATE habnews_event_version SET payload=?',(json.dumps(payload),))
    db.conn.execute("UPDATE habnews_evidence SET url=?,family='social:haskologlu',primary_source=0",(url,))
    job['manual_attribution']={'source_type':'social_x','owner':'X · @haskologlu','account':'haskologlu','url':url}
    result['verification_state']='attributed_single_source'
    did=a.create(job,result,meta);body=db.conn.execute('SELECT body FROM habnews_draft WHERE id=?',(did,)).fetchone()[0]
    assert body.startswith('📢 İbrahim Haskoloğlu, X hesabında')
    assert '“TCMB politika faizini yüzde 40 olarak belirledi.”' in body
    assert '#borsa' not in body
    result['verification_state']='official_primary'
    with pytest.raises(ValidationError,match='not_primary'):a.create(job,result,meta)

def test_missed_recent_observation_recovered_once_and_not_baseline(db):
    s=source()|{'delivery_mode':'verified_drafts'};c=Collector(db,[s]);c.observe(s,[item()|{'provider_id':'oldbaseline'}]);c.observe(s,[item()])
    assert enqueue_recent(db,[source()])==1
    assert enqueue_recent(db,[source()])==0
    assert db.conn.execute("SELECT count(*) FROM habnews_queue WHERE kind='live_feed'").fetchone()[0]==1
    a=Approval(db,123,123);process_live_feed(db,a,[source()]);Outbox(db,FakeTelegram()).send_one()
    record=db.conn.execute('SELECT nonce FROM habnews_feed_callback').fetchone();db.set_state('llm_state','ready')
    click={'update_id':11,'callback_query':{'id':'x','data':record[0],'from':{'id':123},'message':{'message_id':101,'chat':{'id':123,'type':'private'}}}}
    assert 'kaydedildi' in feed_callback(db,a,click,[source()])
    assert db.conn.execute('SELECT version FROM habnews_event').fetchone()[0]==2
    assert db.conn.execute('SELECT count(*) FROM habnews_event').fetchone()[0]==1

@pytest.mark.parametrize('attempt,expected',[(0,'repair_queued'),(2,'needs_review')])
def test_manual_repair_is_bounded_and_counts_known_call(prepared,tmp_path,monkeypatch,attempt,expected):
    from habnews.budget import Budget
    from habnews.db import encode
    db,a,job,result,meta=prepared
    payload=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0])
    payload.update(manual_requested_at=time.time(),source_id='foreks')
    db.conn.execute('UPDATE habnews_event_version SET payload=?',(encode(payload),))
    job.update(manual_attribution={'source_type':'article','owner':'Foreks','url':payload['url']},repair_attempt=attempt)
    result['proposed_body']='This unsupported body must never get delivered.'
    result['verification_state']='attributed_single_source'
    db.enqueue('llm','TEST-MANUAL-REPAIR',{'event_id':job['event_id'],'event_version':1});row=db.claim('llm')
    reservation=Budget(db).reserve(job['event_id'],'P0')
    broker=JobBroker(db,tmp_path/'jobs')
    db.set_state('job:'+row['id'],encode({'lease':row['lease'],'reservation':reservation,'job':job}))
    (broker.directory/(row['id']+'.result.json')).write_text(encode({'result':result,'run_metadata':meta}))
    monkeypatch.setattr('habnews.images.CommonsCandidates.search',lambda *a:[])
    broker.consume(a)
    assert db.conn.execute("SELECT status FROM habnews_queue WHERE kind='llm'").fetchone()[0]==expected
    assert db.conn.execute('SELECT count(*) FROM habnews_draft').fetchone()[0]==0
    budget=db.conn.execute('SELECT actual,status FROM habnews_budget').fetchone();assert tuple(budget)==(1,'complete')
    assert db.conn.execute("SELECT count(*) FROM habnews_queue WHERE kind='research'").fetchone()[0]==(1 if attempt==0 else 0)
    if attempt==0:
        repair=db.conn.execute("SELECT identity,payload FROM habnews_queue WHERE kind='research'").fetchone()
        assert repair['identity']!=json.loads(repair['payload'])['llm_identity']
        main='TCMB politika faizini yüzde 40 olarak belirledi. Bu içerik sentetik TEST verisidir.'*5
        monkeypatch.setattr('habnews.collector.Fetcher.get',lambda *a,**k:(('<article><p>'+main+'</p></article>').encode(),{'content-type':'text/html'},payload['url'],200))
        Collector(db,[source()]).research_one()
        assert db.conn.execute("SELECT count(*) FROM habnews_queue WHERE kind='llm' AND status='pending'").fetchone()[0]==1
