"""Offline cross-source contracts; no network, model calls or Telegram writes."""
import copy
import pytest
from habnews.quality import CASES,case_input
from habnews.schema import validate_delivery_result,ValidationError
from habnews.rewriting import rewrite_sentence
from test_attributed_quote_delivery import case as quote_case,QUOTE

OWNERS=['Foreks','Bloomberg HT','Habertürk','Sözcü','TCMB','Dünya','Ekonomim',
        'CNBC-e','NTV Para','TRT Haber Ekonomi','Anadolu Ajansı Ekonomi','Euronews Türkçe']

@pytest.mark.parametrize('owner',OWNERS)
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_every_news_type_remains_source_bound_for_every_owner(owner,case):
    job,result,evidence=case_input(case)
    job['manual_attribution']['owner']=owner
    # Common real model format: headline is already the first fact, so output
    # omits its redundant second copy. Restore schema representation only.
    result['proposed_body']=result['headline']
    original=copy.deepcopy(result)
    fixed,text,_=validate_delivery_result(result,job,evidence)
    assert result==original and fixed['facts']==result['facts']
    assert 'Kaynak: '+owner in text and len(text)<=380
    assert all(marker in text for marker in case['keep'])

@pytest.mark.parametrize('owner',OWNERS)
@pytest.mark.parametrize('wrapper',['paylaşımında "{}" ifadelerini kullandı.',
                                   'açıklamasında “{}” ifadelerini kullandı.',
                                   ', "{}" dedi.',', “{}” diye konuştu.'])
def test_neutral_quote_wrappers_keep_whole_quote_and_actor(prepared,owner,wrapper):
    result,job,ev=quote_case(prepared)
    source='Yılmaz'+('' if wrapper.startswith(',') else ' ')+wrapper.format(QUOTE)
    fact=result['facts'][0];fact.update(text=source,stage='Meclisimizin gündemindedir')
    result['proposed_body']=result['headline']+'\n\n'+source
    ev['evidence-1']['passage']=result['headline']+'\n\n'+source
    job['manual_attribution']['owner']=owner
    fixed,text,_=validate_delivery_result(result,job,ev)
    assert QUOTE in text and 'Yılmaz: “' in text and len(text)<=380
    assert fixed['facts']==result['facts']

@pytest.mark.parametrize('owner',OWNERS)
@pytest.mark.parametrize('damage',['amount','condition','speaker','extra_body'])
def test_factual_damage_cannot_be_hidden_by_display_recovery(owner,damage):
    case={'id':'negative','actor':'Örnek Şirket','stage':'planladığını',
          'sentence':'Örnek Şirket, izin alınması koşuluyla 10 milyon TL yatırım yapmayı planladığını açıkladı.'}
    job,result,evidence=case_input(case);job['manual_attribution']['owner']=owner
    if damage=='amount':result['facts'][0]['text']=case['sentence'].replace('10','90')
    elif damage=='condition':result['facts'][0]['text']=case['sentence'].replace('izin alınması koşuluyla ','')
    elif damage=='speaker':result['facts'][0]['actor']='Başka Şirket'
    if damage=='extra_body':result['proposed_body']+='\n\nYatırım kesinleşti.'
    else:result['proposed_body']=result['headline']+'\n\n'+result['facts'][0]['text']
    with pytest.raises(ValidationError):validate_delivery_result(result,job,evidence)

def test_foreks_calendar_dates_are_not_monetary_quantities():
    sentence='Aselsan Elektronik Sanayi ve Ticaret AŞ (ASELS), 2026 yılı üçüncü çeyrek finansal sonuçlarını 27 Ekim 2026 tarihinde kamuoyuyla paylaşmayı planladığını duyurdu.'
    actor='Aselsan Elektronik Sanayi ve Ticaret AŞ (ASELS)'
    job,result,evidence=case_input(dict(id='date',sentence=sentence,actor=actor,stage='planladığını',owner='Foreks'))
    result['facts'][0].update(value_raw='27 Ekim 2026',normalized_value=None,period='2026 yılı üçüncü çeyrek')
    result['proposed_body']=result['headline']
    fixed,text,changes=validate_delivery_result(result,job,evidence)
    assert fixed['facts'][0]['value_raw'] is None
    assert '27 Ekim 2026' in text and 'planlıyor' in text
    assert 'calendar_date_not_quantity' in changes

@pytest.mark.parametrize('normalized,currency',[(27,None),(None,'TL')])
def test_date_recovery_does_not_erase_numeric_or_currency_assertions(normalized,currency):
    case=dict(id='date',sentence='Örnek Şirket, sonuçlarını 27 Ekim 2026 tarihinde açıklayacağını bildirdi.',actor='Örnek Şirket',stage='bildirdi')
    job,result,evidence=case_input(case)
    result['facts'][0].update(value_raw='27 Ekim 2026',normalized_value=normalized,currency=currency)
    with pytest.raises(ValidationError):validate_delivery_result(result,job,evidence)

def test_full_intro_is_merged_only_with_its_same_source_quote(prepared):
    result,job,ev=quote_case(prepared)
    intro='Cumhurbaşkanı Yardımcısı Cevdet Yılmaz, fon tasfiye sürecine ilişkin sosyal medya hesabından açıklamalarda bulundu.'
    fact=dict.fromkeys(result['facts'][0]);fact.update(text=intro,source_ref='evidence-1',actor='Cumhurbaşkanı Yardımcısı Cevdet Yılmaz',stage='açıklamalarda bulundu')
    result['facts'].insert(0,fact);result['headline']=intro.rstrip('.')
    result['proposed_body']=result['headline']+'\n\n'+'\n\n'.join(f['text'] for f in result['facts'])
    ev['evidence-1']['passage']=intro+'\n'+ev['evidence-1']['passage']
    fixed,text,_=validate_delivery_result(result,job,ev)
    assert 'Cumhurbaşkanı Yardımcısı Cevdet Yılmaz' in text and 'fon tasfiye sürecine ilişkin sosyal medya hesabından' in text
    assert QUOTE in text and len(text)<=380
    assert fixed['facts']==result['facts']
    from habnews.rewriting import merge_statement_intro
    fact['source_ref']='foreign'
    assert merge_statement_intro(result['facts'],fact) is None

def test_schedule_rewrite_does_not_drop_trailing_condition():
    sentence='Örnek Şirket, 2026 yılı üçüncü çeyrek finansal sonuçlarını 27 Ekim 2026 tarihinde kamuoyuyla paylaşmayı planladığını duyurdu; tarih ertelenebilir.'
    assert rewrite_sentence(sentence,'Örnek Şirket')==sentence

@pytest.mark.parametrize('owner',OWNERS)
def test_draft_creation_queues_one_clean_private_message_per_source(prepared,owner):
    import json
    result,job,evidence=quote_case(prepared)
    db,approval,_,_,metadata=prepared
    job.update(quiet_delivery=True,edit_controls=True)
    job['manual_attribution']['owner']=owner
    import time
    item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0])
    item['manual_requested_at']=time.time()
    db.conn.execute('UPDATE habnews_event_version SET payload=?',(json.dumps(item),))
    ref='evidence-1'
    db.conn.execute('UPDATE habnews_evidence SET passage=? WHERE id=?',(evidence[ref]['passage'],ref))
    did=approval.create(job,result,metadata)
    rows=db.conn.execute('SELECT method,payload FROM habnews_outbox WHERE draft_id=?',(did,)).fetchall()
    assert len(rows)==1 and rows[0]['method']=='sendMessage'
    message=json.loads(rows[0]['payload'])
    assert QUOTE in message['text'] and 'Kaynak: '+owner in message['text']
    assert 'needs_review' not in message['text']
    assert message['link_preview_options']=={'is_disabled':True}
    assert db.conn.execute('SELECT status FROM habnews_draft WHERE id=?',(did,)).fetchone()[0]=='pending'
