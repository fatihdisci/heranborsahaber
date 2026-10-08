from pathlib import Path
from unittest.mock import Mock
import pytest
from habnews.gallery import parse_gallery, read_gallery, page_number
from habnews.article import extract_document

URL = 'https://www.ekonomim.com/foto-galeri/ekonomi/en-yuksek-mevduat-faizi-hangi-bankada-iste-1-milyon-tlnin-banka-banka-guncel-getirisi-galeri-923299'
DATA = (Path(__file__).parent/'fixtures/ekonomim-gallery.html').read_bytes()


def response(number, total=21, title=None):
    heading, _, _, _, _, _ = parse_gallery(DATA, 'text/html', URL, URL)
    body = f'BANKA {number}<p>Faiz Oranı: Yüzde 35</p><p>Net Kazanç: {number}.000 TL</p>'
    return (f'<link rel="canonical" href="{URL}"><article class="content-detail gallery-detail">'
            f'<header><h1>{title or heading}</h1><h2>Giriş metni</h2></header>'
            f'<div class="infinity-item" data-url="{URL}?p={number}">'
            f'<div property="articleBody"><p>BANKA {number}</p>{body}</div>'
            f'<span class="page">{number} | {total}</span></div></article>').encode()


def test_real_structure_reproduces_old_failure_and_selects_four_parts():
    with pytest.raises(ValueError, match='multiple_article_bodies_ambiguous'):
        extract_document(DATA, 'text/html', URL)
    title, intro, parts, total, links, images = parse_gallery(DATA, 'text/html', URL, URL)
    assert total == 21 and list(parts) == [1, 2, 3, 4]
    assert 'ZİRAAT KATILIM' in parts[1] and '21.195 TL' in parts[1]
    assert 'ZİRAAT DİNAMİK' in parts[2] and 'ENPARA' in parts[4]
    assert '32 günlük' in intro and 'mevduat' in title
    assert links[4] == URL + '?p=5'
    assert images[0]['url'].endswith('atm-kart-y32s.jpg')


def test_all_21_parts_in_order_and_no_unrelated_text():
    fetcher = Mock()
    fetcher.get.side_effect = lambda url: (response(int(url.split('=')[-1])), {'content-type':'text/html'}, url, 200)
    result = read_gallery(DATA, 'text/html', URL, fetcher, Mock())
    assert result['gallery_pages'] == 21 and fetcher.get.call_count == 17
    assert result['body'].index('ENPARA') < result['body'].index('BANKA 5') < result['body'].index('BANKA 21')
    assert '21.000 TL' in result['body']
    assert 'UNRELATED' not in result['body']
    assert result['body'].splitlines().count('Faiz Oranı: Yüzde 35') == 18


@pytest.mark.parametrize('bad', ['https://evil.example/?p=5', URL+'?p=99', URL+'?p=5&x=1', URL+'?p=5&p=6'])
def test_next_link_cannot_escape_gallery(bad):
    with pytest.raises(ValueError):
        parse_gallery(DATA.replace((URL+'?p=5').encode(), bad.encode()), 'text/html', URL, URL)


def test_missing_or_changed_slide_never_returns_partial_article():
    for chunk in (response(6), response(5, total=20), response(5, title='Başka haber')):
        fetcher = Mock(); fetcher.get.return_value = (chunk, {'content-type':'text/html'}, URL+'?p=5', 200)
        with pytest.raises(ValueError, match='gallery_content_mismatch'):
            read_gallery(DATA, 'text/html', URL, fetcher, Mock())


def test_fetch_failure_never_returns_first_four_only():
    fetcher = Mock(); fetcher.get.side_effect = RuntimeError('http_503')
    with pytest.raises(RuntimeError, match='http_503'):
        read_gallery(DATA, 'text/html', URL, fetcher, Mock())


def test_source_reader_uses_gallery_for_full_export(monkeypatch):
    from habnews.source_content import read_document
    fetcher = Mock()
    fetcher.get.side_effect = lambda url: (DATA if url == URL else response(int(url.split('=')[-1])), {'content-type':'text/html'}, url, 200)
    monkeypatch.setattr('habnews.source_content.Fetcher', lambda *args: fetcher)
    result = read_document({'url':URL,'title':'En yüksek mevduat faizi'}, {'enabled':True,'allowed_hosts':['www.ekonomim.com']}, Mock())
    assert result['method'] == 'ekonomim_gallery' and result['gallery_pages'] == 21
    assert 'BANKA 21' in result['body']


def test_continuation_without_header_uses_bound_publisher_title():
    import re
    chunk = response(5)
    heading = parse_gallery(DATA, 'text/html', URL, URL)[0]
    chunk = re.sub(b'<header>.*?</header>', b'', chunk)
    chunk = ('<meta property="og:title" content="'+heading+'">').encode() + chunk
    title, intro, parts, total, _, _ = parse_gallery(chunk, 'text/html', URL+'?p=5', URL)
    assert title == heading and intro == '' and 5 in parts and total == 21
    with pytest.raises(ValueError, match='gallery_header_missing'):
        parse_gallery(chunk, 'text/html', URL, URL)
