"""Source-faithful editorial fixtures; never call a real model or Telegram."""
import copy
import re
import pytest
from habnews.article import extract_document
from habnews.schema import validate_result,ValidationError
from habnews.tweet_style import decorate
from habnews.editorial_prompt import clipboard_prompt,model_policy


def article(body,title='Örnek Şirket yatırım açıklaması'):
    return f'<article><header><h1>{title}</h1></header><div class="article-body">{body}</div></article>'.encode()


def test_header_and_mixed_body_keep_actor_qualifiers_and_short_negation():
    first='Örnek Şirket, Türkiye’de yeni terminal yatırımı planladığını açıkladı.'
    second='Proje, ilgili kurumlardan izin alınması koşuluyla hayata geçirilecek.'
    body=first+f'<p>{second}</p><strong>Kesinleşmedi.</strong><p>Hayır.</p>'
    doc=extract_document(article(body),'text/html','https://example.test/story')
    assert doc['title']=='Örnek Şirket yatırım açıklaması'
    assert doc['body']==first+'\n'+second+'\nKesinleşmedi.\nHayır.'


def test_hidden_content_and_related_stories_do_not_enter_source():
    text='TCMB, politika faizine ilişkin değerlendirmeyi gelecek toplantıda yapacağını açıkladı. Henüz yeni bir karar alınmadı.'
    hidden='<p style="display: none !important">YANLIŞ oran yüzde 90 oldu.</p><p aria-hidden="TRUE">YANLIŞ</p><aside>YANLIŞ</aside>'
    doc=extract_document(article('<p>'+text+'</p>'+hidden),'text/html')
    assert doc['body']==text


def test_tables_preserve_company_amount_and_following_condition():
    body='<p>Şirketlerin açıkladığı sözleşmeler, aşağıdaki tabloda kendi para birimleriyle listelenmiştir.</p><table><tr><th>Şirket</th><th>Tutar</th></tr><tr><td>Örnek A</td><td>10 milyon TL</td></tr><tr><td>Örnek B</td><td>20 milyon dolar</td></tr></table>Ödemeler onaya tabidir.'
    doc=extract_document(article(body),'text/html')
    assert 'Şirket | Tutar\nÖrnek A | 10 milyon TL\nÖrnek B | 20 milyon dolar' in doc['body']
    assert doc['body'].endswith('Ödemeler onaya tabidir.')


def draft_case(prepared,headline,sentence):
    db,_,job,result,_=prepared
    ev=dict(db.conn.execute('SELECT * FROM habnews_evidence').fetchone())
    ev['passage']=headline+'\n'+sentence
    job=job|{'content_contract':'article-v2','source_title':headline,'manual_attribution':{'source_type':'article','owner':'TEST','url':ev['url']}}
    result=copy.deepcopy(result)
    result['facts'][0].update(text=sentence,actor='TCMB',stage='açıkladı',value_raw=None,normalized_value=None,unit=None,currency=None,scale=None,period=None,scope=None,quote=None)
    result.update(headline=headline,proposed_body=headline+'\n\n'+sentence,verification_state='attributed_single_source')
    return result,job,{ev['id']:ev}


@pytest.mark.parametrize('headline,sentence',[
 ('TCMB: Mevduatlarda 800 milyar TL artış','TCMB, mevduatlarda 800 milyar TL üzerinde artış olduğunu açıkladı.'),
 ('TCMB: 1 milyon TL destek','TCMB, en fazla 1 milyon TL destek sağlanacağını açıkladı.'),
 ('TCMB: 14 terminal','TCMB, yaklaşık 14 terminal planlandığını açıkladı.'),
])
def test_headline_cannot_drop_numeric_qualification(prepared,headline,sentence):
    result,job,ev=draft_case(prepared,headline,sentence)
    with pytest.raises(ValidationError,match='headline_missing_quantity_qualifier'):validate_result(result,job,ev)


@pytest.mark.parametrize('sentence',[
 'TCMB, mevduatlarda 800 milyar TL üzerinde artış olduğunu açıkladı.',
 'TCMB, en fazla 1 milyon TL destek sağlanacağını açıkladı.',
 'TCMB, yaklaşık 14 terminal planlandığını açıkladı.',
])
def test_complete_qualified_headline_is_concise_and_displayed_once(prepared,sentence):
    result,job,ev=draft_case(prepared,sentence.rstrip('.'),sentence)
    output=validate_result(result,job,ev)
    assert output.count(sentence.rstrip('.'))==1
    assert len(output)<=380
    assert 'Kaynak: TEST' in output
    assert output.startswith('📢 ')
    assert 2<=len(re.findall(r'#\w+',output))<=3


def test_repeated_body_facts_are_repaired(prepared):
    result,job,ev=draft_case(prepared,'TCMB faiz açıklaması','TCMB, faiz kararının gelecek toplantıda verileceğini açıkladı.')
    result['facts'].append(copy.deepcopy(result['facts'][0]))
    result['proposed_body']+='\n\n'+result['facts'][0]['text']
    with pytest.raises(ValidationError,match='duplicate_article_fact'):validate_result(result,job,ev)


def test_currency_amount_and_under_threshold_do_not_invent_market_tags():
    text='Örnek Şirket, 10 milyon doların altında bir sözleşme imzaladı.'
    output=decorate(text,text)
    assert '#altın' not in output and '#döviz' not in output
    assert '#şirket' in output


def test_actual_gold_and_exchange_rate_topics_remain_available():
    assert '#altın' in decorate('Haber','Altın fiyatları yükseldi.')
    assert '#döviz' in decorate('Haber','Dolar kuru yükseldi.')


def test_normal_fund_commentary_is_not_an_emergency():
    assert decorate('Haber','TCMB fon piyasası değerlendirmesini yayımladı.').startswith('📢 ')


def test_sensitive_report_has_no_attention_emoji():
    text='Kazanın ardından hayatını kaybeden kişinin kimliği açıklandı.'
    output=decorate(text,text)
    assert '📢' not in output and '🚨' not in output


def test_both_prompts_require_conditions_row_binding_and_concrete_subjects():
    document={'title':'TEST','body':'TEST gövdesi','source_url':'https://example.test/story'}
    for prompt in (clipboard_prompt(document,{'owner':'TEST'}),model_policy({'manual_attribution':{'source_type':'article'}})):
        assert 'başka satırın rakamını' in prompt
        assert 'kim, ne yaptı' in prompt
        assert 'kanıtsız neden-sonuç' in prompt


def test_article_header_standfirst_is_kept_without_timestamp_or_controls():
    intro='Örnek Şirket, yatırımın yalnızca izin alınması halinde başlayacağını açıkladı.'
    text='Yatırımın finansmanına ilişkin görüşmeler sürüyor. Henüz kesin bir başlangıç tarihi verilmedi.'
    raw=f'<article><header><h1>Örnek Şirket yatırım açıklaması</h1><time>BUGÜN SAAT 12:00</time><h2>{intro}</h2><button>PAYLAŞ</button></header><div class="article-body"><p>{text}</p></div></article>'
    doc=extract_document(raw.encode(),'text/html')
    assert doc['body']==intro+'\n'+text


@pytest.mark.parametrize('word',['fonlardan','fonların','fonlarında','fonlarının','fonuna','fonunun'])
def test_fund_suffixes_keep_relevant_hashtag(word):
    assert '#fon' in decorate('Haber','Bu '+word+' yeni açıklama geldi.')


def test_standfirst_alone_is_not_mistaken_for_full_article():
    intro='Bu yalnız haberin kısa tanıtımıdır; ana metin sitede yüklenmediği için eksiksiz kaynak olarak kullanılamaz.'
    raw=f'<article><header><h1>Başlık</h1><h2>{intro}</h2></header></article>'
    with pytest.raises(ValueError,match='main_text_missing'):extract_document(raw.encode(),'text/html')


def test_standfirst_does_not_disable_full_structured_article_fallback():
    import json
    intro='Bu kısa tanıtım gerçek haber metninin yerini alamaz. Ayrıntılar ayrıca yayımlanan haber metninde yer alıyor.'
    text='TCMB, faiz kararına ilişkin değerlendirmelerini açıkladı. Metin tüm koşullarıyla birlikte bu alanda yer alıyor.'
    raw=f'<article><header><h1>Başlık</h1><h2>{intro}</h2></header></article><script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','headline':'Başlık','articleBody':text})+'</script>'
    assert extract_document(raw.encode(),'text/html')['body']==text


def test_source_title_cannot_supply_causality_absent_from_chosen_facts(prepared):
    result,job,ev=draft_case(prepared,'TCMB: Fonlar mevduata yöneldi','TCMB, fonlardan çıkış ve aynı dönemde mevduatta artış olduğunu açıkladı.')
    with pytest.raises(ValidationError,match='headline_not_grounded_in_facts'):validate_result(result,job,ev)


@pytest.mark.parametrize('headline,code',[
 ('TCMB faiz açıklaması mı?','question_article_headline'),
 ('SON DAKİKA TCMB faiz açıklaması','breaking_label_not_allowed'),
])
def test_clickbait_and_breaking_labels_trigger_editorial_repair(prepared,headline,code):
    result,job,ev=draft_case(prepared,headline,'TCMB, faiz kararı konusunda henüz yeni bir adım atılmadığını açıkladı.')
    with pytest.raises(ValidationError,match=code):validate_result(result,job,ev)


@pytest.mark.parametrize('code',['headline_not_grounded_in_facts','headline_missing_quantity_qualifier','duplicate_article_fact','question_article_headline','breaking_label_not_allowed'])
def test_editorial_failure_queues_bounded_repair_without_sending(prepared,tmp_path,code):
    import json,time
    from habnews.budget import Budget
    from habnews.db import encode
    from habnews.hermes import JobBroker,atomic_file
    db,_,job,result,metadata=prepared
    item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version').fetchone()[0])
    item.update(source_id='tcmb',manual_requested_at=time.time())
    db.conn.execute('UPDATE habnews_event_version SET payload=?',(encode(item),))
    job=job|{'manual_attribution':{'source_type':'article'},'deadline':time.time()+180}
    db.enqueue('llm','editorial-repair-test',job);row=db.claim('llm')
    reservation=Budget(db).reserve(job['event_id'],'P0')
    db.set_state('job:'+row['id'],encode({'lease':row['lease'],'reservation':reservation,'job':job}))
    atomic_file(tmp_path/(row['id']+'.result.json'),{'result':result,'run_metadata':metadata})
    class Reject:
        def create(self,*args,**kwargs):raise ValidationError(code)
    JobBroker(db,tmp_path).consume(Reject())
    assert db.conn.execute("SELECT status FROM habnews_queue WHERE kind='llm'").fetchone()[0]=='repair_queued'
    payload=json.loads(db.conn.execute("SELECT payload FROM habnews_queue WHERE kind='research'").fetchone()[0])
    assert payload['repair_attempt']==1 and payload['repair_feedback']['validation_code']==code
    assert db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]==0
