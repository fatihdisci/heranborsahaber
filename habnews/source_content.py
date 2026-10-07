"""One source reader shared by tweet production and complete clipboard export."""
from .network import Fetcher


def read_document(item, source, guard):
    if not source.get('enabled', True) or source.get('article_access') == 'blocked_http_403':
        raise ValueError('source_unavailable')
    guard()
    if source.get('method') == 'nitter_rss':
        from .social import check_source
        check_source(source)
        if item.get('x_account') != source['x_account'] or item.get('source_type') != 'social_x':
            raise ValueError('social_job_mismatch')
        return {'title': item['title'], 'body': item['full_post'], 'source_url': item['url'],
                'preview_url': item['url'], 'method': 'social_rss'}
    data, meta, url, _ = Fetcher(source['allowed_hosts'], guard).get(item['url'])
    from .article import extract_document
    return extract_document(data, meta.get('content-type', ''), url,
                            expected_title=item['title'], requested_url=item['url'])


def document_text(document, source):
    if source.get('method') == 'nitter_rss': return document['body']
    return (document['title'] + '\n\n' if document['title'] else '') + document['body']


def document_photo(document, source, directory, guard):
    if source.get('method') == 'nitter_rss': return None
    from .article_media import article_photo
    from .images import matched_official_archive
    return (article_photo(document, source, directory, guard)
            or matched_official_archive(document['title'], directory, guard,
                                        article_body=document['body']))
