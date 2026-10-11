"""Topic tags are selected only from validated headline/facts, never publisher names."""
import re

TOPICS=[
 ('fon',r'\bfon(?:u|un|lar|ların|ları|lardan|larda|larına|larının|larında|larından|larındaki|lardaki|daki|dan|a|da|una|unun|unda|undan)?\b|yatırım fon'),
 ('borsa',r'borsa|\bbist\b'),('SPK',r'\bspk\b|sermaye piyasası kurulu'),
 ('TCMB',r'\btcmb\b|merkez bankası'),('faiz',r'\bfaiz\w*'),('mevduat',r'\bmevduat\w*'),
 ('enflasyon',r'enflasyon|tüfe|üfe'),('altın',r'\baltın(?:ın|a|ı)?\b'),('petrol',r'petrol|brent|motorin'),
 ('döviz',r'\bdöviz\w*|\bparite\w*|\b(?:dolar|euro|avro)\s*(?:/\s*(?:tl|try)|kuru|yüksel|düş|gerile)'),('vergi',r'vergi'),('halkaarz',r'halka arz'),
 ('Fed',r'\bfed\b'),('ECB',r'\becb\b'),('ihracat',r'ihracat'),
 ('istihdam',r'istihdam|işsizlik'),('kripto',r'bitcoin|kripto|ethereum'),
 ('şirket',r'şirket|hisse|temettü'),('ekonomi',r'ekonomi|finans|hazine|sanayi|yatırım|mevduat'),
]
SENSITIVE=re.compile(r'\bölüm|öldü|öldür|ölü bulundu|intihar|hayatını kayb|can kayb|vefat|katliam',re.I)
URGENT=re.compile(r'tasfiye|fon krizi|fonlardan? (?:ciddi )?çıkış|faiz kararı|işlem durdur|iflas|deprem',re.I)

def decorate(text,subject):
    tags=[]
    for tag,pattern in TOPICS:
        if re.search(pattern,subject,re.I) and tag not in tags:tags.append(tag)
    for tag in (['ekonomi','finans'] if tags else ['gündem','haber']):
        if len(tags)>=2:break
        if tag not in tags:tags.append(tag)
    # Optional emoji: avoid treating every news item as an emergency or decorating death reports.
    emoji='' if SENSITIVE.search(subject) else '🚨 ' if URGENT.search(subject) else '📢 '
    return emoji+text+'\n\n'+' '.join('#'+tag for tag in tags[:3])
