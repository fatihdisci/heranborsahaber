from habnews.article import extract_document
from habnews.normalizer import parse_feed,classify
import pytest

@pytest.mark.parametrize('url,css',[('https://www.trthaber.com/haber/ekonomi/x.html','news-content'),('https://www.aa.com.tr/tr/ekonomi/x/1','embed-responsive prose other')])
def test_publisher_body_excludes_footer_and_summary(url,css):
    body='Merkez Bankası faiz kararı ile ilgili açıklama yaptı. '+ 'Haberin ana metnindeki ayrıntılar burada yer alıyor. '*4
    html=f'<h1>Ekonomi haberi</h1><div class="{css}"><p>{body}</p></div><footer><p>ABONE OL</p></footer><script type="application/ld+json">{{"@type":"NewsArticle","articleBody":"Kısa özet"}}</script>'
    doc=extract_document(html.encode(),'text/html',url)
    assert doc['body']==body.strip()
    assert 'ABONE' not in doc['body']
    assert doc['method']=='article_body'

def test_rss_html_summary_does_not_show_image_markup():
    feed=b'<rss><channel><item><title>Ekonomi</title><link>https://example.org/x</link><description><![CDATA[<img src="x"/>Yeni <b>faiz</b> karari<script>bad</script>]]></description></item></channel></rss>'
    assert parse_feed(feed,'trt')[0]['summary']=='Yeni faiz karari'

@pytest.mark.parametrize('headline',['Petrol fiyatı yükseldi','Altın fiyatı geriledi','Fed faiz kararı','Döviz piyasalarında hareketlilik'])
def test_global_market_categories_require_a_turkey_connection(headline):
    assert classify({'title':headline})[0]=='filtered'
    assert classify({'title':headline,'summary':'Türkiye ekonomisine ilişkin etkileri değerlendirildi.'})[0] in ('P0','P1')


def test_aa_streamed_body_not_short_jsonld_summary():
    body='Gerçek haberin kamuya açık metni ve sayısal açıklamalar. '*5
    html='<div hidden><div class="embed-responsive prose"><p>'+body+'</p></div></div>'
    doc=extract_document(html.encode(),'text/html','https://www.aa.com.tr/tr/ekonomi/x/1')
    assert doc['body']==body.strip()
