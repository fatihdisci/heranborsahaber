from pathlib import Path
import yaml
from .network import validate,host_ok

ROOT=Path(__file__).resolve().parent.parent

def sources(path=None):
    doc=yaml.safe_load(Path(path or ROOT/'sources.yaml').read_text())
    rows=doc['sources'];seen=set()
    for s in rows:
        if s['stable_id'] in seen:raise ValueError('duplicate_source_id')
        seen.add(s['stable_id'])
        if not all(host_ok(h,s['allowed_hosts']) for h in s['allowed_hosts']):raise ValueError('prohibited_source_host')
        if s['enabled'] and (s['method'] not in ('rss','tcmb_home','nitter_rss') or not s['parser_version'] or not s['verified_at'] or not s['terms_approved'] or not s['validation_report'] or s['health'] not in ('ok','validated')):raise ValueError('enabled_source_unverified')
        if s.get('delivery_mode','verified_drafts') not in ('verified_drafts','live_feed'):raise ValueError('delivery_mode')
        if s['method']=='nitter_rss':
            from .social import check_source
            check_source(s)
        if s.get('article_access','verified') not in ('verified','blocked_http_403'):raise ValueError('article_access_mode')
        if s['polling_interval']<60:raise ValueError('minimum_source_interval')
    if sum(bool(s['enabled']) for s in rows)>20:raise ValueError('enabled_source_limit')
    return rows
