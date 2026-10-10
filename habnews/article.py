"""Select one article and its own body, excluding navigation and recommendations."""
import json,re
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit,unquote

class Node:
    def __init__(self,tag='',attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child,Node):yield from child.walk()
    def text(self):
        if ignored(self):return ''
        return ''.join(('\n'+c.text()+'\n' if c.tag in ('p','div','li','h1','h2','h3','blockquote') else c.text()) if isinstance(c,Node) else c for c in self.children)

NOISE=re.compile(r'(?:^|[\s_-])(?:related|suggested|recommend|advertisement|adv|newsletter|social|share|comments|news-list|google-news|footer|navigation|widget|tags|tag-list)(?:[\s_-]|$)',re.I)
def ignored(node):
    return node.tag in ('script','style','nav','aside','footer','header','form','button','iframe','noscript','template') or 'hidden' in node.attrs or node.attrs.get('aria-hidden')=='true' or node.attrs.get('role') in ('navigation','dialog') or bool(NOISE.search(node.attrs.get('class','')+' '+node.attrs.get('id','')))

class Tree(HTMLParser):
    VOID={'meta','link','img','input','hr','br','source','wbr','embed','area','base','col','param','track'}
    def __init__(self):super().__init__();self.root=Node('root');self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs);self.stack[-1].children.append(node)
        if tag=='br':node.children.append('\n')
        if tag not in self.VOID:self.stack.append(node)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:del self.stack[i:];break
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in self.VOID:self.handle_endtag(tag)
    def handle_data(self,data):self.stack[-1].children.append(data)

BODY_CLASSES={'article-wrapper','article-body','content-text','news-detail-content','news-content-body','news-text','cms-container','detail-content','tcmb-content'}
def body_node(n):
    return 'articleBody' in (n.attrs.get('itemprop','')+' '+n.attrs.get('property','')).split() or bool(set(n.attrs.get('class','').split()) & BODY_CLASSES)
def visible_walk(node,skip_nested_articles=False,_root=True):
    if ignored(node):return
    if skip_nested_articles and not _root and node.tag=='article':return
    yield node
    for child in node.children:
        if isinstance(child,Node):yield from visible_walk(child,skip_nested_articles,False)
def clean(text):return ' '.join(text.split())

def same_page(left,right):
    from .normalizer import canonical
    a,b=(urlsplit(canonical(v)) for v in (left,right))
    return (a.hostname,unquote(a.path).rstrip('/'),a.query)==(b.hostname,unquote(b.path).rstrip('/'),b.query)

def outer_roots(roots):
    return [r for r in roots if not any(r is not other and any(n is r for n in other.walk()) for other in roots)]

def extract_document(data,mime,url='',expected_title='',requested_url=''):
    if 'html' not in mime:raise ValueError('unsupported_article_mime')
    charset=re.search(r'charset=["\s]*([\w-]+)',mime,re.I)
    encoding=charset.group(1) if charset else 'utf-8'
    if encoding.lower() not in ('utf-8','utf8','windows-1254','iso-8859-9'):raise ValueError('unsupported_article_encoding')
    decoded=data.decode(encoding,errors='replace')
    if decoded.count('\ufffd')>max(3,len(decoded)//1000):raise ValueError('article_encoding_damaged')
    tree=Tree();tree.feed(decoded);all_nodes=list(tree.root.walk())
    meta={n.attrs.get('property',n.attrs.get('name','')):n.attrs.get('content','') for n in all_nodes if n.tag=='meta'}
    canonical_links={urljoin(url,n.attrs['href']) for n in all_nodes if n.tag=='link' and 'canonical' in n.attrs.get('rel','').split() and n.attrs.get('href')}
    declared=canonical_links or ({urljoin(url,meta['og:url'])} if meta.get('og:url') else set())
    if url and declared and (len(declared)!=1 or not same_page(next(iter(declared)),url)):raise ValueError('article_url_mismatch')
    articles=[n for n in visible_walk(tree.root) if n.tag=='article']
    matched=[n for n in articles if url and n.attrs.get('data-url') and same_page(urljoin(url,n.attrs['data-url']),url)]
    headed=[n for n in articles if any(x.tag=='h1' for x in visible_walk(n,True))]
    candidates=matched or headed or outer_roots(articles)
    if len(candidates)>1:raise ValueError('multiple_articles_ambiguous')
    selected=candidates[0] if candidates else tree.root
    nodes=list(visible_walk(selected,True));roots=[n for n in nodes if body_node(n)]
    host=urlsplit(url).hostname
    publisher_classes={'www.trthaber.com':{'news-content'},'www.aa.com.tr':{'embed-responsive','prose'},
        'www.foreks.com':{'Detay'},'foreks.com':{'Detay'},'www.haberturk.com':{'cms-container'},
        'haberturk.com':{'cms-container'},'www.ntv.com.tr':{'ck-content'},'tr.euronews.com':{'c-article-content'}}
    required=publisher_classes.get(host)
    if required:
        # AA streams the public body inside a React suspense wrapper marked hidden.
        # Select only its unique article prose block, never arbitrary hidden page text.
        candidates=all_nodes if host=='www.aa.com.tr' else nodes
        scoped=[n for n in candidates if required.issubset(set(n.attrs.get('class','').split()))]
        if scoped:roots=outer_roots(scoped)
    # Prefer the inner body over an article-wide wrapper that also contains UI.
    if not required:roots=[r for r in roots if not any(n is not r and body_node(n) for n in r.walk())]
    from .cnbce_gallery import select_gallery
    gallery=select_gallery(nodes,url)
    if gallery:roots=gallery[0]
    if len(roots)>1 and host!='www.ntv.com.tr' and not gallery:raise ValueError('multiple_article_bodies_ambiguous')
    chosen=roots or ([selected] if articles else [])
    paragraphs=[gallery[1]] if gallery and gallery[1] else []
    def blocks(n,root=True):
        if ignored(n) or not root and n.tag=='article':return
        # Publishers also use leaf divs as paragraphs; never flatten their
        # parent containers, which may contain ads, related news or tables.
        leaf_div=n.tag=='div' and not root and not any(child is not n and child.tag in ('div','p','h1','h2','h3','table','ul','ol','li','section','article') for child in n.walk())
        if n.tag in ('p','h2','h3','li','table') or leaf_div:
            yield n;return
        for child in n.children:
            if isinstance(child,Node):yield from blocks(child,False)
    for root in chosen:
        for n in blocks(root):
                if n.tag=='table':
                    text='\n'.join(' | '.join(clean(cell.text()) for cell in row.children if isinstance(cell,Node) and cell.tag in ('td','th')) for row in visible_walk(n) if row.tag=='tr')
                else:text=clean(n.text())
                if len(text)>=(1 if gallery else 8) and not re.match(r'^(?:FOTO(?:ĞRAF)?|Fotoğraf kaynağı)\s*:',text,re.I) and (gallery or text not in paragraphs):paragraphs.append(text)
        if not paragraphs and roots and not any(n.tag in ('p','h2','h3','li') for n in root.walk()):
            paragraphs=[clean(root.text())]
    headline=next((clean(n.text()) for n in nodes if n.tag=='h1' and clean(n.text())),meta.get('og:title',''))
    method='cnbce_gallery' if gallery else ('article_body' if roots else 'single_article')
    if not paragraphs:
        # Structured articleBody is a source-owned alternative, never a whole-page fallback.
        objects=[]
        def visit(v):
            if isinstance(v,list):
                for x in v:visit(x)
            if isinstance(v,dict):
                kinds=v.get('@type',[]);kinds=[kinds] if isinstance(kinds,str) else kinds
                if any(k in ('NewsArticle','Article','ReportageNewsArticle') for k in kinds) and isinstance(v.get('articleBody'),str):objects.append(v)
                if '@graph' in v:visit(v['@graph'])
        for n in all_nodes:
            if n.tag=='script' and n.attrs.get('type')=='application/ld+json':
                try:visit(json.loads(''.join(c for c in n.children if isinstance(c,str))))
                except (ValueError,TypeError):pass
        matches=[v for v in objects if isinstance(v.get('url'),str) and url and same_page(urljoin(url,v['url']),url)]
        if len(matches)==1 or len(objects)==1 and (not objects[0].get('url') or not url):
            obj=matches[0] if matches else objects[0];fragment=Tree();fragment.feed(obj['articleBody'])
            paragraphs=[clean(fragment.root.text())];headline=clean(obj.get('headline') or headline);method='jsonld_article_body'
    body='\n'.join(paragraphs)
    if len(body)<80:raise ValueError('main_text_missing_or_parser_needs_review')
    if len(body)>45000:raise ValueError('article_too_long_for_verified_model_input')
    if expected_title and headline and (not declared or requested_url and not same_page(requested_url,url)):
        words=lambda s:set(re.findall(r'\w{3,}',s.casefold()))
        a,b=words(expected_title),words(headline)
        if a and b and len(a&b)/min(len(a),len(b))<0.25:raise ValueError('article_title_mismatch')
    images=[]
    def add_image(raw,selection):
        if not isinstance(raw,str) or not raw.strip():return
        try:
            image=urljoin(url,raw.strip());p=urlsplit(image)
            if p.scheme!='https' or p.username is not None or p.password is not None or p.port not in (None,443) or p.fragment:return
        except ValueError:return
        if re.search(r'(?:^|[/_.-])(?:logo|avatar|icon|banner|sprite|blank|loading|placeholder)(?:[/_.-]|$)',p.path,re.I):return
        if image not in {v['url'] for v in images}:images.append({'url':image,'method':selection})
    meta_bound=not (articles and selected is not articles[0] and not declared)
    if meta_bound:
        for key in ('og:image:secure_url','og:image','twitter:image','twitter:image:src'):add_image(meta.get(key),key)
    structured=[]
    def collect_images(value):
        if isinstance(value,list):
            for v in value:collect_images(v)
        elif isinstance(value,dict):
            kinds=value.get('@type',[]);kinds=[kinds] if isinstance(kinds,str) else kinds
            if any(k in ('NewsArticle','Article','ReportageNewsArticle') for k in kinds):structured.append(value)
            if '@graph' in value:collect_images(value['@graph'])
    for n in all_nodes:
        if n.tag=='script' and n.attrs.get('type')=='application/ld+json':
            try:collect_images(json.loads(''.join(c for c in n.children if isinstance(c,str))))
            except (ValueError,TypeError):pass
    for obj in structured:
        linked=obj.get('url') or obj.get('mainEntityOfPage')
        if isinstance(linked,dict):linked=linked.get('@id') or linked.get('url')
        bound=isinstance(linked,str) and url and same_page(urljoin(url,linked),url)
        if not bound and not (len(structured)==1 and not linked and meta_bound):continue
        values=obj.get('image',[]);values=values if isinstance(values,list) else [values]
        for value in values:add_image(value.get('url') or value.get('contentUrl') if isinstance(value,dict) else value,'jsonld:image')
    for n in nodes:
        if n.tag!='img' or not articles and n.attrs.get('itemprop')!='image':continue
        if re.search(r'author|avatar|logo|related|banner',n.attrs.get('class',''),re.I):continue
        add_image(n.attrs.get('data-src') or n.attrs.get('data-original') or n.attrs.get('src'),'article:img')
    image=images[0]['url'] if images else None
    return {'title':headline,'body':body,'image_url':image,'image_candidates':images[:3],'preview_url':url if image else None,'method':method,'source_url':url,'canonical_url':next(iter(declared),url),'paragraph_count':len(paragraphs),**({'gallery_pages':gallery[2]} if gallery else {})}
