"""Select one complete CNBC-e gallery, keeping article tables and slide order."""
import re
from urllib.parse import urlsplit, urljoin, parse_qs
from .article import body_node, clean, visible_walk, same_page


def select_gallery(nodes, url):
    parsed = urlsplit(url)
    if parsed.hostname not in ('www.cnbce.com', 'cnbce.com') or not re.search(r'-g\d+$', parsed.path):
        return None
    items = [n for n in nodes if 'gallery-item' in n.attrs.get('class', '').split()]
    if not items:
        raise ValueError('cnbce_gallery_missing')
    parts = {}; totals = set()
    for item in items:
        target = urljoin(url, item.attrs.get('data-url', ''))
        p = urlsplit(target); query = parse_qs(p.query, keep_blank_values=True)
        base = p._replace(query='', fragment='').geturl()
        if not same_page(base, url) or p.fragment or p.username or p.password:
            raise ValueError('cnbce_gallery_cross_article')
        number = item.attrs.get('data-page', '')
        if not re.fullmatch(r'[1-9]\d*', number):
            raise ValueError('cnbce_gallery_page_invalid')
        number = int(number)
        if (query and query != {'sayfa':[str(number)]}) or not query and number != 1:
            raise ValueError('cnbce_gallery_url_page_mismatch')
        scoped = list(visible_walk(item))
        def counter(name):
            values = [clean(n.text()) for n in scoped if n.tag == 'span' and name in n.attrs.get('class', '').split()]
            if len(values) != 1 or not values[0].isdigit():
                raise ValueError('cnbce_gallery_counter_missing')
            return int(values[0])
        total = counter('total')
        if counter('page') != number or not 1 <= number <= total <= 80 or number in parts:
            raise ValueError('cnbce_gallery_counter_invalid')
        roots = [n for n in scoped if body_node(n)]
        if len(roots) != 1 or not clean(roots[0].text()):
            raise ValueError('cnbce_gallery_body_missing')
        parts[number] = roots[0]; totals.add(total)
    if len(totals) != 1 or set(parts) != set(range(1, next(iter(totals)) + 1)):
        raise ValueError('cnbce_gallery_incomplete')
    summaries = [n for n in nodes if 'post-summary' in n.attrs.get('class', '').split()]
    if len(summaries) > 1:
        raise ValueError('cnbce_gallery_summary_ambiguous')
    intro = clean(summaries[0].text()) if summaries else ''
    return [parts[n] for n in sorted(parts)], intro, len(parts)
