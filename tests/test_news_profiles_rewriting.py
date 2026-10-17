import pytest
from habnews.news_profiles import profile
from habnews.rewriting import rewrite_sentence
from habnews.editorial_prompt import model_policy,clipboard_prompt

@pytest.mark.parametrize('text,kind',[
 ('TCMB politika faizi kararı','rate'),('TÜFE aylık enflasyon','inflation'),
 ('Şimşek yıllıklandırılmış cari açık','current_account'),('Örnek Şirket net kâr bilanço','earnings'),
 ('Temettü teklifi genel kurulda','dividend'),('Şirket yeni sözleşme imzaladı','company'),
 ('Şirket yatırım iddialarını yalanladı','claim'),('Duyuru','general'),
])
def test_profile(text,kind):assert profile(text)['type']==kind

def test_both_prompts_include_type_specific_period_instructions():
 doc={'title':'Cari denge','body':'Aylık cari fazla açıklandı.','source_url':'https://example.test/news'}
 for prompt in (clipboard_prompt(doc,{'owner':'TEST'}),model_policy({'manual_attribution':{'source_type':'article'},'source_title':'Cari denge'}) ):
  assert 'HABER TÜRÜNE GÖRE ÖNCELİK' in prompt and 'yıllıklandırılmış' in prompt

@pytest.mark.parametrize('source,actor,want',[
 ('TCMB, politika faizini yüzde 40 olarak belirlediğini açıkladı.','TCMB','TCMB: Politika faizini %40 olarak belirledi.'),
 ('Örnek Şirket, 10 milyon TL tutarında yatırım yapmayı planladığını açıkladı.','Örnek Şirket','Örnek Şirket: 10 milyon TL tutarında yatırım yapmayı planlıyor.'),
 ('Örnek Şirket, 10 milyon dolar tutarında sözleşme imzaladığını bildirdi.','Örnek Şirket','Örnek Şirket: 10 milyon dolar tutarında sözleşme imzaladı.'),
])
def test_bounded_rewrite(source,actor,want):assert rewrite_sentence(source,actor)==want

@pytest.mark.parametrize('source',[
 'Örnek Şirket, izin alınması koşuluyla 10 milyon TL tutarında yatırım yapmayı planladığını açıkladı.',
 'Örnek Şirket, 10 milyon TL tutarında yatırım yapmayı planladığı iddiasını yalanladı.',
 'Örnek Şirket, 10 milyon TL tutarında yatırım yapmayı planladığını açıklamadı.',
 'TCMB, politika faizini yüzde 40 olarak belirlediğini açıkladı; karar henüz yürürlüğe girmedi.',
])
def test_conditions_denials_and_trailing_clauses_preserved(source):
 out=rewrite_sentence(source,source.split(',')[0])
 assert out==source.replace('yüzde 40','%40')

@pytest.mark.parametrize('text',['Artış yüzde 5 puan oldu.','“Faiz yüzde 40” açıklaması geldi.'])
def test_point_units_and_quotes_preserved(text):assert rewrite_sentence(text)==text
