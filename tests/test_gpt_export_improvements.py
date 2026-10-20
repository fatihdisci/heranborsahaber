import json,re
import pytest
from habnews.editorial_prompt import clipboard_prompt,model_policy,BOT_OUTPUT_LIMITS
from habnews.gpt_export import gpt_callback,process_gpt_export
from test_gpt_export import setup_export,prepare_read,decode_export

def test_clipboard_prompt_has_adaptive_length_without_fixed_character_cap():
    doc=dict(title='Çok hisseli haber',body='Örnek haber.',source_url='https://fixture.invalid/news')
    prompt=clipboard_prompt(doc,{'owner':'TEST'})
    instructions=prompt.split('HABER VERİSİ\n')[0]
    assert '280' not in instructions and '380' not in instructions
    assert not re.search(r'(?:en fazla|üst sınır|hedefi yaklaşık)\s+\d+\s*karakter',instructions)
    assert 'Sabit bir karakter, kelime veya satır sınırı uygulama' in instructions
    assert 'şirket/hisse başına ayrı ve kısa satırlar' in instructions
    assert 'tek kısa ayrıntı' not in instructions
    assert BOT_OUTPUT_LIMITS not in prompt
    # The Telegram bot's existing caption and validation contract stays explicit.
    assert BOT_OUTPUT_LIMITS in model_policy({'manual_attribution':True})

def test_multi_company_export_preserves_every_company_amount_and_condition(db,monkeypatch):
    approval,source,item,click=setup_export(db)
    body='\n'.join(f'Örnek Şirket {i} | {i+10} milyon TL | İzin alınması koşuluyla yatırım planlanıyor.' for i in range(60))
    doc=prepare_read(monkeypatch,item,body=body)
    gpt_callback(db,approval,click,[source]);process_gpt_export(db,approval,[source])
    outbox=db.conn.execute('SELECT payload FROM habnews_outbox WHERE id=(SELECT outbox_id FROM habnews_gpt_export)').fetchone()
    prompt=decode_export(json.loads(outbox[0]))['prompt']
    data=json.loads(prompt.split('HABER VERİSİ\n')[1])
    assert data['haber_metni']==doc['body']==body
    assert 'başka satırın rakamını' in prompt and 'Hisse kodunu yalnız kaynak açıkça veriyorsa kullan' in prompt
    assert db.conn.execute('SELECT count(*) FROM habnews_budget').fetchone()[0]==0

@pytest.mark.parametrize('broken',['foreign_article','wrong_digest','malformed'])
def test_bad_photo_does_not_block_the_complete_copy_export(db,monkeypatch,broken):
    approval,source,item,click=setup_export(db);doc=prepare_read(monkeypatch,item)
    media={'path':'/data/media/invalid.jpg','provenance':{}}
    if broken!='malformed':
        import hashlib
        p={'source_id':'foreks','landing_page_url':item['url'],'original_asset_url':'https://news-files.foreks.com/test.jpg',
           'delivery_scope':'private_source_preview','rights_status':'unknown','restrictions':['publication_rights_unverified'],
           'article_digest':hashlib.sha256((doc['title']+'\n\n'+doc['body']).encode()).hexdigest(),'sha256':'a'*64}
        p['landing_page_url']='https://www.foreks.com/different' if broken=='foreign_article' else item['url']
        if broken=='wrong_digest':p['article_digest']='b'*64
        media['provenance']=p
    monkeypatch.setattr('habnews.source_content.document_photo',lambda *a:media)
    gpt_callback(db,approval,click,[source]);process_gpt_export(db,approval,[source])
    row=db.conn.execute('SELECT * FROM habnews_gpt_export').fetchone()
    payload=json.loads(db.conn.execute('SELECT payload FROM habnews_outbox WHERE id=?',(row['outbox_id'],)).fetchone()[0])
    assert row['status']=='ready' and 'file_path' not in payload
    assert json.loads(decode_export(payload)['prompt'].split('HABER VERİSİ\n')[1])['haber_metni']==doc['body']
    assert db.conn.execute("SELECT count(*) FROM habnews_outbox WHERE method='sendPhoto'").fetchone()[0]==0

def test_source_update_during_export_cannot_send_stale_article(db,monkeypatch):
    approval,source,item,click=setup_export(db);prepare_read(monkeypatch,item)
    def changed(*args):
        db.conn.execute("UPDATE habnews_observation SET digest='changed-after-read'")
        return None
    monkeypatch.setattr('habnews.source_content.document_photo',changed)
    gpt_callback(db,approval,click,[source]);process_gpt_export(db,approval,[source])
    assert db.conn.execute('SELECT status FROM habnews_gpt_export').fetchone()[0]=='expired'
    assert db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]==1
