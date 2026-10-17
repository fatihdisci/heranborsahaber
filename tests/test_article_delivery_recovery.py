"""Recover source-bound display errors without relaxing factual validation."""
import copy,json,time
import pytest
from habnews.schema import validate_result,validate_delivery_result,ValidationError
from test_editorial_grounding import draft_case

HEADLINE='Hazine ve Maliye Bakanı Mehmet Şimşek: Cari açığın yönetilebilir seviyelerde kalmasını öngörüyoruz'
SENTENCE='Ağustos ayında 4,1 milyar dolar cari fazla verildiğini belirten Şimşek, yıllıklandırılmış cari açığın 42,1 milyar dolar gerçekleştiğini bildirdi.'


def news_case(prepared):
    result,job,evidence=draft_case(prepared,HEADLINE,SENTENCE)
    result['facts'][0].update(actor='Şimşek',stage='bildirdi',period='Ağustos ayında')
    job['manual_attribution']['owner']='CNBC-e'
    return result,job,evidence


def test_cnbce_current_account_story_recovers_with_exact_selected_sentence(prepared):
    result,job,evidence=news_case(prepared);original=copy.deepcopy(result)
    with pytest.raises(ValidationError,match='headline_not_grounded_in_facts'):validate_result(result,job,evidence)
    canonical,text,changes=validate_delivery_result(result,job,evidence)
    assert canonical['headline']==SENTENCE.rstrip('.')
    assert text.count('4,1 milyar')==1 and text.count('42,1 milyar')==1
    assert 'Kaynak: CNBC-e' in text and len(text)<=380
    assert changes==['source_sentence_headline']
    assert result==original
    assert canonical['facts']==result['facts']
    assert validate_result(canonical,job,evidence)==text


@pytest.mark.parametrize('key',['scope','period','unit','currency','scale','quote'])
def test_optional_annotation_missing_from_fact_is_omitted_only(prepared,key):
    result,job,evidence=news_case(prepared)
    result['facts'][0][key]='unsupported optional label'
    canonical,text,changes=validate_delivery_result(result,job,evidence)
    assert canonical['facts'][0][key] is None
    assert 'omit_unbound_'+key in changes
    assert canonical['facts'][0]['text']==SENTENCE
    assert result['facts'][0][key]=='unsupported optional label'
    assert validate_result(canonical,job,evidence)==text


@pytest.mark.parametrize('damage,code',[
 ('number','unsupported_sentence'),('normalization','numeric_normalization_mismatch'),
 ('actor','unsupported_actor'),('stage','unsupported_stage'),
 ('body','unreferenced_body_claim'),('verification','not_primary'),
])
def test_recovery_cannot_hide_factual_or_contract_errors(prepared,damage,code):
    result,job,evidence=news_case(prepared)
    result['facts'][0]['scope']='unsupported label'
    if damage=='number':
        result['facts'][0]['text']=SENTENCE.replace('42,1','99,9')
        result['proposed_body']=result['headline']+'\n\n'+result['facts'][0]['text']
    elif damage=='normalization':result['facts'][0].update(value_raw='4,1 milyar',normalized_value=41)
    elif damage=='actor':result['facts'][0]['actor']='Different actor'
    elif damage=='stage':result['facts'][0]['stage']='kesinleşti'
    elif damage=='body':result['proposed_body']+='\n\nYatırımcılar kesin kazanacak.'
    else:
        for record in evidence.values():record['primary_source']=False
        result['verification_state']='official_primary'
    with pytest.raises(ValidationError,match=code):validate_delivery_result(result,job,evidence)


def test_social_output_is_never_rewritten_by_article_recovery(prepared):
    result,job,evidence=news_case(prepared)
    job['manual_attribution']['source_type']='social_x'
    with pytest.raises(ValidationError):validate_delivery_result(result,job,evidence)


def test_valid_result_is_returned_unchanged(prepared):
    result,job,evidence=news_case(prepared)
    result.update(headline=SENTENCE.rstrip('.'),proposed_body=SENTENCE.rstrip('.')+'\n\n'+SENTENCE)
    canonical,text,changes=validate_delivery_result(result,job,evidence)
    assert canonical is result and changes==[]


def long_case(prepared):
    headline='TCMB: Bankaların kredi büyümesine ilişkin düzenlemenin uygulama koşullarını açıkladı'
    first='TCMB, bankaların kredi büyümesine ilişkin düzenlemenin gelecek ay yürürlüğe gireceğini ve mevcut kredileri kapsamayacağını açıkladı.'
    second='TCMB, bankaların yeni başvurular için geçerli olacak uygulama koşullarını müşterilerine sözleşme öncesinde bildirmeleri gerektiğini açıkladı.'
    result,job,evidence=draft_case(prepared,headline,first)
    fact=copy.deepcopy(result['facts'][0]);fact['text']=second
    result['facts'].append(fact)
    result['proposed_body']+='\n\n'+second
    next(iter(evidence.values()))['passage']+='\n'+second
    return result,job,evidence


def test_overlong_draft_removes_redundant_heading_without_losing_conditions(prepared):
    result,job,evidence=long_case(prepared)
    original=copy.deepcopy(result)
    with pytest.raises(ValidationError,match='tweet_too_long'):validate_result(result,job,evidence)
    canonical,text,changes=validate_delivery_result(result,job,evidence)
    assert len(text)<=380 and changes==['source_sentence_headline']
    assert canonical['facts']==original['facts'] and result==original
    for fact in result['facts']:
        assert text.count(fact['text'].rstrip('.'))==1
    assert 'mevcut kredileri kapsamayacağını' in text
    assert 'sözleşme öncesinde' in text
    assert 'Kaynak: TEST' in text


def test_recovery_never_drops_a_fact_to_fit_the_length_budget(prepared):
    result,job,evidence=long_case(prepared)
    extra='TCMB, düzenleme kapsamında bankaların müşterilere verecekleri bilgilerin açık ve anlaşılır olması gerektiğini ayrıca açıkladı.'
    fact=copy.deepcopy(result['facts'][0]);fact['text']=extra
    result['facts'].append(fact);result['proposed_body']+='\n\n'+extra
    next(iter(evidence.values()))['passage']+='\n'+extra
    original=copy.deepcopy(result)
    with pytest.raises(ValidationError,match='tweet_too_long'):validate_delivery_result(result,job,evidence)
    assert result==original


def test_approval_persists_corrected_result_and_queues_only_one_quiet_draft(prepared):
    db,approval,_,_,metadata=prepared
    result,job,evidence=news_case(prepared)
    job['quiet_delivery']=True
    result['facts'][0]['scope']='cari denge'
    item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0])
    item['manual_requested_at']=time.time()
    db.conn.execute('UPDATE habnews_event_version SET payload=?',(json.dumps(item),))
    record=next(iter(evidence.values()))
    db.conn.execute('UPDATE habnews_evidence SET passage=?',(record['passage'],))
    did=approval.create(job,result,metadata)
    draft=db.conn.execute('SELECT body,metadata FROM habnews_draft WHERE id=?',(did,)).fetchone()
    persisted=json.loads(draft['metadata'])['validated_result']
    assert persisted['headline']==SENTENCE.rstrip('.') and persisted['facts'][0]['scope'] is None
    rows=db.conn.execute('SELECT method,payload FROM habnews_outbox WHERE draft_id=?',(did,)).fetchall()
    assert len(rows)==1 and rows[0]['method']=='sendMessage'
    assert json.loads(rows[0]['payload'])['text']==draft['body']
    assert db.conn.execute("SELECT count(*) FROM habnews_audit WHERE kind='article_result_normalized'").fetchone()[0]==1
