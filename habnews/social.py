"""Read-only public RSS for four explicit accounts; never fetch/publish on X."""
import re,time
from html.parser import HTMLParser
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from .normalizer import date_value

ACCOUNTS={'ismailsaymaz':'İsmail Saymaz','haskologlu':'İbrahim Haskoloğlu',
          'abakingurlek':'Akın Gürlek','rterdogan':'Recep Tayyip Erdoğan'}

def check_source(source):
    account=source.get('x_account')
    if account not in ACCOUNTS or source['stable_id']!='x-'+account or source['endpoint']!='https://nitter.cf/'+account+'/rss' or source['allowed_hosts']!=['nitter.cf']:
        raise ValueError('social_source_not_allowlisted')

class OwnText(HTMLParser):
    def __init__(self):
        super().__init__();self.quote=0;self.skip=0;self.paragraph=0;self.done=False;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag=='blockquote':self.quote+=1
        if tag in ('script','style'):self.skip+=1
        if tag=='p' and not self.quote and not self.done:self.paragraph+=1
        if tag=='br' and self.paragraph and not self.quote:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag=='blockquote':self.quote=max(0,self.quote-1)
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
        if tag=='p' and self.paragraph:
            self.paragraph-=1
            if not self.paragraph:self.done=True
    def handle_data(self,text):
        if self.paragraph and not self.quote and not self.skip:self.parts.append(text)

def parse_social_feed(data,source,now=None):
    check_source(source);now=time.time() if now is None else now
    if len(data)>1_000_000 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('social_xml_denied')
    root=ET.fromstring(data);channel=root.find('channel');account=source['x_account']
    if root.tag!='rss' or channel is None or '@'+account not in (channel.findtext('title') or '').casefold():raise ValueError('social_channel_mismatch')
    entries=channel.findall('item')
    if not entries:raise ValueError('social_empty_feed')
    result=[]
    for node in entries[:100]:
        link=urlsplit(node.findtext('link') or '');match=re.fullmatch(r'/([a-zA-Z0-9_]+)/status/(\d{15,22})/?',link.path)
        title=node.findtext('title') or ''
        if link.scheme!='https' or link.hostname not in ('nitter.cf','x.com','twitter.com') or not match or match[1].casefold()!=account or re.match(r'^(RT\s|R to\s|R @)',title,re.I):continue
        stamp,precision=date_value(node.findtext('pubDate'))
        if stamp is None or precision!='second' or stamp>now+60:raise ValueError('social_invalid_timestamp')
        parser=OwnText();parser.feed(node.findtext('description') or '')
        text='\n'.join(' '.join(line.split()) for line in ''.join(parser.parts).splitlines()).strip()
        if not text or len(text)>30_000:raise ValueError('social_own_text_missing')
        post_id=match[2]
        result.append({'source_id':source['stable_id'],'provider_id':post_id,'url':f'https://x.com/{account}/status/{post_id}',
                       'title':text[:160],'summary':text,'full_post':text,'source_type':'social_x','x_account':account,
                       'published_at':stamp,'time_precision':precision,'first_seen_at':now})
    if not result:raise ValueError('social_no_owned_posts')
    return sorted(result,key=lambda item:int(item['provider_id']))
