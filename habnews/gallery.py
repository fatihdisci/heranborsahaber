"""Read a complete, publisher-bound Ekonomim gallery without unrelated page text."""
import re
from urllib.parse import urlsplit, urlunsplit, parse_qs, urljoin
from .article import Tree, clean, body_node, visible_walk, same_page

MAX_PAGES = 40
MAX_TEXT = 45000


def gallery_base(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in ('www.ekonomim.com', 'ekonomim.com') or not re.fullmatch(r'/foto-galeri/[^/]+/[^/]+-galeri-\d+', p.path):
        return None
    if p.username or p.password or p.port not in (None, 443) or p.fragment:
        raise ValueError('gallery_url_invalid')
    return urlunsplit((p.scheme, p.netloc, p.path, '', ''))


def page_number(url, base):
    if gallery_base(url) != base:
        raise ValueError('gallery_cross_article')
    query = parse_qs(urlsplit(url).query, keep_blank_values=True)
    if not query:
        return 1
    if set(query) != {'p'} or len(query['p']) != 1 or not re.fullmatch(r'[1-9]\d*', query['p'][0]):
        raise ValueError('gallery_page_invalid')
    number = int(query['p'][0])
    if number > MAX_PAGES:
        raise ValueError('gallery_page_limit')
    return number


def parse_gallery(data, mime, url, base):
    if 'html' not in mime:
        raise ValueError('unsupported_article_mime')
    charset = re.search(r'charset=["\s]*([\w-]+)', mime, re.I)
    encoding = charset.group(1) if charset else 'utf-8'
    if encoding.lower() not in ('utf-8', 'utf8', 'windows-1254', 'iso-8859-9'):
        raise ValueError('unsupported_article_encoding')
    decoded = data.decode(encoding, errors='replace')
    if decoded.count('\ufffd') > max(3, len(decoded)//1000):
        raise ValueError('article_encoding_damaged')
    tree = Tree(); tree.feed(decoded)
    all_nodes = list(tree.root.walk())
    declared = [urljoin(url, n.attrs['href']) for n in all_nodes if n.tag == 'link' and 'canonical' in n.attrs.get('rel', '').split() and n.attrs.get('href')]
    if not declared or any(gallery_base(v) != base for v in declared):
        raise ValueError('gallery_canonical_mismatch')
    containers = [n for n in all_nodes if n.tag == 'article' and {'gallery-detail', 'content-detail'}.issubset(n.attrs.get('class', '').split())]
    if len(containers) != 1:
        raise ValueError('gallery_container_ambiguous')
    container = containers[0]
    headers = [n for n in container.children if getattr(n, 'tag', '') == 'header']
    if len(headers) > 1 or not headers and page_number(url, base) == 1:
        raise ValueError('gallery_header_missing')
    if headers:
        title = next((clean(n.text()) for n in headers[0].walk() if n.tag == 'h1'), '')
        intro = next((clean(n.text()) for n in headers[0].walk() if n.tag == 'h2'), '')
    else:
        # Subsequent public gallery pages omit the header. Canonical binding above
        # and the same publisher headline below still identify the original story.
        meta = {n.attrs.get('property'): n.attrs.get('content', '') for n in all_nodes if n.tag == 'meta'}
        title = clean(meta.get('og:title', ''))
        intro = ''
    if not title:
        raise ValueError('gallery_title_missing')
    parts = {}; totals = set(); next_links = {}; images = []
    for item in container.children:
        if not hasattr(item, 'attrs') or 'infinity-item' not in item.attrs.get('class', '').split():
            continue
        number = page_number(urljoin(url, item.attrs.get('data-url', '')), base)
        nodes = list(visible_walk(item))
        counters = [clean(n.text()) for n in nodes if n.tag == 'span' and 'page' in n.attrs.get('class', '').split()]
        if len(counters) != 1 or not re.fullmatch(r'\d+\s*\|\s*\d+', counters[0]):
            raise ValueError('gallery_counter_missing')
        index, total = map(int, counters[0].split('|'))
        if index != number or not 1 <= index <= total <= MAX_PAGES:
            raise ValueError('gallery_counter_invalid')
        totals.add(total)
        roots = [n for n in nodes if body_node(n)]
        image_only_last = not roots and number == total and any(n.tag == 'img' for n in nodes)
        if len(roots) != 1 and not image_only_last:
            raise ValueError('gallery_body_ambiguous')
        # Keep repeated labels: each bank's rate/balance belongs to that bank.
        body = '' if image_only_last else '\n'.join(clean(n.text()) for n in visible_walk(roots[0]) if n.tag == 'p' and clean(n.text()))
        if not body and roots:
            body = clean(roots[0].text())
        if (len(body) < 20 and not image_only_last) or number in parts:
            raise ValueError('gallery_body_missing_or_duplicate')
        parts[number] = body
        raw_next = item.attrs.get('data-next')
        if raw_next and number < total:
            target = urljoin(url, raw_next)
            if page_number(target, base) != number + 1:
                raise ValueError('gallery_next_invalid')
            next_links[number] = target
        for node in nodes:
            if node.tag != 'img':
                continue
            raw = node.attrs.get('data-src') or node.attrs.get('src', '')
            image = urljoin(url, raw); parsed = urlsplit(image)
            if parsed.scheme == 'https' and parsed.hostname == 'img.ekonomim.com' and not parsed.username and not parsed.password and parsed.port in (None, 443) and not parsed.fragment and parsed.path.startswith('/storage/files/images/'):
                if image not in [v['url'] for v in images]:
                    images.append({'url': image, 'method': 'article:img'})
    if not parts or len(totals) != 1:
        raise ValueError('gallery_count_inconsistent')
    return title, intro, parts, totals.pop(), next_links, images


def read_gallery(data, mime, url, fetcher, guard):
    base = gallery_base(url)
    page_number(url, base)
    title, intro, parts, total, next_links, images = parse_gallery(data, mime, url, base)
    # Start at page one even if an RSS item happens to point at a later slide.
    visited = {url}; size = len(data)
    while set(parts) != set(range(1, total + 1)):
        missing = next(n for n in range(1, total + 1) if n not in parts)
        target = next_links.get(missing - 1, base if missing == 1 else base + '?p=' + str(missing))
        if target in visited or len(visited) >= MAX_PAGES:
            raise ValueError('gallery_incomplete')
        guard(); visited.add(target)
        chunk, meta, final_url, _ = fetcher.get(target)
        size += len(chunk)
        if size > 8_000_000:
            raise ValueError('gallery_size_limit')
        if page_number(final_url, base) != missing:
            raise ValueError('gallery_redirect_mismatch')
        heading, incoming_intro, incoming, count, links, candidates = parse_gallery(chunk, meta.get('content-type', ''), final_url, base)
        if heading != title or count != total or missing not in incoming:
            raise ValueError('gallery_content_mismatch')
        for number, body in incoming.items():
            if number in parts and parts[number] != body:
                raise ValueError('gallery_changed_during_read')
            parts[number] = body
        if not intro and incoming_intro:
            intro = incoming_intro
        next_links.update(links)
        for candidate in candidates:
            if candidate['url'] not in [v['url'] for v in images]:
                images.append(candidate)
        if sum(map(len, parts.values())) + len(intro) > MAX_TEXT:
            raise ValueError('article_too_long_for_verified_model_input')
    body = '\n\n'.join(([intro] if intro else []) + [parts[n] for n in range(1, total + 1)])
    if not 80 <= len(body) <= MAX_TEXT:
        raise ValueError('gallery_text_size')
    guard()
    image = images[0]['url'] if images else None
    return {'title': title, 'body': body, 'source_url': base, 'canonical_url': base,
            'preview_url': base if image else None, 'image_url': image,
            'image_candidates': images[:3], 'method': 'ekonomim_gallery',
            'paragraph_count': len(body.splitlines()), 'gallery_pages': total, 'image_only_pages': [n for n in parts if not parts[n]]}
