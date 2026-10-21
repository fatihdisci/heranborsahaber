"""Read-only source discovery. A 200 response alone never approves a feed."""
import concurrent.futures, datetime as dt, email.utils, json, pathlib, re
import urllib.request, urllib.error, urllib.parse, xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
UA = 'SectorHaber-SourceCheck/1.0 (RSS validation; private editorial review)'

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/rss+xml,application/atom+xml,text/html;q=0.8'})
    with urllib.request.urlopen(req, timeout=18) as r:
        b = r.read(3_000_001)
        if len(b)>3_000_000: raise ValueError('response_too_large')
        return b, r.url, r.status, r.headers.get('Content-Type','')

def date(value):
    months={'Oca':'Jan','Şub':'Feb','Mar':'Mar','Nis':'Apr','May':'May','Haz':'Jun','Tem':'Jul','Ağu':'Aug','Eyl':'Sep','Eki':'Oct','Kas':'Nov','Ara':'Dec'}
    for tr,en in months.items(): value=value.replace(tr,en)
    for parse in [lambda v:email.utils.parsedate_to_datetime(v),lambda v:dt.datetime.fromisoformat(v.replace('Z','+00:00')),lambda v:dt.datetime.strptime(v,'%d %b %Y %H:%M:%S')]:
        try:
            d=parse(value)
            return d.replace(tzinfo=dt.timezone(dt.timedelta(hours=3))) if not d.tzinfo else d
        except (ValueError,TypeError): pass

def probe(s):
    row={**s,'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'enabled':False}
    try:
        b,u,status,mime=get(s['url']); row.update(http=status,final_url=u,mime=mime,bytes=len(b))
        root=ET.fromstring(b)
        if root.tag.split('}')[-1] not in ('rss','feed','RDF'): raise ValueError('not_rss_or_atom')
        items=[e for e in root.iter() if e.tag.split('}')[-1] in ('item','entry')]
        if not items: raise ValueError('empty_feed')
        dates=[];samples=[]
        for item in items:
            fields={e.tag.split('}')[-1]:e for e in item}
            title=fields.get('title'); links=[e for e in item if e.tag.split('}')[-1]=='link']
            link=next((e for e in links if e.get('rel','alternate')=='alternate'),None)
            url=(link.get('href') or (link.text or '')) if link is not None else ''
            if title is not None and url: samples.append({'title':''.join(title.itertext()).strip(),'url':urllib.parse.urljoin(u,url.strip())})
            for e in item:
                if e.tag.split('}')[-1] in ('pubDate','published','updated','date') and e.text:
                    d=date(e.text.strip())
                    if d: dates.append(d)
        newest=max(dates) if dates else None
        age=(dt.datetime.now(dt.timezone.utc)-newest).total_seconds()/3600 if newest else None
        row.update(entries=len(items),newest=newest.isoformat() if newest else None,age_hours=round(age,1) if age is not None else None,samples=samples[:3])
        row['status']='valid' if age is not None and -1<=age<=s.get('fresh_hours',72) else 'stale_or_undated'
        row['enabled']=row['status']=='valid' and s.get('review_mode') in ('private_facts','official_facts')
        (ROOT/'reports'/'feeds'/f"{s['id']}.xml").write_bytes(b)
    except urllib.error.HTTPError as e: row.update(status='http_error',http=e.code)
    except Exception as e: row.update(status='invalid',error=type(e).__name__,reason=str(e)[:140])
    return row

if __name__=='__main__':
    (ROOT/'reports'/'feeds').mkdir(parents=True,exist_ok=True)
    sources=json.loads((ROOT/'sources.candidates.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(probe,sources))
    (ROOT/'reports'/'source-check.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    for r in results: print(r['id'],r['status'],r.get('http'),r.get('entries'),r.get('newest'))
