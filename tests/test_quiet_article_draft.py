import hashlib,json,time
from decimal import Decimal,InvalidOperation
import pytest
from habnews.article import extract_document
from habnews.schema import numeric_value
from habnews.hermes import JobBroker
from habnews.budget import Budget
from habnews.telegram import ApprovalService

@pytest.mark.parametrize('raw,want',[('455 bin 578','455578'),('1 milyon','1000000'),('87,5 milyar','87500000000'),('455.578','455578'),('1.234,56','1234.56'),('yüzde 40','40'),('1 milyon 200 bin 30','1200030'),("800 milyar TL'nin üzerinde",'800000000000')])
def test_turkish_numbers(raw,want):assert numeric_value(raw)==Decimal(want)

@pytest.mark.parametrize('raw',['455 foo 578','bin 578','455 578',''])
def test_ambiguous_numeric_strings_are_not_guessed(raw):
    with pytest.raises(InvalidOperation):numeric_value(raw)

def test_exact_article_body_excludes_other_stories_and_keeps_short_facts():
    html='''<html><meta property="og:image" content="https://images.example/news.jpg"><main>
    <p>Outside market commentary must not be read.</p><article><h1>Fon tasfiyesi teklifi</h1>
    <div class="article-wrapper"><p>455 bin 578 yatırımcının 1 milyon liraya kadar olan varlıkları teklifin kapsamında değerlendirilecek.</p><p>Teklif 10 maddeden oluşuyor.</p>
    <aside><p>IGNORE aside</p></aside><div class="related-news"><p>IGNORE related company scandal</p></div></div>
    <p>IGNORE footer paragraph outside body</p></article>
    <article><p>IGNORE next automatically loaded news article</p></article></main></html>'''
    d=extract_document(html.encode(),'text/html','https://publisher.example/story')
    assert d['title']=='Fon tasfiyesi teklifi';assert '10 maddeden' in d['body'];assert 'IGNORE' not in d['body'];assert 'Outside' not in d['body']
    assert d['preview_url']=='https://publisher.example/story'

def test_property_articlebody_and_jsonld_fallback():
    text='Bu haber yalnızca kendisine ait ana metin alanından okunmalıdır; menü ve önerilen haberler dışarıda kalmalıdır.'
    d=extract_document(('<main><h1>TEST</h1><div property="articleBody"><p>'+text+'</p></div><p>IGNORE</p></main>').encode(),'text/html')
    assert d['body']==text
    data='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','headline':'TEST','articleBody':text})+'</script>'
    assert extract_document(data.encode(),'text/html')['body']==text

def test_manual_quiet_draft_without_photo_is_one_plain_message(prepared):
    db,a,j,r,m=prepared;j.update(quiet_delivery=True,preview_url='https://www.tcmb.gov.tr/test')
    did=a.create(j,r,m);rows=db.conn.execute('SELECT payload FROM habnews_outbox WHERE draft_id=?',(did,)).fetchall()
    assert len(rows)==1;p=json.loads(rows[0][0]);assert p['text']==db.conn.execute('SELECT body FROM habnews_draft WHERE id=?',(did,)).fetchone()[0]
    assert 'reply_markup' not in p
    assert p['link_preview_options']=={'is_disabled':True}
    assert 'text_only' not in p['text'] and 'habnews' not in p['text']

def test_verified_archive_is_sent_as_one_telegram_photo(prepared,tmp_path,monkeypatch):
    import habnews.approval as approval_module
    from habnews.images import reusable
    db,a,j,r,m=prepared;j.update(quiet_delivery=True,preview_url='https://www.tcmb.gov.tr/test')
    monkeypatch.setattr(approval_module,'MEDIA_ROOT',tmp_path)
    photo=tmp_path/'official.jpg';data=b'fixture-photo-bytes';photo.write_bytes(data)
    provenance={
        'landing_page_url':'https://www.flickr.com/photos/merkez_bankasi/55462088240/',
        'original_asset_url':'https://live.staticflickr.com/65535/55462088240_2fb7910355_b.jpg',
        'publisher':'TCMB','creator':'TCMB','license_name':'TCMB official Flickr reuse',
        'license_version':None,'license_url':'https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Sosyal+Medya',
        'rights_evidence':'TCMB permission','attribution_text':'Fotoğraf: TCMB',
        'restrictions':[],'retrieved_at':time.time(),'photographed_at':'2026-08-13',
        'subject_match':True,'event_match':False,'archive_or_current':'archive',
        'confidence_reason':'curated','rights_status':'verified_reusable',
        'sha256':hashlib.sha256(data).hexdigest()}
    assert reusable(provenance)
    did=a.create(j,r,m,image={'version':1,'path':str(photo),'provenance':provenance})
    rows=db.conn.execute('SELECT method,payload FROM habnews_outbox WHERE draft_id=?',(did,)).fetchall()
    assert len(rows)==1 and rows[0][0]=='sendPhoto'
    payload=json.loads(rows[0][1])
    assert payload['file_path']==str(photo)
    assert payload['file_sha256']==provenance['sha256']
    assert payload['show_caption_above_media'] is True
    assert payload['caption'].startswith(db.conn.execute('SELECT body FROM habnews_draft WHERE id=?',(did,)).fetchone()[0])
    assert 'arşiv fotoğrafı' in payload['caption']
    assert payload['caption'].startswith('📢 ')
    assert '📷' not in payload['caption']
    assert 'link_preview_options' not in payload

def test_manual_tags_include_topic_in_selected_source_title(prepared):
    from habnews.schema import validate_result
    db,_,job,result,_=prepared
    job=job|{'manual_attribution':{'source_type':'article','owner':'TEST','url':'https://www.tcmb.gov.tr/test'},'source_title':'TCMB fon tasfiyesi'}
    evidence={r['id']:dict(r) for r in db.conn.execute('SELECT * FROM habnews_evidence')}
    text=validate_result(result,job,evidence)
    assert '#fon #TCMB #faiz' in text

def test_busy_model_waits_without_claim_attempt_or_incident(db,tmp_path):
    db.set_state('llm_state','ready');Budget(db).reserve('running','P0');db.enqueue('llm','second-request',{})
    JobBroker(db,tmp_path/'jobs').submit_one()
    row=db.conn.execute("SELECT attempts,status FROM habnews_queue WHERE identity='second-request'").fetchone()
    assert tuple(row)==(0,'pending');assert not db.health()['incidents']

def test_internal_incidents_are_not_pushed(prepared):
    db,a,*_=prepared;db.incident('llm_concurrency_limit','internal diagnostic')
    class NoSend:
        def call(self,*args):raise AssertionError('must not push internal diagnostics')
    ApprovalService(db,a,NoSend(),123).notify_incidents()
    assert db.state('incident_notice:llm_concurrency_limit')=='open'

def test_expired_manual_text_is_refetched_without_model_charge(prepared,tmp_path,monkeypatch):
    from habnews.collector import Collector
    from habnews.config import sources
    db,a,j,r,m=prepared;item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0]);item.update(manual_requested_at=time.time(),source_id='foreks')
    db.conn.execute('UPDATE habnews_event_version SET payload=?',(json.dumps(item),));db.set_state('llm_state','ready')
    db.enqueue('llm','TEST-expired',{'event_id':j['event_id'],'event_version':1})
    broker=JobBroker(db,tmp_path/'jobs');broker.submit_one()
    assert db.conn.execute("SELECT status FROM habnews_queue WHERE kind='llm'").fetchone()[0]=='refresh_queued'
    assert db.conn.execute('SELECT sum(reserved) FROM habnews_budget').fetchone()[0]==0
    html=('<article><h1>TEST TCMB</h1><p>'+('TEST TCMB politika faizini yüzde 40 olarak belirledi. '*5)+'</p></article>').encode()
    monkeypatch.setattr('habnews.collector.Fetcher.get',lambda *a,**k:(html,{'content-type':'text/html'},item['url'],200))
    src=next(s for s in sources() if s['stable_id']=='foreks')|{'enabled':True};Collector(db,[src]).research_one();broker.submit_one()
    assert len(list((tmp_path/'jobs').glob('*.job.json')))==1
    assert db.conn.execute('SELECT count(*) FROM habnews_evidence WHERE tombstone=0').fetchone()[0]==1
