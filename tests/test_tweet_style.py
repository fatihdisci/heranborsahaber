import re
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

def test_fund_liquidation_uses_attention_emoji_without_false_breaking_claim():
    out=decorate('Karahan: Mevduatlarda 800 milyar TL artış','Tasfiye sürecindeki fonlardan çıkış yaşandı.')
    assert out.startswith('🚨 Karahan:')
    assert 'SON DAKİKA' not in out
    assert len(re.findall(r'#\w+',out)) in (2,3)
