import hashlib,io,json,time
from pathlib import Path
import pytest
from PIL import Image
from habnews.article import extract_document
from habnews.article_media import article_photo,private_preview,media_hosts
from habnews.images import reusable
from habnews.db import encode

PAGE='https://www.ekonomim.com/ekonomi/test-haberi-123'
ASSET='https://img.ekonomim.com/storage/news.webp'
BODY='Türkiye ekonomisi hakkında yalnız bu haberin ana metninde yer alan, yeterince uzun ve doğrulanabilir bir açıklama.'
SOURCE={'stable_id':'ekonomim','source_family':'ekonomim','owner':'Ekonomim','enabled':True,'allowed_hosts':['www.ekonomim.com'],'priority':'B'}

def picture(size=(640,360),fmt='WEBP'):
    out=io.BytesIO();Image.new('RGB',size,(38,75,120)).save(out,format=fmt);return out.getvalue()

def document():return {'title':'Türkiye ekonomisi','body':BODY,'source_url':PAGE,'image_url':ASSET}

def private_photo(tmp_path,monkeypatch,doc=None):
    monkeypatch.setattr('habnews.article_media.Fetcher.get',lambda *a,**k:(picture(),{'content-type':'image/webp'},ASSET,200))
    return article_photo(doc or document(),SOURCE,tmp_path)

def test_article_picture_fallback_avoids_logo_and_foreign_structured_article():
    obj={'@type':'NewsArticle','url':'https://www.ekonomim.com/other','image':'https://img.ekonomim.com/wrong.jpg'}
    html='<link rel="canonical" href="'+PAGE+'"><meta property="og:image" content="/logo.png"><meta name="twitter:image" content="'+ASSET+'"><script type="application/ld+json">'+json.dumps(obj)+'</script><article><h1>Türkiye ekonomisi</h1><p>'+BODY+'</p><aside><img src="/related.jpg"></aside></article>'
    doc=extract_document(html.encode(),'text/html',PAGE)
    assert doc['image_url']==ASSET
    assert doc['image_candidates']==[{'url':ASSET,'method':'twitter:image'}]

def test_second_article_cannot_borrow_first_articles_metadata():
    html='<meta property="og:image" content="https://img.ekonomim.com/wrong.jpg"><article data-url="https://www.ekonomim.com/other"><h1>Other</h1><p>'+BODY+'</p></article><article data-url="'+PAGE+'"><h1>Türkiye ekonomisi</h1><img src="'+ASSET+'"><p>'+BODY+'</p></article>'
    doc=extract_document(html.encode(),'text/html',PAGE)
    assert doc['image_candidates']==[{'url':ASSET,'method':'article:img'}]

@pytest.mark.parametrize('bad',['http://img.ekonomim.com/a.jpg','https://user:pass@img.ekonomim.com/a.jpg','https://img.ekonomim.com:bad/a.jpg','data:image/png;base64,xxx'])
def test_invalid_image_metadata_does_not_break_valid_article(bad):
    html='<meta property="og:image" content="'+bad+'"><article><h1>Türkiye ekonomisi</h1><p>'+BODY+'</p></article>'
    doc=extract_document(html.encode(),'text/html',PAGE)
    assert doc['body']==BODY and not doc['image_url']

def test_publisher_webp_becomes_real_private_jpeg_without_claiming_reuse(tmp_path,monkeypatch):
    media=private_photo(tmp_path,monkeypatch)
    assert media and private_preview(media['provenance']) and not reusable(media['provenance'])
    path=Path(media['path']);assert path.read_bytes().startswith(b'\xff\xd8\xff')
    with Image.open(path) as im:assert im.format=='JPEG' and im.size==(640,360) and not im.getexif()
    assert media['provenance']['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    assert media['provenance']['source_mime']=='image/webp'
    assert path.stat().st_mode&0o777==0o600

def test_foreign_cdn_and_disabled_source_are_never_contacted(tmp_path,monkeypatch):
    monkeypatch.setattr('habnews.article_media.Fetcher.get',lambda *a,**k:pytest.fail('unexpected host fetched'))
    assert article_photo(document()|{'image_url':'https://evil.example/news.jpg'},SOURCE,tmp_path) is None
    assert article_photo(document(),SOURCE|{'enabled':False},tmp_path) is None
    assert 'img.ekonomim.com' not in media_hosts([SOURCE|{'enabled':False}])

@pytest.mark.parametrize('raw,mime',[(b'<html>not a photo</html>','image/jpeg'),(picture((16,16)),'image/webp'),(picture(),'text/html')])
def test_spoofed_or_tiny_pictures_do_not_enter_private_store(tmp_path,monkeypatch,raw,mime):
    monkeypatch.setattr('habnews.article_media.Fetcher.get',lambda *a,**k:(raw,{'content-type':mime},ASSET,200))
    assert article_photo(document(),SOURCE,tmp_path) is None
    assert not list(tmp_path.glob('*.jpg'))

def prepare_bound_media(prepared,tmp_path,monkeypatch):
    db,a,j,r,m=prepared
    passage=db.conn.execute('SELECT passage FROM habnews_evidence').fetchone()[0]
    # Its exact title/body join is bound to the already-verified evidence digest.
    doc={'title':'','body':passage,'source_url':PAGE,'image_url':ASSET}
    media=private_photo(tmp_path,monkeypatch,doc)
    db.conn.execute('UPDATE habnews_evidence SET url=?',(PAGE,))
    item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0]);item.update(url=PAGE,manual_requested_at=time.time())
    db.conn.execute('UPDATE habnews_event_version SET payload=?',(encode(item),))
    j.update(quiet_delivery=True,manual_attribution={'source_type':'article','owner':'Ekonomim','url':PAGE},preview_url=PAGE)
    monkeypatch.setattr('habnews.approval.MEDIA_ROOT',tmp_path)
    return db,a,j,r,m,media

def test_draft_is_one_uploaded_photo_with_exact_tweet_caption(prepared,tmp_path,monkeypatch):
    db,a,j,r,m,media=prepare_bound_media(prepared,tmp_path,monkeypatch)
    did=a.create(j,r,m,image=media)
    row=db.conn.execute('SELECT method,payload FROM habnews_outbox WHERE draft_id=?',(did,)).fetchone();payload=json.loads(row['payload'])
    assert row['method']=='sendPhoto' and payload['file_path']==media['path']
    assert payload['caption']==db.conn.execute('SELECT body FROM habnews_draft WHERE id=?',(did,)).fetchone()[0]
    assert payload['show_caption_above_media'] and payload['reply_markup']['inline_keyboard'][0][0]['url']==PAGE
    assert 'link_preview_options' not in payload
    assert db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]==1

def test_picture_from_different_article_cannot_accompany_verified_tweet(prepared,tmp_path,monkeypatch):
    db,a,j,r,m,media=prepare_bound_media(prepared,tmp_path,monkeypatch)
    media['provenance']['article_digest']='0'*64
    did=a.create(j,r,m,image=media)
    row=db.conn.execute('SELECT method,payload FROM habnews_outbox WHERE draft_id=?',(did,)).fetchone()
    assert row['method']=='sendMessage' and json.loads(row['payload'])['link_preview_options']=={'is_disabled':True}
    assert json.loads(db.conn.execute('SELECT metadata FROM habnews_draft WHERE id=?',(did,)).fetchone()[0])['image'] is None

def test_private_preview_cannot_enter_automatic_or_publication_package(prepared,tmp_path,monkeypatch):
    from habnews.editorial import export_approved
    db,a,j,r,m,media=prepare_bound_media(prepared,tmp_path,monkeypatch)
    with pytest.raises(ValueError,match='media_not_verified'):a.create(j|{'quiet_delivery':False},r,m,image=media)
    did=a.create(j,r,m,image=media)
    row=db.conn.execute('SELECT hash FROM habnews_draft WHERE id=?',(did,)).fetchone()
    db.conn.execute("UPDATE habnews_draft SET status='approved' WHERE id=?",(did,))
    db.conn.execute('INSERT INTO habnews_decision VALUES(?,?,?,?,?,?,?)',('decision',did,row['hash'],123,'approve','private_source_preview',time.time()))
    export_approved(db,did,tmp_path/'export')
    assert not list((tmp_path/'export').glob('original*'))
    assert 'yeniden yayınlama izni' in (tmp_path/'export/attribution.txt').read_text()

def test_collector_binds_downloaded_photo_to_the_exact_maintext(prepared,tmp_path,monkeypatch):
    from habnews.collector import Collector
    db,a,j,r,m=prepared
    item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0]);item.update(url=PAGE,source_id='ekonomim',manual_requested_at=time.time())
    html=('<link rel="canonical" href="'+PAGE+'"><meta property="og:image" content="'+ASSET+'"><article><h1>TEST TCMB politika faizi</h1><p>'+BODY+'</p></article>').encode()
    def fetch(self,url,*args,**kwargs):
        return (html,{'content-type':'text/html'},url,200) if url==PAGE else (picture(),{'content-type':'image/webp'},ASSET,200)
    monkeypatch.setattr('habnews.collector.Fetcher.get',fetch)
    db.enqueue('research','manual-photo',{'event_id':j['event_id'],'event_version':1,'item':item,'source_id':'ekonomim','manual':True})
    Collector(db,[SOURCE]).research_one()
    spool=json.loads(next((tmp_path/'maintext').glob('*.json')).read_text())
    assert spool['media'] and spool['media']['provenance']['article_digest']==hashlib.sha256(spool['text'].encode()).hexdigest()
    assert db.conn.execute('SELECT rights FROM habnews_image_candidate').fetchone()[0]=='unknown'
    assert db.conn.execute("SELECT status FROM habnews_queue WHERE kind='research'").fetchone()[0]=='done'

def test_telegram_edits_use_multipart_photo_not_a_remote_link(tmp_path,monkeypatch):
    from habnews.telegram import Telegram
    raw=picture(fmt='JPEG');file=tmp_path/'news.jpg';file.write_bytes(raw);calls=[]
    monkeypatch.setattr('habnews.telegram.Path',lambda p:tmp_path if p=='/data/media' else Path(p))
    class Response:
        status=200
        def read(self,*args):return b'{"ok":true,"result":{"message_id":194,"photo":[{}]}}'
    class Connection:
        def __init__(self,*a,**k):pass
        def request(self,*a,**k):calls.append((a,k))
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr('habnews.telegram.http.client.HTTPSConnection',Connection)
    tg=Telegram('123:fixture');media={'type':'photo','media':'attach://photo','caption':'TEST taslak','show_caption_above_media':True}
    response=tg.call('editMessageMedia',{'chat_id':123,'message_id':194,'file_path':str(file),'file_sha256':hashlib.sha256(raw).hexdigest(),'media':media})
    body=calls[0][1]['body'];assert raw in body and b'name="photo"' in body and b'attach://photo' in body
    assert b'file_path' not in body and response['message_id']==194
    with pytest.raises(ValueError,match='private_chat_only'):tg.call('editMessageMedia',{'chat_id':-123})
