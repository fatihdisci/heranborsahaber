"""TCMB homepage announcement cards, discovered from actual official markup.
Not an exhaustive historical feed. Dynamic URL year, never a fixed-year scan.
"""
import re,time
from html.parser import HTMLParser
from urllib.parse import urljoin
from .normalizer import date_value,canonical

class TCMBParser(HTMLParser):
    def __init__(self):super().__init__();self.card=None;self.field=None;self.items=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);classes=attrs.get('class','').split()
        if tag=='a' and 'tab-content-box' in classes:
            href=attrs.get('href','')
            if re.search(r'/duyurular/basin/20\d{2}/duy20\d{2}-\d+$',href,re.I):self.card={'href':href,'title':'','day':'','month':''}
        if self.card:
            for key,css in [('title','tab-content-text'),('day','tab-content-date-day'),('month','tab-content-date-month')]:
                if css in classes:self.field=key
    def handle_data(self,data):
        if self.card and self.field:self.card[self.field]+=data
    def handle_endtag(self,tag):
        if tag=='a' and self.card:self.items.append(self.card);self.card=None;self.field=None
        elif tag in ('p','div'):self.field=None

def parse_tcmb_home(data,source_id):
    parser=TCMBParser();parser.feed(data.decode('utf-8','replace'))
    if not parser.items:raise ValueError('tcmb_card_parser_failure')
    items=[]
    for card in parser.items[:10]:
        year=re.search(r'/basin/(20\d{2})/',card['href'],re.I).group(1)
        try:stamp,precision=date_value(f"{year}-{int(card['month']):02d}-{int(card['day']):02d}")
        except ValueError:stamp=None;precision='unknown'
        url=canonical(urljoin('https://www.tcmb.gov.tr/',card['href']))
        items.append({'source_id':source_id,'provider_id':url.lower(),'url':url,'title':'TCMB: '+card['title'].strip(),'summary':'','published_at':stamp,'time_precision':precision,'first_seen_at':time.time()})
    return items
