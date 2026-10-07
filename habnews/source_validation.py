import json,time
from pathlib import Path
from datetime import datetime,timezone
from .config import sources
from .network import Fetcher
from .normalizer import parse_feed

def validate_sources(destination):
    results=[]
    for s in sources():
        if s['method'] not in ('rss','nitter_rss'):
            results.append({'id':s['stable_id'],'status':'unverified','reason':'Publication endpoint, ownership, parser and terms discovery pending','enabled':False});continue
        row={'id':s['stable_id'],'endpoint':s['endpoint'],'tested_at':datetime.now(timezone.utc).isoformat(),'enabled':False,'parser_version':s['parser_version'],'terms':'unverified'}
        try:
            data,headers,url,status=Fetcher(s['allowed_hosts'],timeout=12).get(s['endpoint'])
            row.update(http_status=status,mime=headers.get('content-type'),final_url=url,bytes=len(data))
            if s['method']=='nitter_rss':
                from .social import parse_social_feed
                items=parse_social_feed(data,s)
            else:items=parse_feed(data,s['stable_id'])
            row.update(entries=len(items),status='reachable' if items else 'parser_needs_review',sample_time_precision=items[0]['time_precision'] if items else None)
        except Exception as exc:
            row.update(status='blocked' if getattr(exc,'status',None) in (401,403) else 'unverified',reason=type(exc).__name__,http_status=getattr(exc,'status',None))
        results.append(row)
    Path(destination).write_text(json.dumps(results,ensure_ascii=False,indent=2))
    return results
