import io,json,time
from pathlib import Path
import pytest
from PIL import Image
from habnews.article import extract_document
from habnews.schema import validate_result,ValidationError,complete_source_sentence
from habnews.images import matched_official_archive,store_image
from habnews.db import encode
from habnews.hermes import JobBroker,atomic_file
from habnews.budget import Budget
from habnews.telegram import Outbox,TelegramError,MediaError

TEXT='TEST Merkez Bankası, koşullar sağlanırsa düzenleme yapılacağını açıkladı. Bu bilgi sentetik bir kaynak metnidir.'

@pytest.mark.parametrize('host,css',[
    ('www.foreks.com','Detay'),('www.haberturk.com','cms-container'),
    ('www.ntv.com.tr','ck-content'),('tr.euronews.com','c-article-content')])
def test_publisher_scopes_exclude_widgets_and_related_headlines(host,css):
    html=f'<article property="articleBody"><h1>TEST</h1><div class="{css}"><p>{TEXT}</p><aside><p>UNRELATED</p></aside></div><div class="widget-bottom-navigation"><p>BUTTONS</p></div><div class="footer-news"><p>DISCLAIMER</p></div><article><h2>WRONG ARTICLE</h2><p>UNRELATED</p></article></article>'
    d=extract_document(html.encode(),'text/html','https://'+host+'/story')
    assert d['body']==TEXT

def test_canonical_mismatch_does_not_read_other_story():
    html=f'<link rel="canonical" href="https://example.org/other"><article><p>{TEXT}</p></article>'
    with pytest.raises(ValueError,match='article_url_mismatch'):extract_document(html.encode(),'text/html','https://example.org/chosen')

def test_jsonld_for_different_article_is_rejected():
    html='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','url':'https://example.org/other','articleBody':TEXT})+'</script>'
    with pytest.raises(ValueError,match='main_text_missing'):extract_document(html.encode(),'text/html','https://example.org/chosen')

def test_multiple_articles_require_identity_match():
    html=f'<article data-url="/wrong"><h1>Wrong</h1><p>{TEXT}</p></article><article data-url="/chosen"><h1>Chosen</h1><p>{TEXT}</p></article>'
    assert extract_document(html.encode(),'text/html','https://example.org/chosen')['title']=='Chosen'
    with pytest.raises(ValueError,match='multiple_articles'):extract_document(html.encode(),'text/html','https://example.org/unknown')

def test_redirect_to_unrelated_homepage_rejected():
    html=f'<link rel="canonical" href="https://example.org/new"><article><h1>Futbol sonuçları</h1><p>{TEXT}</p></article>'
    with pytest.raises(ValueError,match='article_title_mismatch'):
        extract_document(html.encode(),'text/html','https://example.org/new','TCMB faiz kararı','https://example.org/chosen')

def test_ntv_multiple_body_segments_are_kept_without_tags():
    html=f'<h1>TEST</h1><div property="articleBody"><div class="ck-content"><p>{TEXT}</p></div><div class="ck-content"><p>İkinci paragraf da bu haberin kendi içeriğidir.</p></div><ul><li>Yanlış etiket</li></ul></div>'
    d=extract_document(html.encode(),'text/html','https://www.ntv.com.tr/story')
    assert 'İkinci paragraf' in d['body'] and 'Yanlış etiket' not in d['body']

@pytest.mark.parametrize('text,ok',[
 ('Kurul tasfiyeye karar verdi.',False),
 ('Kurul tasfiyeye karar verdiği iddiasını yalanladı.',True),
 ('yatırımcılar ödeme alacak',False),
 ('Koşullar sağlanırsa yatırımcılar ödeme alacak.',True)])
def test_qualifiers_and_denials_cannot_be_clipped(text,ok):
    source='Kurul tasfiyeye karar verdiği iddiasını yalanladı. Koşullar sağlanırsa yatırımcılar ödeme alacak.'
    assert complete_source_sentence(text,source)==ok

def test_rearranged_headline_cannot_pass_word_membership(prepared):
    db,_,j,r,_=prepared;j['content_contract']='article-v2';j['source_title']='TEST TCMB politika faizi'
    r['headline']='yüzde 40 TCMB olarak belirledi';r['proposed_body']=r['headline']+'\n\n'+r['facts'][0]['text']
    ev={x['id']:dict(x) for x in db.conn.execute('SELECT * FROM habnews_evidence')}
    with pytest.raises(ValidationError,match='headline_not_source_phrase'):validate_result(r,j,ev)

def test_headline_amount_requires_selected_fact_support(prepared):
    db,_,j,r,_=prepared;j['content_contract']='article-v2'
    r['headline']='TEST 800 milyar TL mevduat';r['proposed_body']=r['headline']+'\n\n'+r['facts'][0]['text'];j['source_title']=r['headline']
    ev={x['id']:dict(x) for x in db.conn.execute('SELECT * FROM habnews_evidence')}
    ev['evidence-1']['passage']+='\n'+r['headline']
    with pytest.raises(ValidationError,match='headline_unbound_number'):validate_result(r,j,ev)

def test_nested_blocks_preserve_word_boundaries_without_duplicate_text():
    html=f'<article><h1>TEST</h1><ul><li><p>{TEXT}</p><p>İkinci madde.</p></li></ul></article>'
    body=extract_document(html.encode(),'text/html')['body']
    assert body==TEXT+' İkinci madde.'

def test_incidental_person_mention_never_selects_archive(tmp_path,monkeypatch):
    monkeypatch.setattr('habnews.images.store_image',lambda *a:pytest.fail('incidental person image fetched'))
    assert matched_official_archive('IMF küresel büyüme tahmini',tmp_path,article_body='Toplantıya Fatih Karahan da katıldı.') is None
    assert matched_official_archive('Oyuncu Karahan yeni filmde',tmp_path,article_body='Kültür haberi.') is None
    assert matched_official_archive('Fatih Karahan adı geçen kültür haberi',tmp_path,article_body='Kurum bağlantısı bulunmayan metin.') is None

def test_main_subject_archive_is_bound_to_audited_asset(tmp_path,monkeypatch):
    seen=[]
    def store(record,*args):seen.append(record);return tmp_path/'photo.jpg',record
    monkeypatch.setattr('habnews.images.store_image',store)
    assert matched_official_archive('TCMB Başkanı Karahan açıklama yaptı',tmp_path)
    assert len(seen[0]['expected_sha256'])==64 and seen[0]['event_match'] is False

def test_curated_photo_replacement_is_rejected(tmp_path,monkeypatch):
    out=io.BytesIO();Image.new('RGB',(200,200),'white').save(out,format='JPEG')
    monkeypatch.setattr('habnews.images.Fetcher.get',lambda *a:(out.getvalue(),{'content-type':'image/jpeg'},'url',200))
    with pytest.raises(ValueError,match='curated_image_changed'):matched_official_archive('TCMB Başkanı Fatih Karahan',tmp_path)

def test_corrupted_maintext_never_reaches_model(prepared,tmp_path):
    from habnews.normalizer import digest
    db,_,job,_,_=prepared;db.set_state('llm_state','ready')
    item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0]);item.update(manual_requested_at=time.time(),source_id='foreks')
    db.conn.execute('UPDATE habnews_event_version SET payload=?',(encode(item),))
    ev=db.conn.execute('SELECT * FROM habnews_evidence').fetchone();root=db.path.parent/'maintext';root.mkdir()
    atomic_file(root/(ev['id']+'.json'),{'text':'A different, corrupted article','digest':ev['digest'],'expires_at':time.time()+300})
    db.enqueue('llm','tamper-check',job);broker=JobBroker(db,tmp_path/'jobs');broker.submit_one()
    assert not list(broker.directory.glob('*.job.json'))
    assert db.conn.execute("SELECT status FROM habnews_queue WHERE kind='llm'").fetchone()[0]=='refresh_queued'
    assert db.conn.execute('SELECT sum(reserved) FROM habnews_budget').fetchone()[0]==0

def test_photo_hash_is_checked_before_request(tmp_path,monkeypatch):
    from habnews.telegram import Telegram
    photo=tmp_path/'test.jpg';photo.write_bytes(b'changed')
    real_path=Path
    monkeypatch.setattr('habnews.telegram.Path',lambda p:tmp_path if p=='/data/media' else real_path(p))
    class Connection:
        def __init__(self,*a,**k):pass
        def request(self,*a,**k):pytest.fail('corrupted file sent')
        def close(self):pass
    monkeypatch.setattr('habnews.telegram.http.client.HTTPSConnection',Connection)
    with pytest.raises(MediaError,match='upload_digest'):
        Telegram('123:fixture').call('sendPhoto',{'chat_id':123,'file_path':str(photo),'file_sha256':'0'*64})

def test_stalled_model_releases_reservation_without_replaying(db,tmp_path):
    db.set_state('llm_state','ready');db.enqueue('llm','stalled',{'event_id':'e','event_version':1});row=db.claim('llm')
    reservation=Budget(db).reserve('e','P0');rid=row['id'];broker=JobBroker(db,tmp_path/'jobs')
    job={'job_id':rid,'event_id':'e','event_version':1,'deadline':time.time()-90,'evidence_refs':[]}
    db.set_state('job:'+rid,encode({'job':job,'reservation':reservation,'lease':row['lease']}));atomic_file(broker.directory/(rid+'.job.running'),job)
    broker.reap_stalled()
    assert db.conn.execute('SELECT status FROM habnews_budget').fetchone()[0]=='uncertain'
    assert db.conn.execute('SELECT status FROM habnews_queue').fetchone()[0]=='uncertain'
    assert db.state('llm_state')=='ready' and not list(broker.directory.iterdir())
    assert Budget(db).reserve('next','P0')

def test_one_failed_model_job_does_not_pause_global_model(db,tmp_path):
    db.set_state('llm_state','ready');db.enqueue('llm','broken',{});row=db.claim('llm');rid=row['id']
    reservation=Budget(db).reserve('e','P0');broker=JobBroker(db,tmp_path/'jobs')
    db.set_state('job:'+rid,encode({'lease':row['lease'],'reservation':reservation,'job':{'job_id':rid,'deadline':time.time()+100,'evidence_refs':[]}}))
    atomic_file(broker.directory/(rid+'.result.json'),{'error':'needs_review'})
    broker.consume(None)
    assert db.state('llm_state')=='ready'
    assert db.conn.execute('SELECT status FROM habnews_budget').fetchone()[0]=='uncertain'

@pytest.mark.parametrize('failure',[TelegramError(400),MediaError('hash')])
def test_photo_rejection_delivers_one_text_fallback(prepared,failure):
    db,a,j,r,m=prepared;j['quiet_delivery']=True;did=a.create(j,r,m)
    meta=json.loads(db.conn.execute('SELECT metadata FROM habnews_draft WHERE id=?',(did,)).fetchone()[0]);meta['manual_attribution']={'source_type':'article'}
    db.conn.execute('UPDATE habnews_draft SET metadata=? WHERE id=?',(encode(meta),did))
    db.conn.execute("UPDATE habnews_outbox SET method='sendPhoto' WHERE draft_id=?",(did,))
    class Transport:
        def __init__(self):self.calls=[]
        def call(self,method,payload):
            self.calls.append((method,payload))
            if method=='sendPhoto':raise failure
            return {'message_id':999}
    t=Transport();out=Outbox(db,t);out.send_one();out.send_one();out.send_one()
    assert [c[0] for c in t.calls]==['sendPhoto','sendMessage']
    assert db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]==1
    assert t.calls[1][1]['text']==db.conn.execute('SELECT body FROM habnews_draft WHERE id=?',(did,)).fetchone()[0]

def test_uncertain_photo_send_is_not_repeated_as_text(prepared):
    db,a,j,r,m=prepared;j['quiet_delivery']=True;did=a.create(j,r,m);db.conn.execute("UPDATE habnews_outbox SET method='sendPhoto'")
    class Transport:
        def call(self,*args):raise TelegramError(0)
    out=Outbox(db,Transport());out.send_one();out.send_one()
    assert db.conn.execute('SELECT status FROM habnews_outbox').fetchone()[0]=='uncertain'
