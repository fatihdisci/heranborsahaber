from pathlib import Path
import re
import pytest
from habnews.article import extract_document,Tree


def fixture(id):
    raw=(Path(__file__).parent/'fixtures'/('cnbce-'+id+'.html')).read_bytes()
    t=Tree();t.feed(raw.decode())
    url=next(n.attrs['href'] for n in t.root.walk() if n.tag=='link')
    return raw,url


@pytest.mark.parametrize('id,count,last',[('g39045',7,'lojistik gayrimenkul'),('g39044',38,'58.620 lot')])
def test_actual_gallery_preserves_every_slide_and_final_detail(id,count,last):
    raw,url=fixture(id);doc=extract_document(raw,'text/html',url)
    assert doc['method']=='cnbce_gallery' and doc['gallery_pages']==count
    assert last in doc['body'] and 'UNRELATED' not in doc['body']
    assert doc['image_url'].startswith('https://img.cnbce.com/')


def test_buyback_tables_keep_all_37_company_rows_and_lots():
    raw,url=fixture('g39044');body=extract_document(raw,'text/html',url)['body']
    rows=[r for r in body.splitlines() if r.endswith(' lot')]
    assert len(rows)==37
    assert 'BLCYT | Bilici Yatırım Sanayi ve Ticaret A.Ş. | 2.027.518 lot' in rows
    assert rows[-1]=='PCILT | PC İletişim ve Medya Hizmetleri Sanayi Ticaret A.Ş. | 58.620 lot'
    assert body.index('BLCYT |') < body.index('PCILT |')


@pytest.mark.parametrize('change', ['missing','duplicate','foreign','counter'])
def test_ambiguous_or_incomplete_gallery_never_returns_partial_body(change):
    raw,url=fixture('g39045');html=raw.decode()
    if change=='missing':html=re.sub(r'<div class="gallery-item".*?</aside></div>', '',html,count=1,flags=re.S)
    if change=='duplicate':html=html.replace('data-page="2"','data-page="1"')
    if change=='foreign':html=html.replace(url+'?sayfa=2','https://evil.example/story?sayfa=2')
    if change=='counter':html=html.replace('<span class="total">7</span>','<span class="total">8</span>',1)
    with pytest.raises(ValueError,match='cnbce_gallery_'):extract_document(html.encode(),'text/html',url)


def test_shared_reader_used_by_tweet_and_gpt_export(monkeypatch):
    from habnews.source_content import read_document
    raw,url=fixture('g39044')
    monkeypatch.setattr('habnews.source_content.Fetcher.get',lambda *args:(raw,{'content-type':'text/html'},url,200))
    doc=read_document({'url':url,'title':'37 şirket borsada kendi paylarını aldı'},{'enabled':True,'allowed_hosts':['www.cnbce.com']},lambda:None)
    assert doc['gallery_pages']==38 and '58.620 lot' in doc['body']
