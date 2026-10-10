from pathlib import Path
from habnews.article import extract_document

URL='https://www.cnbce.com/borsa/bu-hafta-7-hisse-uzerindeki-yasaklar-kalkacak-h39178'


def test_cnbce_div_article_keeps_paragraphs_all_seven_rows_and_qualification():
    raw=(Path(__file__).parent/'fixtures/cnbce-h39178.html').read_bytes()
    doc=extract_document(raw,'text/html',URL)
    body=doc['body']
    assert body.startswith("Borsa İstanbul'da 7 hisse senedi")
    for code in ('MRGYO','YKSLN','CATES','CITAS','SELEC','AHSGY','KZGYO'):
        assert sum(line.startswith(code+' | ') for line in body.splitlines())==1
    assert '14.09.2026 | 13.10.2026' in body
    assert '16.09.2026 | 15.10.2026' in body
    assert 'brüt takas veya emir paketi gibi ek bir tedbir bulunmamaktadır' in body
    assert body.endswith('seans sonu itibarıyla sona erecektir.')
    assert 'UNRELATED' not in body


def test_nested_div_containers_do_not_repeat_paragraphs_or_include_related_news():
    first='Türkiye ekonomisine ilişkin açıklama, gerekli koşullar sağlanırsa yürürlüğe girecek.'
    second='Şirket, yatırımın tamamlanmasının ardından üretime başlayacağını bildirdi.'
    raw=f'<article><h1>Yatırım açıklaması</h1><div class="content-text"><div><div>{first}</div><div>{second}</div><div class="related-news">YANLIŞ HABER</div></div></div></article>'
    body=extract_document(raw.encode(),'text/html','https://example.test/article')['body']
    assert body==first+'\n'+second
