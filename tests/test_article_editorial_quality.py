import copy
import pytest
from habnews.schema import validate_result,ValidationError
from habnews.editorial_prompt import EDITORIAL_RULES,clipboard_prompt,model_policy


def manual_case(prepared,sentence):
    db,_,job,result,_=prepared
    ev=dict(db.conn.execute('select * from habnews_evidence').fetchone())
    ev['passage']=sentence
    job=job|{'content_contract':'article-v2','source_title':sentence,'manual_attribution':{'source_type':'article','owner':'Ekonomim','url':ev['url']}}
    result=copy.deepcopy(result);fact=result['facts'][0]
    fact.update(text=sentence,actor=sentence.split()[0],stage='amaçlıyor',value_raw=None,normalized_value=None,unit=None,currency=None,scale=None,period=None,scope=None,quote=None)
    result.update(headline=sentence.rstrip('.'),proposed_body=sentence.rstrip('.')+'\n\n'+sentence,verification_state='attributed_single_source')
    return job,result,{ev['id']:ev}


def test_explicit_actor_sentence_used_as_headline_is_displayed_once(prepared):
    sentence='Örnek Lojistik, Türkiye güzergâhında 14 terminal kurmayı amaçlıyor.'
    job,result,evidence=manual_case(prepared,sentence)
    rendered=validate_result(result,job,evidence)
    assert rendered.count('14 terminal')==1 and 'Örnek Lojistik' in rendered


def test_anaphoric_company_headline_rejected_for_editorial_repair(prepared):
    sentence='Şirket, Türkiye güzergâhında 14 terminal kurmayı amaçlıyor.'
    job,result,evidence=manual_case(prepared,sentence)
    with pytest.raises(ValidationError,match='generic_article_headline'):
        validate_result(result,job,evidence)


def test_both_prompts_share_explicit_actor_and_no_repetition_rules():
    doc={'source_url':'https://example.test/article','title':'Başlık','body':'Tam kaynak metni'}
    exported=clipboard_prompt(doc,{'owner':'Test'})
    bot=model_policy({'manual_attribution':{'source_type':'article'}})
    assert EDITORIAL_RULES in exported and EDITORIAL_RULES in bot
    assert 'ana kişi/kurum/şirket adı' in exported and 'İkinci cümle yalnız' in bot
