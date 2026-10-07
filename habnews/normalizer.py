import hashlib, re, time, unicodedata
from html import unescape
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from xml.etree import ElementTree as ET


def norm(text): return ' '.join(unicodedata.normalize('NFKC',text).casefold().split())
def digest(text): return hashlib.sha256(text.encode()).hexdigest()
def canonical(url):
    p=urlsplit(url); q=[(k,v) for k,v in parse_qsl(p.query) if not k.startswith('utm_') and k not in ('fbclid','gclid')]
    return urlunsplit((p.scheme,p.netloc,p.path,urlencode(q),''))
def date_value(raw):
    if not raw: return None,'unknown'
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw.strip()):
        from zoneinfo import ZoneInfo
        return datetime.fromisoformat(raw).replace(tzinfo=ZoneInfo('Europe/Istanbul')).timestamp(),'date'
    try:
        dt=datetime.fromisoformat(raw.replace('Z','+00:00'))
    except ValueError:
        try: dt=parsedate_to_datetime(raw)
        except (ValueError,TypeError): return None,'unknown'
    if dt.tzinfo is None: return None,'unknown'
    return dt.timestamp(),'second'

def fresh(item, now=None):
    now=now or time.time(); stamp=item.get('published_at'); precision=item.get('time_precision','unknown')
    if stamp is not None and stamp>now+60: return False,'future_quarantine'
    if stamp is not None and now-stamp>86400: return False,'old_event'
    if item.get('manual_requested_at') is not None:
        age=now-item['manual_requested_at']
        return (0<=age<=1800,'manual_request' if 0<=age<=1800 else 'expired')
    if precision=='second' and stamp is not None:
        return (now-stamp<=1800,'fresh' if now-stamp<=1800 else 'expired')
    first=item.get('first_seen_at',now)
    return (now-first<=1800,'newly_seen_time_unknown' if now-first<=1800 else 'expired')

ROUTINE_KAP=re.compile(r'(?:(?:\bkap\b|kamuyu aydınlatma).{0,180}(?:geri alım|pay alım|pay satış|pay satım|dkb)|(?:geri alım|pay alım|pay satış|pay satım|dkb).{0,180}(?:\bkap\b|kamuyu aydınlatma))',re.I)
TURKEY=re.compile(r'\b(?:türkiye|turkey|turkish|türk|tcmb|bist(?:\s*100)?|borsa istanbul|spk|sermaye piyasası kurulu|tefas|tüik|bddk|hazine|tbmm|resm[iî] gazete|türk lirası|\btl\b|\btry\b|ankara|istanbul|izmir|bursa|kocaeli|gaziantep|adana|konya|antalya|recep tayyip erdoğan|mehmet şimşek|fatih karahan|cevdet yılmaz)\b',re.I)
TR_COMPANY=re.compile(r'\b(?:thy|thy.?ao|turkish airlines|aselsan|tüpraş|tupras|turkcell|türk telekom|koç holding|koc holding|sabancı|sabanci|şişecam|sisecam|garanti bbva|akbank|iş bankası|is bankası|yapı kredi|yapi kredi|halkbank|vakıfbank|vakifbank|ziraat bankası|pegasus|ford otosan|tofaş|tofas|petkim|arçelik|arcelik|vestel|sasa|erdemir|enerjisa|astor|ülker|ulker|türk traktör|turk traktor|mavi giyim)\b',re.I)
HYPE=re.compile(r'hisseyi uçur|piyasayı salla|hedef fiyat|al tavsiyesi|sat tavsiyesi|garanti kazanç',re.I)
def classify(item):
    text=item['title']+' '+item.get('summary','')
    if ROUTINE_KAP.search(text): return 'scope_excluded','routine KAP share transaction'
    if HYPE.search(text): return 'filtered','promotion'
    # Generic global market terms alone are noisy. A Turkey reference, local
    # institution, lira, or domestic issuer is sufficient relevance evidence.
    if not (TURKEY.search(text) or TR_COMPANY.search(text) or item.get('source_id')=='tcmb'):
        return 'filtered','no_turkey_relevance'
    if re.search(r'TCMB.*(faiz|karar)|işlem durdur|piyasa.*kesinti|tasfiye',text,re.I): return 'P0','critical_decision'
    return 'P1','turkey_relevance'

def event_key(item):
    """Only explicit macro identities auto-cluster. Other semantic matches require review."""
    t=norm(item['title']+' '+item.get('summary','')); stamp=item.get('published_at')
    day=datetime.fromtimestamp(stamp or item['first_seen_at'],timezone.utc).date().isoformat()
    if 'tcmb' in t and 'faiz' in t and ('karar' in t or 'politika' in t): return f'tcmb:policy_rate:{day}'
    period=re.search(r'(20\d{2})[-/](0[1-9]|1[0-2])',t)
    if 'tüfe' in t and period: return 'tuik:cpi:'+period.group(0)
    return 'exact:'+digest(norm(item['title']))

def material_signature(item):
    text=norm(item['title']+' '+item.get('summary',''))
    numbers=re.findall(r'(?<!\w)[+-]?\d+(?:[.,]\d+)*(?:\s*(?:%|baz puan|milyar|milyon|tl|adet|lot))?',text)
    stages=[s for s in ('başvuru','onay','karar','gerçekleş','artır','indir','değiştir','değil','aylık','yıllık') if s in text]
    return digest('|'.join(sorted(numbers)+sorted(stages))) if numbers else digest(text)

class FeedText(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)
def feed_text(raw):
    parser=FeedText();parser.feed(raw);return ' '.join(' '.join(parser.parts).split())

def parse_feed(data,source_id):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper(): raise ValueError('xml_entity_denied')
    root=ET.fromstring(data)
    if root.tag.split('}')[-1] not in ('rss','feed','RDF'): raise ValueError('not_feed')
    entries=root.findall('.//item')+root.findall('{http://www.w3.org/2005/Atom}entry')
    def field(node,*names):
        for name in names:
            el=node.find(name)
            if el is not None and el.text: return el.text.strip()
        return ''
    result=[]
    for node in entries[:200]:
        title=field(node,'title','{http://www.w3.org/2005/Atom}title')
        url=field(node,'link')
        if not url:
            link=node.find('{http://www.w3.org/2005/Atom}link'); url=link.get('href','') if link is not None else ''
        if not title or not url: continue
        raw=field(node,'pubDate','{http://www.w3.org/2005/Atom}published','{http://www.w3.org/2005/Atom}updated')
        stamp,precision=date_value(raw)
        result.append({'source_id':source_id,'provider_id':field(node,'guid','{http://www.w3.org/2005/Atom}id') or canonical(url),
                       'url':canonical(url),'title':feed_text(title),'summary':feed_text(field(node,'description','{http://www.w3.org/2005/Atom}summary')),
                       'published_at':stamp,'time_precision':precision,'first_seen_at':time.time()})
    return result

# Article extraction lives separately so selectors and noise boundaries are testable.
from .article import extract_document

def extract_article(data,mime):
    return extract_document(data,mime)['body']
