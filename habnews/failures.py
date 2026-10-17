"""Sanitized failure categories and explicitly requested, version-bound retries."""
import json,secrets,time
from .db import uid,encode
from .normalizer import fresh

MESSAGES = {
    'source_denied': 'Kaynak, haber metnine erişimi engelledi.',
    'source_timeout': 'Kaynak metni okunurken zaman aşımı oluştu.',
    'source_parse': 'Haberin tam metni güvenilir biçimde ayrıştırılamadı.',
    'source_network': 'Haber kaynağına şu anda ulaşılamıyor.',
    'model_response': 'Tweet motorundan kullanılabilir bir yanıt alınamadı.',
    'model_timeout': 'Tweet motorunun yanıt süresi doldu.',
    'auth_required': 'Tweet motorunun oturumunun yenilenmesi gerekiyor.',
    'quota_paused': 'Tweet motorunun kullanım sınırına ulaşıldı.',
    'model_unavailable': 'Yapılandırılmış tweet modeli şu anda kullanılamıyor.',
    'validation': 'Üretilen metin kaynak ve biçim doğrulamasından geçmedi.',
    'expired': 'Bu taslak isteğinin hazırlama süresi doldu.',
    'paused': 'İşlem, haber akışı durdurulduğu için tamamlanamadı.',
    'unknown': 'Taslak hazırlanırken işlem tamamlanamadı.',
}


def record_failure(db, queue_id, stage, code):
    code = code if code in MESSAGES else 'unknown'
    db.conn.execute('INSERT OR REPLACE INTO habnews_job_failure VALUES(?,?,?,?)', (queue_id,stage,code,time.time()))


def source_failure(exc):
    status = getattr(exc,'status',None)
    if status in (401,403):return 'source_denied'
    if isinstance(exc,TimeoutError):return 'source_timeout'
    if isinstance(exc,OSError) or status:return 'source_network'
    return 'source_parse'


def failure_notice(db, approval, row):
    failure = db.conn.execute('SELECT code FROM habnews_job_failure WHERE queue_id=?',(row['id'],)).fetchone()
    code = failure[0] if failure else {'expired':'expired','paused_result':'paused'}.get(row['status'],'unknown')
    nonce=secrets.token_urlsafe(16);oid=uid()
    text=MESSAGES.get(code,MESSAGES['unknown'])
    if code=='expired':text+=' Haber kartından yeniden taslak isteyebilirsin.'
    else:text+=' Yeniden denemek için aşağıdaki düğmeyi kullanabilirsin.'
    payload={'chat_id':approval.chat_id,'text':text}
    if code!='expired':payload['reply_markup']={'inline_keyboard':[[{'text':'↻ Yeniden dene','callback_data':nonce}]]}
    db.conn.execute('INSERT INTO habnews_outbox(id,recipient,part,method,payload,next_at,created) VALUES(?,?,?,?,?,?,?)',(oid,approval.chat_id,0,'sendMessage',encode(payload),time.time(),time.time()))
    if code!='expired':db.conn.execute('INSERT INTO habnews_retry_callback VALUES(?,?,?,?,?,0)',(nonce,row['id'],approval.chat_id,None,oid))


def retry_callback(db,approval,update):
    cb=update['callback_query'];message=cb.get('message',{})
    record=db.conn.execute('SELECT * FROM habnews_retry_callback WHERE nonce=?',(cb.get('data',''),)).fetchone()
    if not record:return None
    if not approval.authorized(message,cb.get('from',{})):raise PermissionError('unauthorized_private_chat')
    with db.transaction() as c:
        key='retry:'+str(update['update_id'])
        if c.execute('SELECT 1 FROM habnews_update WHERE id=?',(key,)).fetchone():return 'duplicate'
        c.execute('INSERT INTO habnews_update VALUES(?,?)',(key,time.time()))
        if record['used'] or record['recipient']!=approval.chat_id or record['message_id']!=message.get('message_id'):return 'stale'
        if not db.enabled():return 'Akış durdurulmuş. Önce /haber_baslat kullan.'
        old=c.execute('SELECT * FROM habnews_queue WHERE id=?',(record['queue_id'],)).fetchone()
        if not old or old['kind'] not in ('research','llm') or old['status'] not in ('needs_review','dead_letter','uncertain','paused_result'):return 'stale'
        payload=json.loads(old['payload']);eid=payload['event_id'];version=payload['event_version']
        event=c.execute('SELECT * FROM habnews_event WHERE id=?',(eid,)).fetchone()
        if not event or event['version']!=version or event['status']=='rejected':return 'stale'
        item=json.loads(c.execute('SELECT payload FROM habnews_event_version WHERE event_id=? AND version=?',(eid,version)).fetchone()[0])
        if not item.get('manual_requested_at') or not fresh(item)[0]:return 'İsteğin süresi doldu. Haber kartından yeniden taslak isteyebilirsin.'
        if c.execute("SELECT 1 FROM habnews_queue WHERE status IN ('pending','leased') AND kind IN ('research','llm','draft_edit','revision') AND json_extract(payload,'$.event_id')=? AND json_extract(payload,'$.event_version')=?",(eid,version)).fetchone():return 'Tweet isteğin zaten hazırlanıyor.'
        if c.execute("SELECT 1 FROM habnews_draft WHERE event_id=? AND event_version=? AND status IN ('pending','approved') AND created>?",(eid,version,old['created'])).fetchone():return 'Taslak bu sohbette hazır.'
        if old['kind']=='llm' and db.state('llm_state')!='ready':return 'Tweet motoru hazır değil; oturum veya kullanım sınırının düzelmesini bekle.'
        c.execute('UPDATE habnews_retry_callback SET used=1 WHERE nonce=?',(record['nonce'],))
        payload['repair_attempt']=0
        identity='retry:'+record['nonce']
        if old['kind']=='research':payload['llm_identity']='llm:'+identity
        db.enqueue(old['kind'],identity,payload)
        db.audit('manual_stage_retry',old['id'],{'stage':old['kind']})
        return 'Tweet isteği kaydedildi; başarısız aşamadan devam ediliyor.'
