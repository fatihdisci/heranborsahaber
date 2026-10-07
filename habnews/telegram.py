"""Only private Telegram review. This module has no X/publication capability."""
import contextlib, http.client, json, os, time
from pathlib import Path
from .db import encode,uid
from .normalizer import fresh

class TelegramError(RuntimeError):
    def __init__(self,code,retry=0):self.code=code;self.retry=retry;super().__init__(f'telegram_{code}')

class MediaError(ValueError):pass

class Telegram:
    METHODS={'getMe','getWebhookInfo','getUpdates','sendMessage','sendPhoto','sendDocument','editMessageCaption','editMessageMedia','editMessageReplyMarkup','answerCallbackQuery'}
    def __init__(self,token):
        if not token or ':' not in token: raise ValueError('telegram_auth_required')
        self._token=token; self.next_at=0
    def call(self,method,payload):
        if method not in self.METHODS: raise ValueError('telegram_method_denied')
        if (method.startswith('send') or method in ('editMessageCaption','editMessageMedia','editMessageReplyMarkup')) and payload.get('chat_id',0)<=0: raise ValueError('private_chat_only')
        if method=='editMessageReplyMarkup' and payload.get('message_id',0)<=0:raise ValueError('private_message_required')
        if method=='editMessageMedia':
            media=payload.get('media',{})
            if not payload.get('file_path') or payload.get('message_id',0)<=0 or media.get('type')!='photo' or media.get('media')!='attach://photo' or len(media.get('caption',''))>1024:raise ValueError('private_photo_edit_only')
        wait=self.next_at-time.monotonic()
        if wait>0: time.sleep(min(wait,60))
        proxy=os.environ.get('HABNEWS_TELEGRAM_PROXY')
        if proxy:
            if proxy!='telegram-egress:3128':raise ValueError('telegram_proxy_lock')
            conn=http.client.HTTPSConnection('telegram-egress',port=3128,timeout=40);conn.set_tunnel('api.telegram.org',443)
        else:conn=http.client.HTTPSConnection('api.telegram.org',timeout=40)
        try:
            if 'file_path' in payload:
                import hashlib
                try:
                    path=Path(payload['file_path']).resolve()
                    if path.parent!=Path('/data/media') or not path.is_file() or path.stat().st_size>10_000_000:raise MediaError('upload_path')
                    blob=path.read_bytes()
                    if not payload.get('file_sha256') or hashlib.sha256(blob).hexdigest()!=payload['file_sha256']:raise MediaError('upload_digest')
                except OSError:raise MediaError('upload_unavailable') from None
                if method not in ('sendPhoto','sendDocument','editMessageMedia'):raise ValueError('upload_method')
                boundary='habnews'+uid();chunks=[]
                for k,v in payload.items():
                    if k in ('file_path','file_sha256'):continue
                    value=json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,bool)) else str(v)
                    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{value}\r\n'.encode())
                field='document' if method=='sendDocument' else 'photo'
                content_type={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp','.txt':'text/plain; charset=utf-8'}.get(path.suffix.lower(),'application/octet-stream')
                filename='gpt-aktarim.txt' if path.suffix.lower()=='.txt' else 'image'+path.suffix
                chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'.encode()+blob+f'\r\n--{boundary}--\r\n'.encode())
                body=b''.join(chunks);headers={'Content-Type':'multipart/form-data; boundary='+boundary}
            else:body=encode(payload).encode();headers={'Content-Type':'application/json'}
            conn.request('POST','/bot'+self._token+'/'+method,body=body,headers=headers)
            resp=conn.getresponse(); raw=resp.read(2_000_001)
            if len(raw)>2_000_000: raise TelegramError(502)
            data=json.loads(raw)
            if not data.get('ok'):
                code=data.get('error_code',resp.status);retry=data.get('parameters',{}).get('retry_after',0)
                if code==429:self.next_at=time.monotonic()+retry
                raise TelegramError(code,retry)
            if method.startswith('send'):self.next_at=time.monotonic()+1.1
            return data['result']
        except MediaError:raise
        except (OSError,ValueError): raise TelegramError(0) from None
        finally:conn.close()
    def preflight(self,expected_bot_id):
        me=self.call('getMe',{})
        if me['id']!=expected_bot_id or not me.get('is_bot'): raise ValueError('operator_new_bot_identity_mismatch')
        webhook=self.call('getWebhookInfo',{})
        if webhook.get('url'): raise ValueError('webhook_present_do_not_modify')
        return {'bot_id':me['id'],'username':me.get('username'),'webhook':'absent'}

class Outbox:
    def __init__(self,db,transport): self.db=db;self.transport=transport
    def photo_fallback(self,row,attempt,reason):
        from .gpt_export import delivery_fallback
        if delivery_fallback(self.db,row,attempt,reason):return True
        if row['method']!='sendPhoto' or not row['draft_id']:return False
        draft=self.db.conn.execute('SELECT body,metadata FROM habnews_draft WHERE id=?',(row['draft_id'],)).fetchone()
        if not draft or not json.loads(draft['metadata']).get('manual_attribution'):return False
        with self.db.transaction() as c:
            c.execute("UPDATE habnews_outbox SET method='sendMessage',payload=?,status='pending',next_at=?,lease=NULL WHERE id=?",(encode({'chat_id':row['recipient'],'text':draft['body'],'link_preview_options':{'is_disabled':True}}),time.time(),row['id']))
            c.execute("UPDATE habnews_attempt SET status='media_rejected' WHERE id=?",(attempt,))
            self.db.audit('photo_delivery_fallback',row['id'],{'reason':reason})
        return True
    def send_one(self):
        self.db.require_enabled();now=time.time()
        if float(self.db.state('telegram_cooldown','0'))>now:return
        with self.db.transaction() as c:
            c.execute("UPDATE habnews_outbox SET status='uncertain',lease=NULL WHERE status='sending' AND lease_until<?",(now,))
            row=c.execute("SELECT o.* FROM habnews_outbox o WHERE o.status='pending' AND o.next_at<=? AND NOT EXISTS(SELECT 1 FROM habnews_outbox prev WHERE prev.draft_id=o.draft_id AND prev.part<o.part AND prev.status!='sent') ORDER BY o.created,o.part LIMIT 1",(now,)).fetchone()
            if not row:return
            feed=c.execute('SELECT observation_id FROM habnews_feed_callback WHERE outbox_id=?',(row['id'],)).fetchone()
            if feed:
                observed=c.execute('SELECT metadata FROM habnews_observation WHERE id=?',(feed[0],)).fetchone()
                if not observed or not fresh(json.loads(observed[0]))[0]:
                    c.execute("UPDATE habnews_outbox SET status='expired' WHERE id=?",(row['id'],));return
            if row['draft_id']:
                draft=c.execute('SELECT * FROM habnews_draft WHERE id=?',(row['draft_id'],)).fetchone()
                current=c.execute('SELECT version FROM habnews_event WHERE id=?',(draft['event_id'],)).fetchone()[0]
                item=json.loads(c.execute('SELECT payload FROM habnews_event_version WHERE event_id=? AND version=?',(draft['event_id'],current)).fetchone()[0])
                if current!=draft['event_version'] or draft['status']=='stale' or not fresh(item)[0]:
                    c.execute("UPDATE habnews_outbox SET status='expired' WHERE draft_id=? AND status='pending'",(draft['id'],));return
            lease=uid();attempt=uid()
            c.execute("UPDATE habnews_outbox SET status='sending',lease=?,lease_until=? WHERE id=?",(lease,now+60,row['id']))
            c.execute('INSERT INTO habnews_attempt VALUES(?,?,?,?,NULL)',(attempt,row['id'],'sending',now))
        try:
            self.db.require_enabled()
            result=self.transport.call(row['method'],json.loads(row['payload']))
            # If receipt persistence fails, sending lease expires to uncertain; never auto-resend.
            with self.db.transaction() as c:
                c.execute("UPDATE habnews_outbox SET status='sent',message_id=?,lease=NULL WHERE id=? AND lease=?",(result['message_id'],row['id'],lease))
                c.execute("UPDATE habnews_attempt SET status='accepted',message_id=? WHERE id=?",(result['message_id'],attempt))
                if 'reply_markup' in json.loads(row['payload']):c.execute('UPDATE habnews_callback SET message_id=? WHERE draft_id=?',(result['message_id'],row['draft_id']))
                c.execute('UPDATE habnews_feed_callback SET message_id=? WHERE outbox_id=?',(result['message_id'],row['id']))
                self.db.audit('telegram_accepted',row['id'],{'message_id':result['message_id']})
        except MediaError:
            if not self.photo_fallback(row,attempt,'local_integrity'):
                self.db.conn.execute("UPDATE habnews_outbox SET status='blocked',lease=NULL WHERE id=?",(row['id'],))
                self.db.incident('telegram_delivery','invalid_media')
        except TelegramError as exc:
            if exc.code==400 and self.photo_fallback(row,attempt,'telegram_rejected_photo'):return
            if exc.code==429:self.db.set_state('telegram_cooldown',time.time()+exc.retry)
            status='pending' if exc.code==429 else 'blocked' if exc.code in (400,401,403) else 'uncertain'
            self.db.conn.execute('UPDATE habnews_outbox SET status=?,next_at=?,lease=NULL WHERE id=?',(status,time.time()+max(1,exc.retry),row['id']))
            self.db.conn.execute('UPDATE habnews_attempt SET status=? WHERE id=?',(status,attempt))
            if status!='pending':self.db.incident('telegram_delivery',status)
        except RuntimeError as exc:
            if str(exc)=='paused':self.db.conn.execute("UPDATE habnews_outbox SET status='pending',lease=NULL WHERE id=?",(row['id'],))
            else:raise

@contextlib.contextmanager
def polling_owner(path):
    import fcntl
    f=Path(path).open('a');os.chmod(path,0o600)
    try:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);yield
    except BlockingIOError:raise RuntimeError('polling_owner_exists') from None
    finally:f.close()

class ApprovalService:
    def __init__(self,db,approval,transport,expected_bot_id):self.db=db;self.approval=approval;self.tg=transport;self.expected_bot_id=expected_bot_id
    def command(self,message):
        if not self.approval.authorized(message,message.get('from',{})):raise PermissionError('unauthorized')
        text=message.get('text',''); cmd=text.split()[0] if text else ''
        if cmd=='/haber_durdur':self.db.set_state('setup_activation_requested','false');self.db.set_state('enabled','false');self.db.audit('kill_switch','telegram');return 'habnews durduruldu. Kuyruk korundu.'
        if cmd=='/haber_baslat':
            from .readiness import check_ready
            from .config import sources
            active=[s for s in sources() if s['enabled']]
            missing=check_ready(self.db,require_llm=not active or any(s.get('delivery_mode')!='live_feed' for s in active))
            if missing:return 'Başlatılmadı: '+', '.join(missing)
            self.db.set_state('enabled','true');self.db.audit('start','telegram');return 'habnews başlatıldı; eski kuyruk tazelik kontrolünden geçer.'
        if cmd=='/haber_durum':return encode(self.db.health())
        if cmd=='/haber_butce':
            rows=[dict(r) for r in self.db.conn.execute('SELECT day,kind,sum(reserved) calls FROM habnews_budget GROUP BY day,kind ORDER BY day DESC LIMIT 7')]
            return encode({'local':rows,'real_pro_quota':'bilinmiyor','shared_account_limits':True,'paid_tools_usd':0})
        if cmd=='/haber_filtre':return 'Türkiye odağı: Türkiye/Türk/TL ve yerel kurum, piyasa veya şirket sinyali yeterlidir; genel Fed/altın/petrol gibi küresel başlıklar tek başına gelmez. SPK haberleri kabul edilir. Yalnız KAP içindeki rutin geri alım/pay işlemi bildirimleri ve açık yatırım tanıtımı elenir. Yeni haber önce kaynak kartı olarak gelir; model yalnız Tweet oluştur düğmesine basınca çalışır. X hesapları: @ismailsaymaz @haskologlu @abakingurlek @rterdogan.'
        if cmd=='/haber_kaynaklar':
            from .config import sources
            rows=[]
            for source in sources():
                if not source['enabled']:continue
                mode='canlı haber; Tweet oluştur düğmesi' if source.get('delivery_mode')=='live_feed' else 'aktif'
                if source.get('article_access')=='blocked_http_403':mode+='; metin erişimi engelli (403)'
                rows.append(source['owner']+' — '+mode+'; '+str(source['polling_interval']//60)+' dakikada bir')
            return '\n'.join(rows) if rows else 'Aktif kaynak yok.'
        if cmd=='/haber_taslak' and len(text.split())==2:
            ident=text.split()[1]
            if not ident.isalnum():return 'Geçersiz ID.'
            row=self.db.conn.execute('SELECT body FROM habnews_draft WHERE id=?',(ident,)).fetchone()
            return row[0] if row else 'Taslak bulunamadı; tam ID kullan.'
        return 'Komutlar: /haber_durum /haber_durdur /haber_baslat /haber_butce /haber_kaynaklar /haber_filtre /haber_taslak <id>'
    def notify_incidents(self):
        # Operational diagnostics are available via /haber_durum, never pushed into the news conversation.
        for incident in self.db.conn.execute('SELECT * FROM habnews_incident').fetchall():
            self.db.set_state('incident_notice:'+incident['id'],incident['status'])
    def tick(self):
        self.notify_incidents()
        waiting=self.db.conn.execute("SELECT 1 FROM habnews_outbox WHERE status='pending' AND next_at<=? LIMIT 1",(time.time(),)).fetchone()
        updates=self.tg.call('getUpdates',{'offset':int(self.db.state('telegram_offset','0')),'timeout':0 if waiting and self.db.enabled() else 20,'allowed_updates':['message','callback_query']})
        for update in updates:
            try:
                if 'callback_query' in update:
                    from .live_feed import feed_callback
                    from .config import sources
                    from .gpt_export import gpt_callback
                    active_sources=sources()
                    response=gpt_callback(self.db,self.approval,update,active_sources)
                    if response is None:response=feed_callback(self.db,self.approval,update,active_sources)
                    feed_response=response is not None
                    if response is None:response=self.approval.callback(update)
                    toast=('Hazırlanıyor…' if 'kaydedildi' in response or 'hazırlanıyor' in response else 'Taslak hazır.' if response.startswith('Hazırlanan taslak:') else response[:190]) if feed_response else 'İşlem kaydedildi.' if response not in ('stale','duplicate') else response
                    self.tg.call('answerCallbackQuery',{'callback_query_id':update['callback_query']['id'],'text':toast})
                    if response.startswith('revision_prompt:'):
                        did=response.split(':',1)[1]
                        sent=self.tg.call('sendMessage',{'chat_id':self.approval.chat_id,'text':'Bu mesaja yanıt olarak revizyon talimatını yaz.','reply_markup':{'force_reply':True}})
                        draft=self.db.conn.execute('SELECT event_id FROM habnews_draft WHERE id=?',(did,)).fetchone()
                        self.db.conn.execute('INSERT OR REPLACE INTO habnews_revision VALUES(?,?,?,?)',(sent['message_id'],draft[0],did,self.approval.chat_id))
                    elif feed_response:
                        if response.startswith('Hazırlanan taslak:\n\n'):
                            self.tg.call('sendMessage',{'chat_id':self.approval.chat_id,'text':response.split('\n\n',1)[1]})
                    elif response not in ('duplicate','Reddedildi.'):
                        self.tg.call('sendMessage',{'chat_id':self.approval.chat_id,'text':response})
                elif 'message' in update:
                    msg=update['message']
                    if msg.get('text','').startswith('/'):
                        key='command:'+str(update['update_id'])
                        if self.db.conn.execute('SELECT 1 FROM habnews_update WHERE id=?',(key,)).fetchone():continue
                        response=self.command(msg)
                        self.db.conn.execute('INSERT INTO habnews_update VALUES(?,?)',(key,time.time()))
                    else:response=self.approval.reply(update)
                    self.tg.call('sendMessage',{'chat_id':self.approval.chat_id,'text':response[:4096]})
            except PermissionError:
                self.db.audit('callback_authorization_error','telegram')
            self.db.set_state('telegram_offset',update['update_id']+1)
        from .readiness import activate_requested_setup
        if activate_requested_setup(self.db):
            self.tg.call('sendMessage',{'chat_id':self.approval.chat_id,'text':'Kurulum doğrulamaları tamamlandı. Foreks ve TCMB takibi açıldı; yeni doğrulanmış taslaklar bu özel sohbete gelecek. Onay yalnız paket kaydıdır, yayın yapmaz. /haber_durum /haber_durdur'})
        if self.db.enabled():Outbox(self.db,self.tg).send_one()
