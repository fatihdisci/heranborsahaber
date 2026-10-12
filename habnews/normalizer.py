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
TR_COMPANY=re.compile(r'\b(?:thy|thy.?ao|turkish airlines|aselsan|tüpraş|tupras|turkcell|türk telekom|koç holding|koc holding|sabancı|sabanci|şişecam|sisecam|garanti bbva|akbank|iş bankası|is bankası|yapı kredi|yapi kredi|halkbank|vakıfbank|vakifbank|ziraat bankası|pegasus|ford otosan|tofaş|tofas|petkim|arçelik|arcelik|vestel|sasa|erdemir|enerjisa|astor|ülker|ulker|türk traktör|turk traktor|mavi giyim|smart güneş|smart gunes|emlak konut|akfen|migros|bim|şok market|sok market|coca.?cola içecek|anadolu efes|doğuş otomotiv|dogus otomotiv|otokar|kardemir|gübre fabrikaları|gubretas|hektaş|hektas|alarko|enka|tav havalimanları|tav havalimanlari|çimsa|cimsa|oyak çimento|oyak cimento|kaleseramik|kontr|kontrolmatik|cw enerji|europower|gesan|borusan|reeder|koton|yapı ve kredi|yapi ve kredi|türkiye sigorta|turkiye sigorta)\b',re.I)
HYPE=re.compile(r'hisseyi uçur|piyasayı salla|hedef fiyat|al tavsiyesi|sat tavsiyesi|garanti kazanç|köşeyi dönecek|kaçırılmayacak fırsat',re.I)
# Independent OR routes: a domestic market, fund or regulator signal is enough.
# Place names, TL amounts and politicians alone never establish market relevance.
MARKET=re.compile(r"\b(?:spk|kap|sermaye piyasası kurulu|bist(?:\s*\d+)?|borsa istanbul|tefas|bes|bireysel emeklilik sistemi|vbts|takasbank|mkk|merkezi kayıt kuruluşu|yatırımcı tazmin merkezi)\b|halka arz|temettü|bedelli|bedelsiz|sermaye artır|açığa satış|devre kesici|pay geri al|hisse(?:ler|nin|ye|de|den|si| senedi| senetleri)?\b|portföy yönetim|yatırım ortaklığı",re.I)
STOCK_EXCHANGE=re.compile(r'\bborsa(?:da|dan|nın|ya|sı|yı|lar|ları)?\b',re.I)
COMMODITY_EXCHANGE=re.compile(r'ticaret borsası|emtia borsası|ürün ihtisas borsası',re.I)
FUND=re.compile(r'\bfon(?:u|un|a|da|dan|lar|ları|ların|larda|lardan|larına|larının|larında|larından|larındaki|una|unun|unda|undan)?\b',re.I)
FUND_CONTEXT=re.compile(r'yatırım|yatırımcı|para piyasası|portföy|tefas|tasfiye|stopaj|getiri|manipülasyon|soruşturma|kriz|ödeme|tazmin|iad[ea]|fon kurulu|fon yönetim|fon.*(?:giriş|çıkış|dondur)|(?:giriş|çıkış).*fon',re.I)
ISSUER_EVENT=re.compile(r'bilanço|finansal sonuç|k[âa]r(?:ı|ını|ında|\b)|zarar|gelir|ciro|hasılat|mevduat|kredi hacmi|yolcu say|doluluk oran|abone say|trafik sonuç|satış|sözleşme|anlaşma|sipariş|ihale|yatırım|üretim|kapasite|birleşme|satın al|devral|borç|finansman|kredi not|iflas|konkordato|yönetim kurulu|genel kurul|sermaye|\bpay(?:ı|ları|larının|larını|dan|da)?\b|iş birliği|işbirliği|ortaklık',re.I)
MACRO=re.compile(r'faiz|enflasyon|\btüfe\b|\büfe\b|\bppk\b|zorunlu karşılık|rezerv|likidite|para politikası|parasal sıkılaş|parasal genişle|\bgsy[iı]?h\b|ekonomik büyüme|büyüme (?:veri|oran|rakam)|cari (?:açık|açığ|fazla|denge)|bütçe (?:açık|açığ|fazla|denge)|işsizlik (?:oran|veri|rakam)|sanayi üretim|dış ticaret (?:açık|fazla|denge)|güven endeks|kredi derecelendir|kredi not|risk primi|\bcds\b|mevduat.*(?:artış|azal|çıkış|giriş|büyü)|(?:artış|azal).*mevduat|döviz.*(?:müdahale|düzenleme)|sermaye (?:akım|hareket)|yabancı yatırımcı|yabancı.*(?:alım|satış)|ödeme sistem|finansal istikrar|bankacılık.*(?:düzenleme|kriz)|stopaj|kurumlar vergisi',re.I)
FOREIGN_MARKET=re.compile(r'wall street|nasdaq|dow jones|s&p|new york borsası|tokyo borsası|avrupa borsaları|çin borsası|\bnikkei\b|\bdax\b|\bftse\b|\b(?:abd|amerikan|küresel|global|avrupa|çin|japonya)\b',re.I)
DOMESTIC_MARKET=re.compile(r'\b(?:spk|bist(?:\s*\d+)?|tefas|vbts|kap)\b|borsa istanbul|sermaye piyasası kurulu',re.I)
# These templates produce repeated consumer/reference notices, not new market events.
LOW_SIGNAL_TITLE=re.compile(r'personel alımı|eleman alımı|memur alımı|işçi alımı|iş ilanı|emekli.*promosyon|promosyon.*emekli|maaşını taşı|(?:mevduat|kredi|faiz|promosyon).{0,80}hangi banka|hangi banka.{0,80}(?:mevduat|kredi|faiz|promosyon)|banka banka|(?:dolar|euro|altın|gram|çeyrek).*(?:kaç (?:tl|lira)|ne kadar|güncel fiyat|fiyatları ne)|(?:en yüksek|en iyi).*mevduat|son depremler listesi|aktüel ürün|indirim katalo',re.I)
CRITICAL_MARKET=re.compile(r'tasfiye|işlem(?:leri)? durdur|işleme kapat|açığa satış.*yasak|temerrüt|iflas|konkordato|el koy|el kon|fon.*(?:dondur|ödeme|el kon)|tcmb.*(?:faiz karar|politika faiz)|ppk.*karar',re.I)

def classify(item):
    # Casefold of Turkish capital İ includes a combining dot; remove it only
    # for relevance matching, leaving source text and evidence untouched.
    title=norm(item['title']).replace('\u0307','')
    text=title+' '+norm(item.get('summary','')).replace('\u0307','')
    if ROUTINE_KAP.search(text) and not re.search(r'\bspk\b|sermaye piyasası kurulu',title):return 'scope_excluded','routine KAP share transaction'
    regulatory=bool(re.search(r'\bspk\b|sermaye piyasası kurulu',title) and re.search(r'düzenleme|ceza|suç duyur|soruştur|yasak|yaptırım',text))
    if HYPE.search(text) and not regulatory:return 'filtered','promotion'
    if LOW_SIGNAL_TITLE.search(title) and (re.search(r'personel alımı|eleman alımı|memur alımı|işçi alımı|iş ilanı',title) or not regulatory):return 'filtered','routine_consumer_or_recruitment'
    local_text=re.sub(r'\b(?:abd|amerikan|ingiltere|çin)\s+hazine', 'foreign treasury',text)
    local=bool(TURKEY.search(local_text) or TR_COMPANY.search(text) or re.search(r'\b(?:erdoğan|şimşek|karahan|tmsf|bddk|seddk)\b',text) or item.get('source_id') in ('tcmb','x-rterdogan','x-abakingurlek'))
    market=bool(MARKET.search(text) or STOCK_EXCHANGE.search(text) and not COMMODITY_EXCHANGE.search(text))
    fund=bool(FUND.search(text) and FUND_CONTEXT.search(text) and not re.search(r'uluslararası para fonu|\bimf\b|afet fonu|iklim fonu|sosyal yardım fonu',text))
    # A specific foreign market is not assumed to be a Turkish security.
    if FOREIGN_MARKET.search(text) and not (local or DOMESTIC_MARKET.search(text)):
        return 'filtered','no_turkey_relevance'
    if market:reason='capital_markets'
    elif fund and (local or not FOREIGN_MARKET.search(text)):reason='investment_funds'
    elif TR_COMPANY.search(text) and ISSUER_EVENT.search(text):reason='listed_company_material_event'
    elif local and (MACRO.search(text) or re.search(r'\b(?:bddk|seddk|tmsf)\b',text) and re.search(r'mevduat|kredi|sermaye|faaliyet izni|lisans|el koy|el kon|devir|tasfiye|sigorta.*(?:düzenleme|kural)',text)):reason='turkey_market_macro'
    else:return 'filtered','no_direct_market_relevance' if local else 'no_turkey_relevance'
    if CRITICAL_MARKET.search(text):return 'P0','critical_market_event'
    return 'P1',reason

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
