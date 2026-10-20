import copy
import pytest
from habnews.quality import case_input
from habnews.schema import validate_delivery_result,validate_result,ValidationError
from habnews.story_context import ipo_application_heading
from habnews.editorial_prompt import model_policy,clipboard_prompt
from habnews.news_profiles import profile

TITLE="FLO halka arz için SPK'ya yeniden başvurdu"
MAIN="Gözde Girişim Sermayesi Yatırım Ortaklığı (GOZDE), yüzde 11,50 oranında pay sahibi olduğu FLO Mağazacılık ve Pazarlama A.Ş.'nin halka arz için Sermaye Piyasası Kuruluna (SPK) yeniden başvurduğunu duyurdu."
DETAIL="Halka arzın, mevcut ortakların pay satışı olmadan yalnızca 510 milyon TL nominal değerli sermaye artırımı yoluyla gerçekleştirilmesi planlanıyor."

def source_case(owner='Foreks'):
    job,result,ev=case_input(dict(id='flo',sentence=DETAIL,actor='Halka arzın',stage='planlanıyor',owner=owner))
    job['source_title']=TITLE
    next(iter(ev.values()))['passage']=TITLE+'\n\n'+MAIN+' '+DETAIL
    result['facts'][0].update(value_raw='510 milyon',normalized_value=510000000,currency='TL',scale='milyon',unit='nominal değerli')
    return job,result,ev

@pytest.mark.parametrize('owner',['Foreks','CNBC-e','Ekonomim','Bloomberg HT','Habertürk','Sözcü'])
def test_ipo_detail_cannot_replace_company_and_main_development(owner):
    job,result,ev=source_case(owner);before=copy.deepcopy(result)
    with pytest.raises(ValidationError,match='missing_story_lead'):validate_result(result,job,ev)
    fixed,text,changes=validate_delivery_result(result,job,ev)
    assert fixed['headline']==TITLE and 'source_story_heading' in changes
    assert text.startswith('📢 '+TITLE)
    assert 'mevcut ortakların pay satışı olmadan' in text and '510 milyon TL nominal değerli' in text
    assert '#SPK' in text and '#halkaarz' in text and len(text)<=380
    assert '#ekonomi' not in text and result==before
    assert fixed['facts']==result['facts']

@pytest.mark.parametrize('body',[
    DETAIL,
    MAIN.replace('yeniden başvurduğunu','henüz yeniden başvurmadığını'),
    MAIN.replace('FLO Mağazacılık','Başka Mağazacılık'),
    MAIN.replace('yeniden başvurduğunu duyurdu.','yeniden başvurduğu iddiasını yalanladı.'),
    MAIN.replace('yeniden başvurduğunu duyurdu.','izin verilmesi koşuluyla yeniden başvuracağını duyurdu.'),
    MAIN.replace('yeniden başvurduğunu duyurdu.','yeniden başvurduğu haberini doğrulamadı.'),
])
def test_source_title_cannot_prove_itself_or_override_denial(body):
    assert ipo_application_heading(TITLE,[TITLE+'\n\n'+body]) is None

def test_source_heading_must_not_upgrade_application_to_approval():
    assert ipo_application_heading(TITLE.replace('yeniden başvurdu','onay aldı'),[MAIN]) is None
    job,result,ev=source_case()
    result['headline']="FLO halka arz için SPK onayı aldı"
    result['proposed_body']=result['headline']+'\n\n'+DETAIL
    fixed,text,_=validate_delivery_result(result,job,ev)
    assert 'onay aldı' not in text and fixed['headline']==TITLE

def test_alternative_company_direct_application_and_unicode_apostrophe():
    title="Örnek A.Ş. halka arz için SPK’ya yeniden başvurdu"
    body="Örnek A.Ş., halka arz için SPK’ya yeniden başvurdu."
    assert ipo_application_heading(title,[title+'\n\n'+body])['issuer']=='Örnek A.Ş.'

def test_ipo_priority_is_shared_by_clipboard_and_bot():
    assert profile(TITLE+'\n'+MAIN)['type']=='ipo'
    doc=dict(title=TITLE,body=MAIN+'\n'+DETAIL,source_url='https://fixture.invalid/flo')
    for prompt in (clipboard_prompt(doc,{'owner':'Foreks'}),model_policy({'manual_attribution':True,'source_title':TITLE,'evidence':[{'full_text':doc['body']}]})):
        assert 'Pay sahibi şirket ile halka arz edilen şirketi karıştırma' in prompt
        assert 'Tweetin ilk satırı şirket/kişi adıyla ana gelişmeyi birlikte anlatmalı' in prompt

def test_unbound_source_claim_is_not_rescued_by_ipo_context():
    job,result,ev=source_case()
    result['facts'][0]['text']=DETAIL.replace('510','999')
    result['proposed_body']=result['headline']+'\n\n'+result['facts'][0]['text']
    with pytest.raises(ValidationError,match='unsupported_sentence'):validate_delivery_result(result,job,ev)
