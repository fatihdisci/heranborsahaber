"""Immediate private source cards; model work begins only on a bound user click."""
import json,re,secrets,time
from html.parser import HTMLParser
from .db import uid,encode
from .normalizer import classify,fresh,digest

class Plain(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
        if tag in ('p','br','div'):self.parts.append(' ')
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,text):
        if not self.skip:self.parts.append(text)

def plain(text):
    parser=Plain();parser.feed(text);return ' '.join(''.join(parser.parts).split())

def process_live_feed(db,approval,sources):
    db.require_enabled();row=db.claim('live_feed')
    if not row:return
    try:
        payload=json.loads(row['payload']);oid=payload['observation_id']
        observation=db.conn.execute('SELECT * FROM habnews_observation WHERE id=?',(oid,)).fetchone()
        item=json.loads(observation['metadata']);source=next(s for s in sources if s['stable_id']==observation['source_id'])
        if not source['enabled'] or not fresh(item)[0]:db.finish(row,'expired');return
        if classify(item)[0] not in ('P0','P1'):db.finish(row,'filtered');return
        title=plain(item['title']);summary=plain(item.get('summary',''))
        if summary==title:summary=''
        text='📰 '+source['owner']+'\n\n'+title[:450]+('\n\n'+summary[:2200] if summary else '')
        if len(summary)>2200:text+='…'
        if source['method']=='nitter_rss':text+='\n\nX paylaşımı — kaynak hesabın aktarımı; iddia ayrıca teyit edilmedi.'
        nonce=secrets.token_urlsafe(16);outbox_id=uid()
        buttons={'inline_keyboard':[[{'text':'🔗 Paylaşımı aç' if source['method']=='nitter_rss' else '🔗 Haberi aç','url':item['url']}],[{'text':'✨ Tweet oluştur','callback_data':nonce}]]}
        with db.transaction() as c:
            c.execute('INSERT INTO habnews_outbox(id,recipient,part,method,payload,next_at,created) VALUES(?,?,?,?,?,?,?)',
                      (outbox_id,approval.chat_id,0,'sendMessage',encode({'chat_id':approval.chat_id,'text':text,'reply_markup':buttons}),time.time(),time.time()))
            c.execute('INSERT INTO habnews_feed_callback(nonce,observation_id,recipient,digest,outbox_id) VALUES(?,?,?,?,?)',(nonce,oid,approval.chat_id,observation['digest'],outbox_id))
            c.execute("UPDATE habnews_observation SET stage='feed_queued' WHERE id=?",(oid,))
            db.finish(row);db.audit('feed_card_created',oid,{'source':source['stable_id'],'automatic_llm':False})
    except Exception as exc:
        db.audit('feed_card_failure',row['id'],{'type':type(exc).__name__});db.finish(row,'needs_review')

def feed_callback(db,approval,update,sources):
    cb=update['callback_query'];message=cb.get('message',{})
    record=db.conn.execute('SELECT * FROM habnews_feed_callback WHERE nonce=?',(cb.get('data',''),)).fetchone()
    if not record:return None
    if not approval.authorized(message,cb.get('from',{})):raise PermissionError('unauthorized_private_chat')
    with db.transaction() as c:
        key='feed_click:'+str(update['update_id'])
        if c.execute('SELECT 1 FROM habnews_update WHERE id=?',(key,)).fetchone():return 'duplicate'
        c.execute('INSERT INTO habnews_update VALUES(?,?)',(key,time.time()))
        if record['recipient']!=approval.chat_id or record['message_id']!=message.get('message_id'):return 'stale'
        observation=c.execute('SELECT * FROM habnews_observation WHERE id=?',(record['observation_id'],)).fetchone()
        if not observation or observation['digest']!=record['digest']:return 'stale'
        linked=c.execute('SELECT e.* FROM habnews_event e JOIN habnews_event_observation o ON e.id=o.event_id WHERE o.observation_id=?',(observation['id'],)).fetchone()
        if record['used'] and linked:
            active=c.execute("SELECT 1 FROM habnews_queue WHERE kind IN ('research','llm') AND status IN ('pending','leased') AND json_extract(payload,'$.event_id')=? AND json_extract(payload,'$.event_version')=? LIMIT 1",(linked['id'],linked['version'])).fetchone()
            if active:return 'Tweet isteğin zaten hazırlanıyor. Tamamlanınca taslak bu sohbete gelecek.'
            draft=c.execute('SELECT id,body,status,metadata FROM habnews_draft WHERE event_id=? AND event_version=? ORDER BY version DESC LIMIT 1',(linked['id'],linked['version'])).fetchone()
            if draft and draft['status'] in ('pending','approved'):
                metadata=json.loads(draft['metadata'])
                if metadata.get('image'):
                    delivered=c.execute("SELECT method,status FROM habnews_outbox WHERE draft_id=? ORDER BY part DESC LIMIT 1",(draft['id'],)).fetchone()
                    if delivered and delivered['method'] in ('sendPhoto','editMessageMedia'):
                        return 'Taslak fotoğrafıyla birlikte bu sohbette hazır.' if delivered['status']=='sent' else 'Taslak hazır; fotoğraflı mesajın gönderimi bekleniyor.'
                    return 'Taslak bu sohbette hazır.'
                if metadata.get('delivery_contract')=='article-photo-v1':return 'Hazırlanan taslak:\n\n'+draft['body']
                # A legacy link-preview draft must pass the new article/photo
                # pipeline on a new owner click instead of repeating cached text.
        item=json.loads(observation['metadata']);source=next(s for s in sources if s['stable_id']==observation['source_id'])
        if not db.enabled():return 'Akış durdurulmuş. Önce /haber_baslat kullan.'
        if not source['enabled']:return 'Bu kaynak şu anda kapalı.'
        # Manual requests may refer to today's earlier news, but never restart expired breaking delivery silently.
        if item.get('published_at') is None or item['published_at']<time.time()-86400:return 'Haber 24 saatten eski veya yayın tarihi belirsiz; güncel tweet oluşturulmadı.'
        if source.get('article_access')=='blocked_http_403':return 'Kaynağın haber metnine erişim engelli (403). RSS özeti geldi; tam metin okunmadan tweet hazırlanmadı.'
        if db.state('llm_state')!='ready':return 'Tweet motoru hazır değil: '+db.state('llm_state','bilinmiyor')+'. Haber akışı devam ediyor.'
        item['manual_requested_at']=time.time()
        now=time.time();state,reason=classify(item)
        if state not in ('P0','P1'):return 'Bu haber güncel Türkiye odağı filtresini geçmedi; taslak hazırlanmadı.'
        if linked:
            eid=linked['id'];version=linked['version']+1
            c.execute("UPDATE habnews_event SET version=?,status='verification_pending',priority=?,updated=? WHERE id=?",(version,state,now,eid))
            c.execute("UPDATE habnews_draft SET status='stale' WHERE event_id=?",(eid,))
            c.execute("UPDATE habnews_outbox SET status='stale' WHERE draft_id IN (SELECT id FROM habnews_draft WHERE event_id=?) AND status='pending'",(eid,))
        else:
            eid=uid();version=1
            c.execute('INSERT INTO habnews_event VALUES(?,?,?,?,?,?,?)',(eid,'manual:'+observation['id'],version,'verification_pending',state,now,now))
            c.execute('INSERT INTO habnews_event_observation VALUES(?,?)',(eid,observation['id']))
        item['source_id']=source['stable_id']
        c.execute('INSERT INTO habnews_event_version VALUES(?,?,?,?,?)',(eid,version,digest(encode(item)),encode(item),now))
        db.enqueue('research','manual:'+observation['id']+':'+str(version),{'event_id':eid,'event_version':version,'observation_id':observation['id'],'item':item,'source_id':source['stable_id'],'manual':True})
        c.execute('UPDATE habnews_feed_callback SET used=1 WHERE observation_id=?',(observation['id'],))
        db.audit('manual_tweet_requested',observation['id'],{'source':source['stable_id'],'user_id':approval.user_id})
        return 'Tweet isteği kaydedildi. Kaynak metni okunup sana onaylanabilir taslak hazırlanıyor; otomatik paylaşım yapılmaz.'

def enqueue_recent(db,sources,now=None):
    """One migration: recover recently missed eligible cards, excluding historical baselines."""
    now=time.time() if now is None else now;available={s['stable_id']:s for s in sources if s['enabled'] and s.get('delivery_mode')=='live_feed'};count=0
    with db.transaction() as c:
        for row in c.execute("SELECT * FROM habnews_observation WHERE first_seen>? AND stage NOT IN ('baseline','tombstone','feed_queued','feed_pending')",(now-1800,)).fetchall():
            if row['source_id'] not in available:continue
            item=json.loads(row['metadata'])
            if classify(item)[0] not in ('P0','P1') or not fresh(item,now)[0]:continue
            db.enqueue('live_feed','feed:'+row['id'],{'observation_id':row['id']});c.execute("UPDATE habnews_observation SET stage='feed_pending' WHERE id=?",(row['id'],));count+=1
        db.audit('live_feed_migration','habnews',{'eligible_recent_cards':count})
    return count

def notify_manual_failures(db,approval):
    for row in db.conn.execute("SELECT id,payload,status FROM habnews_queue WHERE kind IN ('research','llm') AND status IN ('needs_review','dead_letter','uncertain','expired','paused_result')").fetchall():
        payload=json.loads(row['payload']);eid=payload.get('event_id')
        if not eid or db.state('manual_failure_notice:'+row['id']):continue
        event=db.conn.execute('SELECT payload,version FROM habnews_event_version WHERE event_id=? ORDER BY version DESC LIMIT 1',(eid,)).fetchone()
        if not event or payload.get('event_version')!=event['version'] or not json.loads(event[0]).get('manual_requested_at'):continue
        with db.transaction():
            approval._out(None,0,'Bu haberin taslağı hazırlanamadı. Aynı karttan yeniden deneyebilirsin.')
            db.set_state('manual_failure_notice:'+row['id'],'true')
