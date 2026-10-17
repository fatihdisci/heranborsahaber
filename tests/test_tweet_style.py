import re
import pytest
from habnews.tweet_style import decorate

def test_fund_story_gets_relevant_tags_and_one_emoji():
    text='SPK yatırım fonları için borsa düzenlemesi açıkladı.'
    out=decorate(text,text)
    assert out=='📢 '+text+'\n\n#fon #borsa #SPK'
    assert out.count('📢')==1

def test_unrelated_story_not_tagged_borsa():
    out=decorate('Haber','Bakan yeni açıklama yaptı.')
    assert '#borsa' not in out
    assert 2<=len(re.findall(r'#\w+',out))<=3

def test_death_story_has_no_emoji():
    out=decorate('Haber','Fon soruşturmasında adı geçen kişi ölü bulundu.')
    assert '📢' not in out and '🚨' not in out
    assert '#fon' in out

def test_macro_tags_prioritized_without_invented_tickers():
    out=decorate('Haber','TCMB faiz ve enflasyon açıklaması yaptı.')
    assert out.endswith('#TCMB #faiz #enflasyon')

def test_fund_liquidation_does_not_automatically_claim_urgency():
    out=decorate('Karahan: Mevduatlarda 800 milyar TL artış','Tasfiye sürecindeki fonlardan çıkış yaşandı.')
    assert out.startswith('📢 Karahan:')
    assert 'SON DAKİKA' not in out
    assert len(re.findall(r'#\w+',out)) in (2,3)


@pytest.mark.parametrize('text',[
    'Şirket, iflas iddialarını yalanladı.',
    'TCMB, gelecek ayki faiz kararı öncesinde değerlendirme yayımladı.',
    'Geçen yıl tasfiye edilen fonun süreci incelendi.',
])
def test_denied_future_and_historical_events_are_not_decorated_as_urgent(text):
    assert '🚨' not in decorate(text,text)


@pytest.mark.parametrize('text,tag',[
    ('Şimşek: Yıllıklandırılmış cari açık 42,1 milyar dolar oldu.', 'caridenge'),
    ('Ağustosta cari fazla verildi.', 'caridenge'),
    ('Ödemeler dengesi verileri yayımlandı.', 'caridenge'),
    ('Merkezi yönetim bütçesi açık verdi.', 'bütçe'),
    ('Örnek Şirket temettü ödemesini onayladı.', 'temettü'),
    ('Örnek Şirket kâr payı dağıtacak.', 'temettü'),
    ('Bankaların ticari kredilerinde artış yaşandı.', 'kredi'),
])
def test_specific_financial_topics_precede_generic_tags(text,tag):
    tags=re.findall(r'#\w+',decorate(text,text))
    assert tags[0]=='#'+tag
    assert len(tags)==len(set(tags)) and len(tags)<=3


def test_credit_tag_does_not_match_accreditation():
    assert '#kredi' not in decorate('Haber','Şirket akreditasyon belgesi aldı.')
