"""Owner-bound full article export. No model requests or public article storage."""
import base64,gzip,hashlib,json,time
from pathlib import Path
from .db import encode,uid
from .normalizer import digest
from .editorial_prompt import clipboard_prompt

COPY_PAGE='https://fatihdisci.github.io/heranborsahaber/gpt/'
MAX_BUTTON_URL=18000


def export_button(nonce):
    return {'text':'📋 GPT’ye aktar','callback_data':'gpt:'+nonce}


def copy_url(prompt, title):
    blob=encode({'v':1,'prompt':prompt,'title':title,'chars':len(prompt),
                 'sha256':hashlib.sha256(prompt.encode()).hexdigest()}).encode()
    return COPY_PAGE+'#v1.'+base64.urlsafe_b64encode(gzip.compress(blob,mtime=0)).decode().rstrip('=')


def gpt_callback(db,approval,update,sources):
    cb=update['callback_query'];data=cb.get('data','')
    if not data.startswith('gpt:'):return None
    message=cb.get('message',{})
    if not approval.authorized(message,cb.get('from',{})):raise PermissionError('unauthorized_private_chat')
    record=db.conn.execute('SELECT * FROM habnews_feed_callback WHERE nonce=?',(data[4:],)).fetchone()
    if not record or record['recipient']!=approval.chat_id or record['message_id']!=message.get('message_id'):return 'stale'
    with db.transaction() as c:
        key='gpt_click:'+str(update['update_id'])
        if c.execute('SELECT 1 FROM habnews_update WHERE id=?',(key,)).fetchone():return 'duplicate'
        c.execute('INSERT INTO habnews_update VALUES(?,?)',(key,time.time()))
        observation=c.execute('SELECT * FROM habnews_observation WHERE id=?',(record['observation_id'],)).fetchone()
        if not observation or observation['digest']!=record['digest']:return 'stale'
        if not db.enabled():return 'Akış durdurulmuş. Önce /haber_baslat kullan.'
        source=next((s for s in sources if s['stable_id']==observation['source_id']),None)
        if not source or not source['enabled']:return 'Bu kaynak şu anda kapalı.'
        if source.get('article_access')=='blocked_http_403':return 'Kaynağın tam metnine erişim engelli; özet tam haber olarak aktarılmadı.'
        item=json.loads(observation['metadata'])
        if item.get('published_at') is None or not time.time()-86400<=item['published_at']<=time.time()+60:return 'Bu haber güncel değil veya yayın tarihi belirsiz.'
        recent=c.execute("SELECT id,status,created FROM habnews_gpt_export WHERE observation_id=? AND status IN ('pending','ready') ORDER BY created DESC LIMIT 1",(observation['id'],)).fetchone()
        if recent and recent['status']=='pending' and time.time()-recent['created']>=600:
            c.execute("UPDATE habnews_gpt_export SET status='expired' WHERE id=?",(recent['id'],));recent=None
        if recent and (recent['status']=='pending' or time.time()-recent['created']<60):
            return 'GPT aktarımı hazırlanıyor.' if recent['status']=='pending' else 'Prompt ve tam haberin kopyalama düğmesi bu sohbette hazır.'
        rid=uid();now=time.time()
        c.execute('INSERT INTO habnews_gpt_export(id,observation_id,recipient,digest,status,created) VALUES(?,?,?,?,?,?)',(rid,observation['id'],approval.chat_id,record['digest'],'pending',now))
        db.enqueue('gpt_export','gpt:'+rid,{'request_id':rid,'observation_id':observation['id'],
                   'source_id':source['stable_id'],'digest':record['digest'],'recipient':approval.chat_id})
        db.audit('gpt_export_requested',rid,{'observation_id':observation['id'],'model_requested':False})
        return 'GPT aktarımı kaydedildi; tam metin ve görsel hazırlanıyor.'


def queue_part(db,recipient,method,payload):
    oid=uid();now=time.time()
    db.conn.execute('INSERT INTO habnews_outbox(id,recipient,part,method,payload,next_at,created) VALUES(?,?,?,?,?,?,?)',
                    (oid,recipient,0,method,encode(payload),now,now))
    return oid


def prompt_file(db, rid, recipient, prompt):
    root=db.path.parent/'media';root.mkdir(parents=True,exist_ok=True,mode=0o700)
    data=prompt.encode();sha=hashlib.sha256(data).hexdigest();file=root/('gpt-'+rid+'-'+sha+'.txt')
    file.write_bytes(data);file.chmod(0o600)
    return queue_part(db,recipient,'sendDocument',{'chat_id':recipient,'file_path':str(file),
                      'file_sha256':sha,'caption':'Prompt + tam haber metni'})


def delivery_fallback(db, row, attempt, reason):
    """A rejected long link must never cause a clipped or missing export."""
    record=db.conn.execute('SELECT id FROM habnews_gpt_export WHERE outbox_id=?',(row['id'],)).fetchone()
    if not record:return False
    payload=json.loads(row['payload']);markup=payload.pop('reply_markup',None)
    method=row['method']
    if markup:
        url=markup['inline_keyboard'][0][0]['url']
        if not url.startswith(COPY_PAGE+'#v1.'):return False
        encoded=url.split('#v1.',1)[1]
        data=json.loads(gzip.decompress(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4))))
        if hashlib.sha256(data['prompt'].encode()).hexdigest()!=data['sha256']:return False
    elif method!='sendPhoto':return False
    if method=='sendPhoto' and (not markup or reason=='local_integrity'):
        method='sendMessage';payload={'chat_id':row['recipient'],'text':'Prompt ve tam haberin aktarımı hazır.','link_preview_options':{'is_disabled':True}}
        if markup:payload['reply_markup']=markup
    with db.transaction() as c:
        if markup and 'reply_markup' not in payload:prompt_file(db,record['id'],row['recipient'],data['prompt'])
        c.execute("UPDATE habnews_outbox SET method=?,payload=?,status='pending',next_at=?,lease=NULL WHERE id=?",(method,encode(payload),time.time(),row['id']))
        c.execute("UPDATE habnews_attempt SET status='media_rejected' WHERE id=?",(attempt,))
        db.audit('gpt_export_delivery_fallback',record['id'],{'reason':reason,'method':method})
    return True


def process_gpt_export(db,approval,sources):
    db.require_enabled();row=db.claim('gpt_export')
    if not row:return
    request=json.loads(row['payload']);rid=request['request_id']
    try:
        observation=db.conn.execute('SELECT * FROM habnews_observation WHERE id=?',(request['observation_id'],)).fetchone()
        record=db.conn.execute('SELECT * FROM habnews_gpt_export WHERE id=?',(rid,)).fetchone()
        if not record or record['status']!='pending':db.finish(row,'stale');return
        if (not observation or observation['digest']!=request['digest'] or record['digest']!=request['digest']
            or record['observation_id']!=observation['id'] or observation['source_id']!=request['source_id']
            or request['recipient']!=approval.chat_id or record['recipient']!=approval.chat_id):raise ValueError('export_binding')
        if time.time()-record['created']>600:raise ValueError('export_expired')
        source=next(s for s in sources if s['stable_id']==request['source_id'])
        item=json.loads(observation['metadata'])
        from .source_content import read_document,document_photo,document_text
        document=read_document(item,source,db.require_enabled)
        # The same selected heading/body sent to the model, without summary or clipping.
        source_type='social_x' if source.get('method')=='nitter_rss' else 'article'
        prompt=clipboard_prompt(document,source,source_type)
        url=copy_url(prompt,document['title'])
        media=None
        try:media=document_photo(document,source,db.path.parent/'media',db.require_enabled)
        except Exception as exc:
            if not db.enabled():raise RuntimeError('paused') from None
            db.audit('gpt_export_photo_unavailable',rid,{'type':type(exc).__name__})
        if media:
            from .article_media import private_preview
            from .images import reusable
            p=media['provenance']
            if not (private_preview(p) and p['landing_page_url']==document['source_url'] and p['article_digest']==digest(document_text(document,source)) or reusable(p)):raise ValueError('export_media_binding')
        markup={'inline_keyboard':[[{'text':'📋 Prompt + haberi kopyala','url':url}]]} if len(url)<=MAX_BUTTON_URL else None
        caption='GPT’ye aktarım hazır. Prompt ve tam haber metnini kopyalayıp GPT’ye yapıştır.' if markup else 'Prompt ve tam haber metni, kesilmeden TXT dosyasında.'
        if media and media['provenance'].get('archive_or_current')=='archive':caption+='\nArşiv fotoğrafı — '+media['provenance']['attribution_text']
        payload={'chat_id':approval.chat_id,'caption':caption,'show_caption_above_media':True,
                 'file_path':media['path'],'file_sha256':media['provenance']['sha256']} if media else {'chat_id':approval.chat_id,'text':caption,'link_preview_options':{'is_disabled':True}}
        if markup:payload['reply_markup']=markup
        db.require_enabled()
        with db.transaction() as c:
            if media:
                p=media['provenance']
                c.execute('INSERT OR IGNORE INTO habnews_image_candidate(id,event_id,version,payload,rights,created,path) VALUES(?,?,?,?,?,?,?)',
                          (digest('gpt:'+rid+':'+p['sha256']),'gpt:'+rid,1,encode(p),p['rights_status'],time.time(),media['path']))
            oid=queue_part(db,approval.chat_id,'sendPhoto' if media else 'sendMessage',payload)
            if not markup:
                prompt_file(db,rid,approval.chat_id,prompt)
            c.execute("UPDATE habnews_gpt_export SET status='ready',outbox_id=?,chars=?,article_digest=?,expires=? WHERE id=?",(oid,len(prompt),digest(document_text(document,source)),time.time()+86400,rid))
            db.finish(row)
            db.audit('gpt_export_ready',rid,{'article_chars':len(document['body']),'prompt_chars':len(prompt),
                     'source_url':document['source_url'],'photo':bool(media),'delivery':'copy_page' if markup else 'full_text_file','model_requested':False})
    except Exception as exc:
        if not db.enabled():db.finish(row,'pending',5);return
        db.audit('gpt_export_failure',rid,{'type':type(exc).__name__})
        if row['attempts']<2:
            db.finish(row,'pending',10);return
        with db.transaction() as c:
            c.execute("UPDATE habnews_gpt_export SET status='failed' WHERE id=?",(rid,))
            queue_part(db,approval.chat_id,'sendMessage',{'chat_id':approval.chat_id,'text':'Haberin tam metni alınamadı. Aynı karttan GPT’ye aktar düğmesine yeniden basabilirsin.','link_preview_options':{'is_disabled':True}})
            db.finish(row,'needs_review')
