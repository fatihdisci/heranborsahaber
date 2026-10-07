import base64,gzip,hashlib,json,time
from pathlib import Path
import pytest
from habnews.approval import Approval
from habnews.collector import Collector
from habnews.editorial_prompt import EDITORIAL_RULES,model_policy
from habnews.gpt_export import gpt_callback,process_gpt_export,delivery_fallback
from habnews.live_feed import process_live_feed
from habnews.config import sources
from habnews.db import encode


def setup_export(db):
    source=next(s for s in sources() if s['stable_id']=='foreks')|{'enabled':True}
    item={'source_id':'foreks','provider_id':'export-test','url':'https://www.foreks.com/haber/test',
          'title':'TCMB politika faizini açıkladı','summary':'TEST kısa RSS özeti.',
          'published_at':time.time(),'first_seen_at':time.time(),'time_precision':'second'}
    collector=Collector(db,[source]);collector.observe(source,[]);collector.observe(source,[item])
    approval=Approval(db,123,123);process_live_feed(db,approval,[source])
    record=db.conn.execute('SELECT * FROM habnews_feed_callback').fetchone()
    db.conn.execute('UPDATE habnews_feed_callback SET message_id=101')
    click={'update_id':99,'callback_query':{'id':'test-cb','data':'gpt:'+record['nonce'],
           'from':{'id':123},'message':{'message_id':101,'chat':{'id':123,'type':'private'}}}}
    return approval,source,item,click


def decode_export(payload):
    url=payload['reply_markup']['inline_keyboard'][0][0]['url'];blob=url.split('#v1.',1)[1]
    return json.loads(gzip.decompress(base64.urlsafe_b64decode(blob+'='*(-len(blob)%4))))


def prepare_read(monkeypatch,item,body=None):
    body=body or ('TCMB politika faizini yüzde 40 olarak belirledi.\n'+'Açıklamada kararın veri odaklı olduğu vurgulandı.\n')*45+'Kararın uygulanması ek koşullara bağlıdır.'
    document={'title':item['title'],'body':body,'source_url':item['url'],'method':'article_body'}
    monkeypatch.setattr('habnews.source_content.read_document',lambda *args:document)
    monkeypatch.setattr('habnews.source_content.document_photo',lambda *args:None)
    return document


def test_gpt_button_and_request_do_not_use_model_or_consume_tweet_click(db):
    approval,source,item,click=setup_export(db)
    payload=json.loads(db.conn.execute('SELECT payload FROM habnews_outbox').fetchone()[0])
    assert payload['reply_markup']['inline_keyboard'][-1][0]['callback_data'].startswith('gpt:')
    db.set_state('llm_state','quota_paused')
    assert 'kaydedildi' in gpt_callback(db,approval,click,[source])
    assert db.conn.execute('SELECT used FROM habnews_feed_callback').fetchone()[0]==0
    assert db.conn.execute('SELECT count(*) FROM habnews_event').fetchone()[0]==0
    assert db.conn.execute('SELECT count(*) FROM habnews_budget').fetchone()[0]==0
    assert db.conn.execute("SELECT count(*) FROM habnews_queue WHERE kind IN ('llm','research')").fetchone()[0]==0
    assert gpt_callback(db,approval,click,[source])=='duplicate'
    click['update_id']+=1
    assert 'hazırlanıyor' in gpt_callback(db,approval,click,[source])
    assert db.conn.execute('SELECT count(*) FROM habnews_gpt_export').fetchone()[0]==1


@pytest.mark.parametrize('change',['user','message','digest','disabled'])
def test_export_bound_to_owner_card_source_and_observation(db,change):
    approval,source,item,click=setup_export(db)
    if change=='user':
        click['callback_query']['from']['id']=456
        with pytest.raises(PermissionError):gpt_callback(db,approval,click,[source])
    else:
        if change=='message':click['callback_query']['message']['message_id']=102
        elif change=='digest':db.conn.execute("UPDATE habnews_observation SET digest='changed'")
        elif change=='disabled':source['enabled']=False
        assert gpt_callback(db,approval,click,[source]) in ('stale','Bu kaynak şu anda kapalı.')
    assert db.conn.execute('SELECT count(*) FROM habnews_gpt_export').fetchone()[0]==0


def test_export_contains_whole_article_and_same_editorial_rules(db,monkeypatch):
    approval,source,item,click=setup_export(db);document=prepare_read(monkeypatch,item)
    gpt_callback(db,approval,click,[source]);process_gpt_export(db,approval,[source])
    row=db.conn.execute('SELECT * FROM habnews_gpt_export').fetchone()
    payload=json.loads(db.conn.execute('SELECT payload FROM habnews_outbox WHERE id=?',(row['outbox_id'],)).fetchone()[0])
    data=decode_export(payload);news=json.loads(data['prompt'].split('HABER VERİSİ\n',1)[1])
    assert news['haber_metni']==document['body'] and news['başlık']==document['title']
    assert item['summary'] not in data['prompt']
    assert data['sha256']==hashlib.sha256(data['prompt'].encode()).hexdigest()
    assert EDITORIAL_RULES in data['prompt'] and EDITORIAL_RULES in model_policy({'manual_attribution':True})
    assert EDITORIAL_RULES not in model_policy({})
    assert 'yalnızca TEK tweet' in data['prompt']
    assert row['status']=='ready' and db.conn.execute('SELECT count(*) FROM habnews_budget').fetchone()[0]==0


def test_gpt_export_uses_source_reader_not_rss_summary(db,monkeypatch):
    approval,source,item,click=setup_export(db)
    html=b'<article><h1>TCMB politika faizini acikladi</h1><div itemprop="articleBody"><p>TCMB politika faizini sabit tuttu. Karar oy birligiyle alindi ve ek kosullar gelecekteki verilerle degerlendirilecek.</p><p>Son paragraf da eksiksiz aktarilacak.</p></div><aside>ALAKASIZ HABER</aside></article>'
    monkeypatch.setattr('habnews.network.Fetcher.get',lambda *a,**k:(html,{'content-type':'text/html'},item['url'],200))
    monkeypatch.setattr('habnews.source_content.document_photo',lambda *a:None)
    gpt_callback(db,approval,click,[source]);process_gpt_export(db,approval,[source])
    row=db.conn.execute('SELECT outbox_id FROM habnews_gpt_export').fetchone()
    payload=json.loads(db.conn.execute('SELECT payload FROM habnews_outbox WHERE id=?',(row[0],)).fetchone()[0])
    prompt=decode_export(payload)['prompt']
    assert 'Son paragraf da eksiksiz aktarilacak.' in prompt
    assert 'ALAKASIZ HABER' not in prompt and item['summary'] not in prompt


def test_failed_read_never_exports_summary_as_full_article(db,monkeypatch):
    approval,source,item,click=setup_export(db)
    def fail(*a):raise ValueError('ambiguous_main_text')
    monkeypatch.setattr('habnews.source_content.read_document',fail)
    gpt_callback(db,approval,click,[source]);process_gpt_export(db,approval,[source])
    assert db.conn.execute('SELECT status FROM habnews_gpt_export').fetchone()[0]=='pending'
    assert db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]==1


def test_oversize_export_has_exact_text_file_without_clipping(db,monkeypatch):
    approval,source,item,click=setup_export(db);document=prepare_read(monkeypatch,item)
    monkeypatch.setattr('habnews.gpt_export.MAX_BUTTON_URL',10)
    gpt_callback(db,approval,click,[source]);process_gpt_export(db,approval,[source])
    row=db.conn.execute("SELECT payload FROM habnews_outbox WHERE method='sendDocument'").fetchone()
    payload=json.loads(row[0]);data=Path(payload['file_path']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==payload['file_sha256']
    assert json.loads(data.decode().split('HABER VERİSİ\n',1)[1])['haber_metni']==document['body']


def test_private_picture_and_copy_button_in_one_message(db,monkeypatch):
    approval,source,item,click=setup_export(db);document=prepare_read(monkeypatch,item)
    text=document['title']+'\n\n'+document['body'];sha='a'*64
    media={'path':str(db.path.parent/'media/photo.jpg'),'version':1,'provenance':{
        'source_id':'foreks','landing_page_url':item['url'],'original_asset_url':'https://news-files.foreks.com/test.jpg',
        'delivery_scope':'private_source_preview','rights_status':'unknown','restrictions':['publication_rights_unverified'],
        'article_digest':hashlib.sha256(text.encode()).hexdigest(),'sha256':sha,'publisher':'Foreks','attribution_text':'Haber görseli: Foreks'}}
    monkeypatch.setattr('habnews.source_content.document_photo',lambda *a:media)
    gpt_callback(db,approval,click,[source]);process_gpt_export(db,approval,[source])
    row=db.conn.execute("SELECT * FROM habnews_outbox WHERE method='sendPhoto'").fetchone();assert row
    payload=json.loads(row['payload']);assert payload['file_path']==media['path'] and payload['file_sha256']==sha
    assert decode_export(payload)['prompt'].endswith('}')
    assert db.conn.execute('SELECT count(*) FROM habnews_image_candidate').fetchone()[0]==1


def test_rejected_link_falls_back_to_complete_file_without_losing_photo(db,monkeypatch):
    approval,source,item,click=setup_export(db);document=prepare_read(monkeypatch,item)
    gpt_callback(db,approval,click,[source]);process_gpt_export(db,approval,[source])
    rid=db.conn.execute('SELECT outbox_id FROM habnews_gpt_export').fetchone()[0]
    row=dict(db.conn.execute('SELECT * FROM habnews_outbox WHERE id=?',(rid,)).fetchone())
    original=decode_export(json.loads(row['payload']))['prompt']
    row['method']='sendPhoto';db.conn.execute("UPDATE habnews_outbox SET method='sendPhoto' WHERE id=?",(rid,))
    db.conn.execute('INSERT INTO habnews_attempt VALUES(?,?,?,?,?)',('a',rid,'sending',time.time(),None))
    assert delivery_fallback(db,row,'a','telegram_rejected_photo')
    updated=db.conn.execute('SELECT * FROM habnews_outbox WHERE id=?',(rid,)).fetchone()
    assert updated['method']=='sendPhoto' and 'reply_markup' not in json.loads(updated['payload'])
    file=json.loads(db.conn.execute("SELECT payload FROM habnews_outbox WHERE method='sendDocument'").fetchone()[0])
    assert Path(file['file_path']).read_text()==original
    assert delivery_fallback(db,dict(updated),'a','telegram_rejected_photo')
    assert db.conn.execute('SELECT method FROM habnews_outbox WHERE id=?',(rid,)).fetchone()[0]=='sendMessage'
    assert db.conn.execute("SELECT count(*) FROM habnews_outbox WHERE method='sendDocument'").fetchone()[0]==1


def test_stale_export_request_does_not_block_new_click(db):
    approval,source,item,click=setup_export(db);gpt_callback(db,approval,click,[source])
    db.conn.execute('UPDATE habnews_gpt_export SET created=?',(time.time()-601,))
    click['update_id']+=1;assert 'kaydedildi' in gpt_callback(db,approval,click,[source])
    assert db.conn.execute("SELECT count(*) FROM habnews_gpt_export WHERE status='pending'").fetchone()[0]==1
