import json, random, time
from .db import uid, encode
from .normalizer import digest, norm, parse_feed, fresh, classify, event_key, material_signature, extract_article
from .network import Fetcher, HTTPFailure

class Collector:
    def __init__(self,db,sources): self.db=db; self.sources=sources
    def observe(self,source,items):
        now=time.time(); sid=source['stable_id']
        with self.db.transaction() as c:
            c.execute('INSERT OR IGNORE INTO habnews_source(id) VALUES(?)',(sid,))
            baseline=c.execute('SELECT baseline FROM habnews_source WHERE id=?',(sid,)).fetchone()[0]
            for item in items:
                item['first_seen_at']=now; d=digest(norm(item['title']+' '+item.get('summary','')))
                old=c.execute('SELECT id FROM habnews_observation WHERE source_id=? AND provider_id=? AND digest=?',(sid,item['provider_id'],d)).fetchone()
                if old: continue
                oid=uid(); state,reason=classify(item); valid,fresh_reason=fresh(item,now)
                stage='baseline' if not baseline else state if state not in ('P0','P1') else 'research' if valid else fresh_reason
                if stage=='research' and source.get('delivery_mode')=='live_feed':stage='feed_pending'
                elif stage=='research' and source.get('article_access')=='blocked_http_403':stage='article_access_blocked'
                c.execute('INSERT INTO habnews_observation VALUES(?,?,?,?,?,?,?,?)',(oid,sid,item['provider_id'],item['url'],d,encode(item),now,stage))
                self.db.audit('observation',oid,{'stage':stage,'reason':reason,'freshness':fresh_reason})
                if stage=='feed_pending':
                    self.db.enqueue('live_feed','feed:'+oid,{'observation_id':oid});continue
                if stage!='research': continue
                key=event_key(item); signature=material_signature(item)
                event=c.execute('SELECT * FROM habnews_event WHERE identity=?',(key,)).fetchone()
                if event:
                    eid=event['id']; v=event['version']
                    current=c.execute('SELECT digest FROM habnews_event_version WHERE event_id=? AND version=?',(eid,v)).fetchone()[0]
                    if current!=signature:
                        v+=1
                        c.execute("UPDATE habnews_event SET version=?,status='verification_pending',updated=? WHERE id=?",(v,now,eid))
                        c.execute("UPDATE habnews_draft SET status='stale' WHERE event_id=?",(eid,))
                        c.execute("UPDATE habnews_outbox SET status='stale' WHERE draft_id IN (SELECT id FROM habnews_draft WHERE event_id=?) AND status='pending'",(eid,))
                        item['change_note']='GÜNCELLEME/DÜZELTME: kaynakta yeni sayı, karar veya aşama.'
                        c.execute('INSERT INTO habnews_event_version VALUES(?,?,?,?,?)',(eid,v,signature,encode(item),now))
                    elif event['status']=='rejected':
                        c.execute('INSERT INTO habnews_event_observation VALUES(?,?)',(eid,oid)); continue
                else:
                    eid=uid();v=1
                    c.execute('INSERT INTO habnews_event VALUES(?,?,?,?,?,?,?)',(eid,key,v,'verification_pending',state,now,now))
                    c.execute('INSERT INTO habnews_event_version VALUES(?,?,?,?,?)',(eid,v,signature,encode(item),now))
                c.execute('INSERT INTO habnews_event_observation VALUES(?,?)',(eid,oid))
                self.db.enqueue('research',oid,{'event_id':eid,'event_version':v,'observation_id':oid,'item':item,'source_id':sid})
            c.execute('UPDATE habnews_source SET baseline=1,last_success=?,failures=0,health=? WHERE id=?',(now,'ok',sid))
    def poll(self):
        self.db.require_enabled()
        for source in self.sources:
            if not source['enabled']: continue
            self.db.require_enabled(); sid=source['stable_id']; now=time.time()
            self.db.conn.execute('INSERT OR IGNORE INTO habnews_source(id) VALUES(?)',(sid,))
            row=self.db.conn.execute('SELECT * FROM habnews_source WHERE id=?',(sid,)).fetchone()
            if row['next_poll']>now or row['health']=='blocked': continue
            headers={}
            if row['etag']: headers['If-None-Match']=row['etag']
            if row['modified']: headers['If-Modified-Since']=row['modified']
            try:
                data,meta,url,status=Fetcher(source['allowed_hosts'],self.db.require_enabled).get(source['endpoint'],headers)
                if status==200:
                    if source['method']=='tcmb_home':
                        if 'html' not in meta.get('content-type',''):raise ValueError('listing_mime')
                        from .official import parse_tcmb_home
                        items=parse_tcmb_home(data,sid)
                    elif source['method']=='nitter_rss':
                        if not any(t in meta.get('content-type','') for t in ('xml','rss')):raise ValueError('feed_mime')
                        from .social import parse_social_feed
                        items=parse_social_feed(data,source)
                    else:
                        if not any(t in meta.get('content-type','') for t in ('xml','rss','atom')): raise ValueError('feed_mime')
                        items=parse_feed(data,sid)
                    self.observe(source,items)
                self.db.conn.execute('UPDATE habnews_source SET last_poll=?,last_success=?,next_poll=?,etag=?,modified=?,failures=0,health=? WHERE id=?',(now,now,now+source['polling_interval'],meta.get('etag',row['etag']),meta.get('last-modified',row['modified']),'ok',sid))
                self.db.recover('source:'+sid)
            except Exception as exc:
                if not self.db.enabled(): break
                failures=row['failures']+1
                status=getattr(exc,'status',None); health='blocked' if status in (401,403) else 'degraded'
                wait=max(getattr(exc,'retry',0),min(3600,source['polling_interval']*2**min(failures,5))+random.random()*5)
                self.db.conn.execute('UPDATE habnews_source SET failures=?,health=?,next_poll=?,last_poll=? WHERE id=?',(failures,health,now+wait,now,sid))
                if failures>=3: self.db.incident('source:'+sid,type(exc).__name__)
    def research_one(self):
        self.db.require_enabled(); row=self.db.claim('research')
        if not row: return
        job=json.loads(row['payload']); item=job['item']; source=next(s for s in self.sources if s['stable_id']==job['source_id'])
        if source.get('article_access')=='blocked_http_403':self.db.finish(row,'article_access_blocked');return
        valid,reason=fresh(item)
        if not valid: self.db.finish(row,reason); return
        try:
            if source.get('method')=='nitter_rss':
                from .social import check_source
                check_source(source)
                if item.get('x_account')!=source['x_account'] or item.get('source_type')!='social_x':raise ValueError('social_job_mismatch')
                # Entire owned post came from the validated RSS; never request X or quote author's content.
                text=item['full_post'];url=item['url'];document={'title':item['title'],'preview_url':item['url']}
            else:
                data,meta,url,_=Fetcher(source['allowed_hosts'],self.db.require_enabled).get(item['url'])
                from .article import extract_document
                document=extract_document(data,meta.get('content-type',''),url,expected_title=item['title'],requested_url=item['url'])
                text=(document['title']+'\n\n' if document['title'] else '')+document['body']
            media=None
            if source.get('method')!='nitter_rss' and (job.get('manual') or item.get('manual_requested_at')):
                try:
                    from .article_media import article_photo
                    from .images import matched_official_archive
                    media=article_photo(document,source,self.db.path.parent/'media',self.db.require_enabled)
                    if not media:media=matched_official_archive(document['title'],self.db.path.parent/'media',self.db.require_enabled,article_body=document['body'])
                    if media:
                        provenance=media['provenance'];mid=digest(job['event_id']+':'+str(job['event_version'])+':'+provenance['sha256'])
                        self.db.conn.execute('INSERT OR IGNORE INTO habnews_image_candidate(id,event_id,version,payload,rights,created,path) VALUES(?,?,?,?,?,?,?)',
                            (mid,job['event_id'],job['event_version'],encode(provenance),provenance['rights_status'],time.time(),media['path']))
                except Exception as exc:
                    self.db.audit('photo_unavailable',job['event_id'],{'type':type(exc).__name__})
            # A short passage is retained; the full transient main text is passed only in the job.
            eid=job['event_id']; evidence_id=digest(eid+'|'+str(job['event_version'])+'|'+url+'|'+digest(text))
            from .evidence import source_family,evidence_excerpt
            existing=self.db.conn.execute('SELECT family,passage FROM habnews_evidence WHERE event_id=? AND event_version=?',(eid,job['event_version'])).fetchall()
            family='social:'+source['x_account'] if source.get('method')=='nitter_rss' else source_family(source,text,existing)
            passage=text if source.get('method')=='nitter_rss' and len(text)<=1600 else evidence_excerpt(text)
            # Private operational spool, not an article archive. Excluded from backups.
            from .hermes import atomic_file
            root=self.db.path.parent/'maintext';root.mkdir(mode=0o700,exist_ok=True)
            title=document['title'] or item['title']
            binding={'text':text,'source_title':title,'source_url':url}
            atomic_file(root/(evidence_id+'.json'),binding|{'expires_at':time.time()+300,'digest':digest(text),'document_digest':digest(encode(binding)),'content_contract':'article-v2' if source.get('method')!='nitter_rss' else 'social-v1','preview_url':document.get('preview_url'),'media':media})
            self.db.audit('article_extracted',eid,{'url':url,'method':document.get('method','social_rss'),'chars':len(text),'digest':digest(text),'title':title[:180],'has_media':bool(media),'media_scope':media['provenance'].get('delivery_scope','verified_reusable') if media else None})
            with self.db.transaction() as c:
                c.execute('UPDATE habnews_evidence SET tombstone=1 WHERE event_id=? AND event_version=? AND url=? AND id<>?',(eid,job['event_version'],url,evidence_id))
                c.execute('INSERT OR IGNORE INTO habnews_evidence VALUES(?,?,?,?,?,?,?,?,?,?,0)',(evidence_id,eid,job['event_version'],source['stable_id'],family,int(source['priority']=='A'),url,passage,digest(text),time.time()))
                c.execute('UPDATE habnews_evidence SET tombstone=0,retrieved=? WHERE id=?',(time.time(),evidence_id))
                families=c.execute('SELECT count(DISTINCT family) FROM habnews_evidence WHERE event_id=? AND event_version=? AND tombstone=0',(eid,job['event_version'])).fetchone()[0]
                primary=c.execute('SELECT count(*) FROM habnews_evidence WHERE event_id=? AND event_version=? AND primary_source=1 AND tombstone=0',(eid,job['event_version'])).fetchone()[0]
                if job.get('manual') or item.get('manual_requested_at') or primary or families>=2:
                    self.db.enqueue('llm',job.get('llm_identity',f"{eid}:{job['event_version']}"),{'event_id':eid,'event_version':job['event_version'],'revision':job.get('revision'),'repair_attempt':job.get('repair_attempt',0),'repair_feedback':job.get('repair_feedback')})
                else: self.db.audit('verification_pending',eid,{'independent_families':families})
                self.db.finish(row)
        except Exception as exc:
            self.db.audit('research_failure',row['id'],{'type':type(exc).__name__})
            self.db.finish(row,'dead_letter' if row['attempts']>=3 else 'pending',min(300,30*2**row['attempts']))
