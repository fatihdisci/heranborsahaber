import json, secrets, time
from pathlib import Path
from .db import uid,encode
from .normalizer import digest,fresh
from .schema import validate_result,lock_metadata

BUTTONS={'approve':'Taslağı onayla','reject':'Reddet','revise':'Revize et','image':'Başka görsel','sources':'Kaynaklar'}
MEDIA_ROOT=Path('/data/media')

class Approval:
    def __init__(self,db,user_id,chat_id):
        if user_id<=0 or chat_id<=0: raise ValueError('numeric_private_recipient_required')
        self.db=db;self.user_id=user_id;self.chat_id=chat_id
    def create(self,job,result,run_metadata,image=None):
        self.db.require_enabled();lock_metadata(run_metadata)
        private_image=False
        if image:
            from .images import reusable
            from .article_media import private_preview
            import hashlib
            try:
                private_image=bool(job.get('quiet_delivery') and job.get('manual_attribution',{}).get('source_type')=='article' and private_preview(image.get('provenance',{})))
                if not (reusable(image.get('provenance',{})) or private_image):raise ValueError('media_not_verified')
                file=Path(image['path']).resolve()
                if file.parent!=MEDIA_ROOT or hashlib.sha256(file.read_bytes()).hexdigest()!=image['provenance']['sha256']:raise ValueError('media_path_or_digest')
            except (OSError,ValueError,KeyError,TypeError):
                if not job.get('quiet_delivery'):raise
                self.db.audit('draft_media_fallback',job['event_id'],{'reason':'local_media_validation'});image=None;private_image=False
        ev={r['id']:dict(r) for r in self.db.conn.execute('SELECT * FROM habnews_evidence WHERE event_id=? AND event_version=? AND tombstone=0',(job['event_id'],job['event_version']))}
        from .normalizer import digest as source_digest
        for record in job.get('evidence',[]):
            ref=record.get('id');full=record.get('full_text')
            if ref in ev and full is not None:
                if source_digest(full)!=ev[ref]['digest']:raise ValueError('full_text_digest_mismatch')
                ev[ref]['passage']=full
        if private_image and not any(e['url']==image['provenance']['landing_page_url'] and e['digest']==image['provenance']['article_digest'] for e in ev.values()):
            self.db.audit('draft_media_fallback',job['event_id'],{'reason':'article_media_evidence_mismatch'});image=None;private_image=False
        text=validate_result(result,job,ev)
        photo_note=''
        if image and job.get('quiet_delivery') and not private_image:
            provenance=image['provenance'];photo_note='\n\n'+provenance['attribution_text']
            if provenance['archive_or_current']=='archive':photo_note+=' — arşiv fotoğrafı'
            if len(text+photo_note)>1024:
                self.db.audit('draft_media_fallback',job['event_id'],{'reason':'caption_limit'});image=None
        event=self.db.conn.execute('SELECT * FROM habnews_event WHERE id=?',(job['event_id'],)).fetchone()
        payload=json.loads(self.db.conn.execute('SELECT payload FROM habnews_event_version WHERE event_id=? AND version=?',(event['id'],event['version'])).fetchone()[0])
        if job.get('manual_attribution') and (not payload.get('manual_requested_at') or job['manual_attribution'].get('requested_url',job['manual_attribution']['url'])!=payload['url']):raise ValueError('manual_request_not_bound_to_event')
        if event['version']!=job['event_version'] or not fresh(payload)[0]: raise ValueError('stale_event')
        if event['status']=='rejected': raise ValueError('rejected_event')
        with self.db.transaction() as c:
            if event['priority']!='P0' and not job.get('manual_attribution'):
                hour=c.execute('SELECT count(*) FROM habnews_draft WHERE created>?',(time.time()-3600,)).fetchone()[0]
                day=c.execute('SELECT count(*) FROM habnews_draft WHERE created>?',(time.time()-86400,)).fetchone()[0]
                pending=c.execute("SELECT count(*) FROM habnews_draft WHERE status='pending'").fetchone()[0]
                if hour>=6 or day>=30 or pending>100: raise ValueError('noise_backpressure_review_list')
            version=c.execute('SELECT coalesce(max(version),0)+1 FROM habnews_draft WHERE event_id=?',(event['id'],)).fetchone()[0]
            c.execute("UPDATE habnews_draft SET status='stale' WHERE event_id=? AND status IN ('pending','approved')",(event['id'],))
            did=uid(); iv=image['version'] if image else 0; h=digest(encode({'text':text,'image':image,'event_version':event['version'],'draft_version':version}))
            meta={'verification':result['verification_state'],'reason':result['relevance_reason'],'source_urls':list(dict.fromkeys(e['url'] for e in ev.values())),
                  'time_precision':payload['time_precision'],'published_at':payload['published_at'],'first_seen_at':payload['first_seen_at'],
                  'image':image,'run':run_metadata,'validated_result':result,'change_note':payload.get('change_note')}
            if job.get('manual_attribution'):meta['manual_attribution']=job['manual_attribution']
            if job.get('quiet_delivery'):meta['delivery_contract']='article-photo-v1'
            c.execute('INSERT INTO habnews_draft VALUES(?,?,?,?,?,?,?,?,?,?)',(did,event['id'],event['version'],version,iv,h,text,encode(meta),'pending',time.time()))
            for ref in {f['source_ref'] for f in result['facts']}:
                initial=c.execute('SELECT passage FROM habnews_evidence WHERE id=?',(ref,)).fetchone()[0]
                facts_text='\n'.join(f['text'] for f in result['facts'] if f['source_ref']==ref and f['text'] not in initial)
                relevant=initial+('\n'+facts_text if facts_text else '')
                if len(relevant)>3200:raise ValueError('evidence_retention_limit')
                c.execute('UPDATE habnews_evidence SET passage=? WHERE id=?',(relevant,ref))
            for fact in result['facts']: c.execute('INSERT INTO habnews_fact VALUES(?,?,?,?)',(uid(),event['id'],encode(fact),fact['source_ref']))
            if job.get('quiet_delivery'):
                preview=job.get('preview_url')
                if preview and preview not in meta['source_urls']:raise ValueError('preview_source_mismatch')
                if image:
                    markup={'inline_keyboard':[[{'text':'🔗 Kaynak','url':image['provenance']['landing_page_url']}]]} if private_image else None
                    self._out_media(did,0,'sendPhoto',image['path'],text+photo_note,markup)
                else:self._out(did,0,text,disable_preview=True)
                c.execute("UPDATE habnews_event SET status='pending' WHERE id=?",(event['id'],))
                self.db.audit('draft_created',did,{'event_version':event['version'],'draft_version':version,'hash':h,'quiet_delivery':True})
                return did
            keyboard=[]
            for action,label in BUTTONS.items():
                nonce=secrets.token_urlsafe(16)
                c.execute('INSERT INTO habnews_callback VALUES(?,?,?,?,?,?,0)',(nonce,did,action,self.chat_id,None,h))
                keyboard.append([{'text':label,'callback_data':nonce}])
            # v1 text-only safe path; unverified media candidates never uploaded.
            start=0
            if image:
                self._out_media(did,0,'sendPhoto',image['path'],'habnews '+event['id'][:8]);start=1
            self._out(did,start,text)
            from datetime import datetime
            from zoneinfo import ZoneInfo
            def display(stamp): return datetime.fromtimestamp(stamp,ZoneInfo('Europe/Istanbul')).strftime('%d.%m.%Y %H:%M') if stamp else 'belirtilmiyor'
            publication=display(payload['published_at']) if payload['time_precision']=='second' else 'Yayın saati belirtilmiyor; yeni görüldü.'
            card=f"habnews {event['id'][:8]} • {event['priority']} • {result['verification_state']}\nSürüm {event['version']}/{version}/{iv}\nYayın: {publication}\nİlk görülme: {display(payload['first_seen_at'])}\nNeden önemli? {result['relevance_reason']}\n"+'\n'.join(meta['source_urls'])+'\nKullanım hakkı uygun görsel bulunamadı — text_only.'
            if meta['change_note']: card+='\n'+meta['change_note']
            if result['verification_state']=='attributed_single_source':card+='\nKaynak aktarımıdır; haberdeki iddia bağımsız olarak teyit edilmedi.'
            for candidate in result['image_candidates'][:3]:
                from .network import host_ok
                from urllib.parse import urlsplit
                link=candidate.get('landing_page_url','')
                if urlsplit(link).scheme=='https' and host_ok(urlsplit(link).hostname,['commons.wikimedia.org']):
                    card+='\nGörsel adayı; hak/kişi kontrolü bekliyor, dosya verilmedi: '+link
            if image:
                from .images import image_note
                card=card.replace('Kullanım hakkı uygun görsel bulunamadı — text_only.',image_note(image['provenance']))
            self._out(did,start+1,card,{'inline_keyboard':keyboard})
            c.execute("UPDATE habnews_event SET status='pending' WHERE id=?",(event['id'],))
            self.db.audit('draft_created',did,{'event_version':event['version'],'draft_version':version,'hash':h})
            return did
    def _out_media(self,did,part,method,path,caption,markup=None):
        import hashlib
        payload={'chat_id':self.chat_id,'file_path':path,'file_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'caption':caption}
        if method=='sendPhoto':payload['show_caption_above_media']=True
        if markup:payload['reply_markup']=markup
        self.db.conn.execute('INSERT INTO habnews_outbox(id,draft_id,recipient,part,method,payload,next_at,created) VALUES(?,?,?,?,?,?,?,?)',(uid(),did,self.chat_id,part,method,encode(payload),time.time(),time.time()))
    def _out(self,did,part,text,markup=None,preview=None,disable_preview=False):
        if len(text)>4096: raise ValueError('telegram_text_limit')
        payload={'chat_id':self.chat_id,'text':text}
        if markup: payload['reply_markup']=markup
        if preview:payload['link_preview_options']={'url':preview,'prefer_large_media':True,'show_above_text':True}
        elif disable_preview:payload['link_preview_options']={'is_disabled':True}
        self.db.conn.execute('INSERT INTO habnews_outbox(id,draft_id,recipient,part,method,payload,next_at,created) VALUES(?,?,?,?,?,?,?,?)',(uid(),did,self.chat_id,part,'sendMessage',encode(payload),time.time(),time.time()))
    def authorized(self,message,actor):
        return (actor.get('id')==self.user_id and message.get('chat',{}).get('id')==self.chat_id
            and message.get('chat',{}).get('type')=='private' and not any(k in message for k in ('forward_origin','forward_from','forward_from_chat','is_automatic_forward')))
    def callback(self,update):
        cb=update['callback_query'];message=cb.get('message',{})
        if not self.authorized(message,cb.get('from',{})): raise PermissionError('unauthorized_private_chat')
        with self.db.transaction() as c:
            update_id='update:'+str(update['update_id']); callback_id='callback:'+cb['id']
            if c.execute('SELECT 1 FROM habnews_update WHERE id IN (?,?)',(update_id,callback_id)).fetchone(): return 'duplicate'
            for key in (update_id,callback_id): c.execute('INSERT INTO habnews_update VALUES(?,?)',(key,time.time()))
            record=c.execute('SELECT * FROM habnews_callback WHERE nonce=?',(cb.get('data',''),)).fetchone()
            if not record or record['used'] or record['recipient']!=self.chat_id or record['message_id']!=message.get('message_id'): return 'stale'
            draft=c.execute('SELECT * FROM habnews_draft WHERE id=?',(record['draft_id'],)).fetchone()
            event=c.execute('SELECT * FROM habnews_event WHERE id=?',(draft['event_id'],)).fetchone()
            if draft['hash']!=record['hash'] or draft['status']!='pending' or event['version']!=draft['event_version']: return 'stale'
            action=record['action']
            if action in ('approve','reject'):
                c.execute('UPDATE habnews_callback SET used=1 WHERE draft_id=?',(draft['id'],))
                status='approved' if action=='approve' else 'rejected'
                c.execute('UPDATE habnews_draft SET status=? WHERE id=?',(status,draft['id']))
                c.execute('UPDATE habnews_event SET status=? WHERE id=?',(status,event['id']))
                media=json.loads(draft['metadata']).get('image')
                from .images import reusable
                publishable=bool(media and reusable(media.get('provenance',{})))
                media_status='ready_to_share_with_media' if publishable else 'private_source_preview' if media else 'text_only'
                c.execute('INSERT INTO habnews_decision VALUES(?,?,?,?,?,?,?)',(uid(),draft['id'],draft['hash'],self.user_id,action,media_status,time.time()))
                if action=='approve' and publishable:
                    part=c.execute('SELECT max(part)+1 FROM habnews_outbox WHERE draft_id=?',(draft['id'],)).fetchone()[0]
                    self._out_media(draft['id'],part,'sendDocument',media['path'],'Orijinal görsel — atıf/lisans şartları geçerlidir.')
                    self._out(draft['id'],part+1,media['provenance']['attribution_text']+'\n'+media['provenance']['license_url'])
                if action=='approve' and json.loads(draft['metadata']).get('run',{}).get('fixture') and self.db.state('acceptance_test_draft')==draft['id']:
                    self.db.set_state('live_acceptance_verified','true')
                self.db.audit('decision',draft['id'],{'user_id':self.user_id,'action':action,'hash':draft['hash']})
                return 'Taslak onaylandı. Yayınlanmadı; paylaşım sende.\n\n'+draft['body'] if action=='approve' else 'Reddedildi.'
            if action=='sources': return '\n'.join(json.loads(draft['metadata'])['source_urls'])
            if action=='revise': return 'revision_prompt:'+draft['id']
            if action=='image':
                self.db.enqueue('image',event['id']+':'+uid(),{'event_id':event['id'],'draft_id':draft['id']})
                return 'Görsel inceleme isteği kaydedildi; yeni sürüm ayrıca onaylanmalıdır.'
    def reply(self,update):
        message=update['message']
        if not self.authorized(message,message.get('from',{})): raise PermissionError('unauthorized_private_chat')
        ref=message.get('reply_to_message',{}).get('message_id')
        with self.db.transaction() as c:
            key='update:'+str(update['update_id'])
            if c.execute('SELECT 1 FROM habnews_update WHERE id=?',(key,)).fetchone(): return 'duplicate'
            c.execute('INSERT INTO habnews_update VALUES(?,?)',(key,time.time()))
            link=c.execute('SELECT * FROM habnews_revision WHERE message_id=? AND recipient=?',(ref,self.chat_id)).fetchone()
            if not link: return 'Önce ilgili kartta Revize et seçeneğini kullan.'
            draft=c.execute('SELECT * FROM habnews_draft WHERE id=?',(link['draft_id'],)).fetchone()
            if not draft or draft['status']!='pending': return 'stale'
            # Private note is deliberately not written to audit logs.
            self.db.enqueue('revision',key,{'event_id':link['event_id'],'draft_id':link['draft_id'],'instruction':message.get('text','')[:2000]})
            c.execute("UPDATE habnews_draft SET status='stale' WHERE id=?",(link['draft_id'],))
            return 'Revizyon kuyruğa alındı; önceki sürümün onayı geçersiz.'
