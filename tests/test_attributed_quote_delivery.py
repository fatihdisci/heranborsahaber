import pytest
from habnews.schema import validate_delivery_result,ValidationError

QUOTE='Olağan tasfiyeler hızla yapılmaktadır, olağanüstü tasfiye için kanuni düzenlemeler Meclisimizin gündemindedir. Haksız ve fahiş kazançların sisteme dönmesi ve yatırımcılara ödenmesi için yoğun ve çok yönlü çaba sarf edilmektedir'
TITLE='Cumhurbaşkanı Yardımcısı Yılmaz: Olağan tasfiyeler hızla yapılmaktadır'

def case(prepared):
    db,_,job,result,_=prepared
    text='Yılmaz paylaşımında "'+QUOTE+'" ifadelerini kullandı.'
    fact=dict.fromkeys(result['facts'][0]);fact.update(text=text,source_ref='evidence-1',actor='Yılmaz',stage='Meclisimizin gündemindedir',quote=QUOTE)
    result=result|dict(facts=[fact],headline=TITLE,proposed_body=TITLE+'\n\n'+text,verification_state='attributed_single_source')
    job=job|dict(content_contract='article-v2',controlled_rewrite=True,source_title=TITLE,manual_attribution={'source_type':'article','owner':'Habertürk','url':'https://www.tcmb.gov.tr/test'})
    ev={'evidence-1':dict(db.conn.execute('SELECT * FROM habnews_evidence').fetchone())|{'passage':TITLE+'\n\n'+text}}
    return result,job,ev

def test_real_haberturk_long_quote_is_delivered_without_losing_conditions(prepared):
    result,job,ev=case(prepared)
    fixed,text,changes=validate_delivery_result(result,job,ev)
    assert 'Yılmaz: “'+QUOTE+'”' in text
    assert len(text)<=380 and 'Kaynak: Habertürk' in text
    assert fixed['facts']==result['facts'] and changes
    assert 'olağanüstü tasfiye için kanuni düzenlemeler Meclisimizin gündemindedir' in text

@pytest.mark.parametrize('separator',['\n','\n\n\n',' '])
def test_body_whitespace_is_repaired_but_claims_are_preserved(prepared,separator):
    result,job,ev=case(prepared)
    result['proposed_body']=result['headline']+separator+result['facts'][0]['text']
    _,text,changes=validate_delivery_result(result,job,ev)
    assert QUOTE in text and 'body_whitespace' in changes

@pytest.mark.parametrize('extra',[' Yasa kabul edildi.',' Tasfiyeler tamamlandı.'])
def test_extra_body_claim_still_rejected(prepared,extra):
    result,job,ev=case(prepared);result['proposed_body']+=extra
    with pytest.raises(ValidationError,match='unreferenced_body_claim'):validate_delivery_result(result,job,ev)

def test_trailing_denial_is_never_removed_from_quote_wrapper(prepared):
    result,job,ev=case(prepared)
    text=result['facts'][0]['text']+' Ancak bu açıklama daha sonra yalanlandı.'
    result['facts'][0]['text']=text;result['proposed_body']=TITLE+'\n\n'+text
    ev['evidence-1']['passage']=TITLE+'\n\n'+text
    with pytest.raises(ValidationError):validate_delivery_result(result,job,ev)
