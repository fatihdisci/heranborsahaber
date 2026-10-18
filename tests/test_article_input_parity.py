import json,time
from habnews.collector import Collector
from habnews.config import sources
from habnews.db import encode
from habnews.editorial_prompt import clipboard_prompt
from habnews.hermes import JobBroker
from habnews.source_content import document_text
from habnews.rewriting import article_speaker,display_article

TOTAL='Bununla birlikte tasfiye sürecinde bulunan, toplam büyüklüğü 5.375.468.526 TL tutarındaki 15 fonumuzun tasfiyesi başarıyla gerçekleştirilmiştir.'
TODAY='Bugün tasfiye edilen fonlarımızın toplam büyüklüğü 4.154.718.986,82 TL toplam yatırımcı sayısı ise 142 olarak gerçekleşmiştir.'
TITLE="Bulls Portföy'den 5,3 milyar liralık tasfiye açıklaması"

def test_full_article_sent_to_model_matches_clipboard_without_excerpt(prepared,tmp_path,monkeypatch):
    db,_,job,*_=prepared
    source=next(s for s in sources() if s['stable_id']=='foreks')|{'enabled':True}
    item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0])
    item.update(manual_requested_at=time.time(),source_id='foreks')
    db.conn.execute('UPDATE habnews_event_version SET payload=?',(encode(item),))
    document={'title':TITLE,'body':('Açıklamada yatırımcı haklarının korunacağı belirtildi.\n'*60)+TOTAL+'\n'+TODAY,
              'source_url':item['url'],'method':'article_body'}
    monkeypatch.setattr('habnews.source_content.read_document',lambda *a:document)
    monkeypatch.setattr('habnews.source_content.document_photo',lambda *a:None)
    db.enqueue('research','parity',dict(job,source_id='foreks',item=item,manual=True))
    Collector(db,[source]).research_one()
    db.set_state('llm_state','ready')
    JobBroker(db,tmp_path/'jobs').submit_one()
    model=json.loads(next((tmp_path/'jobs').glob('*.job.json')).read_text())
    evidence=model['evidence'][0]
    clipboard=json.loads(clipboard_prompt(document,source).split('HABER VERİSİ\n')[1])
    assert evidence['full_text']==clipboard['başlık']+'\n\n'+clipboard['haber_metni']==document_text(document,source)
    assert TODAY in evidence['full_text'] and item['summary'] not in evidence['full_text']
    assert 'passage' not in evidence
    assert len(db.conn.execute('SELECT passage FROM habnews_evidence WHERE tombstone=0').fetchone()[0])<=1600

def test_named_statement_keeps_total_and_today_distinct():
    facts=[{'text':s,'actor':'fonumuzun','quote':None} for s in (TOTAL,TODAY)]
    passage='Bulls Portföy yaptığı açıklamada şu ifadeleri kullandı:\n"Tasfiye işlemleri tamamlandı.\n'+TOTAL+'\n'+TODAY+'"'
    speaker=article_speaker(TITLE,[passage],facts)
    text=display_article(TOTAL.rstrip('.'),facts,speaker=speaker)
    assert text.startswith('Bulls Portföy, 5.375.468.526 TL büyüklüğündeki 15 fonun')
    assert 'Bugün tasfiye edilen fonların büyüklüğü 4.154.718.986,82 TL; toplam yatırımcı sayısı 142.' in text
    assert 'fonumuz' not in text and 'Bununla birlikte' not in text

def test_foreign_or_unbound_quotation_is_not_attributed():
    facts=[{'text':TOTAL}]
    assert article_speaker(TITLE,['Bulls Portföy yaptığı açıklamada şu ifadeleri kullandı: "Başka açıklama."\n'+TOTAL],facts) is None
    assert article_speaker(TITLE,[TOTAL],facts) is None

def test_literal_quote_preserved_with_named_speaker():
    fact={'text':TOTAL,'actor':'fonumuzun','quote':TOTAL}
    text=display_article(TOTAL.rstrip('.'),[fact],speaker='Bulls Portföy')
    assert 'Bulls Portföy açıklamasında: “'+TOTAL+'”'==text

def test_validated_draft_rewrites_source_voice_and_uses_specific_tags(prepared):
    from habnews.schema import validate_result,ValidationError
    import pytest
    db,_,job,result,_=prepared
    passage='Bulls Portföy yaptığı açıklamada şu ifadeleri kullandı:\n"Tasfiye işlemleri tamamlandı.\n'+TOTAL+'\n'+TODAY+'"'
    fact=result['facts'][0]|dict(text=TOTAL,value_raw='5.375.468.526',normalized_value=5375468526,
                              unit=None,currency='TL',scope='15 fonumuzun',
                              stage='tasfiyesi başarıyla gerçekleştirilmiştir',actor='15 fonumuzun')
    result=result|dict(facts=[fact],headline=TOTAL.rstrip('.'),proposed_body=TOTAL.rstrip('.')+'\n\n'+TOTAL,verification_state='attributed_single_source')
    job=job|dict(source_title=TITLE,controlled_rewrite=True,content_contract='article-v2',
                manual_attribution={'source_type':'article','owner':'CNBC-e','url':'https://www.tcmb.gov.tr/test'})
    evidence={fact['source_ref']:dict(db.conn.execute('SELECT * FROM habnews_evidence').fetchone())|dict(passage=passage)}
    text=validate_result(result,job,evidence)
    assert 'Bulls Portföy, 5.375.468.526 TL' in text
    assert '#fon #portföy #tasfiye' in text and '#gündem' not in text
    job['source_title']='Başka şirket açıklaması'
    with pytest.raises(ValidationError,match='unattributed_source_voice'):
        validate_result(result,job,evidence)
