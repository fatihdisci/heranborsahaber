"""Conservative cross-publisher grouping; matching is not corroboration."""
import json,time
from .db import encode,uid
from .normalizer import norm


def group_duplicate(db, approval, source, item, observation):
    if source.get('method') == 'nitter_rss' or len(norm(item['title'])) < 40 or len(norm(item.get('summary', ''))) < 80:
        return False
    # Identical complete title + summary, a narrow publication window and a
    # different publisher are required. Different numbers or claims never merge.
    candidates = db.conn.execute("SELECT o.*, f.outbox_id FROM habnews_observation o JOIN habnews_feed_callback f ON f.observation_id=o.id WHERE o.digest=? AND o.source_id<>? AND o.first_seen>? AND o.stage='feed_queued' ORDER BY o.first_seen", (observation['digest'],source['stable_id'],time.time()-1800)).fetchall()
    for candidate in candidates:
        old = json.loads(candidate['metadata'])
        if old.get('source_type') == 'social_x' or not old.get('published_at') or not item.get('published_at') or abs(old['published_at']-item['published_at']) > 1800:
            continue
        if norm(old['title']) != norm(item['title']) or norm(old.get('summary','')) != norm(item.get('summary','')):
            continue
        outbox = db.conn.execute("SELECT * FROM habnews_outbox WHERE id=? AND status IN ('pending','sent')", (candidate['outbox_id'],)).fetchone()
        if not outbox:
            continue
        payload = json.loads(outbox['payload'])
        markup = payload['reply_markup']
        links = [button['url'] for row in markup['inline_keyboard'] for button in row if 'url' in button and not button['url'].startswith('https://t.me/')]
        if len(links) >= 8:
            continue
        if item['url'] not in links:
            markup['inline_keyboard'].append([{'text':'Aynı haber · '+source['owner'][:50], 'url':item['url']}])
        if outbox['status'] == 'pending':
            db.conn.execute('UPDATE habnews_outbox SET payload=? WHERE id=?', (encode(payload),outbox['id']))
        else:
            # Store the newest markup for further duplicates, then queue a
            # private message edit. It does not create another news message.
            db.conn.execute('UPDATE habnews_outbox SET payload=? WHERE id=?', (encode(payload),outbox['id']))
            edit={'chat_id':approval.chat_id,'message_id':outbox['message_id'],'reply_markup':markup}
            db.conn.execute('INSERT INTO habnews_outbox(id,recipient,part,method,payload,next_at,created) VALUES(?,?,?,?,?,?,?)', (uid(),approval.chat_id,0,'editMessageReplyMarkup',encode(edit),time.time(),time.time()))
        db.conn.execute('INSERT INTO habnews_feed_group VALUES(?,?,?)', (observation['id'],candidate['id'],time.time()))
        db.conn.execute("UPDATE habnews_observation SET stage='feed_grouped' WHERE id=?", (observation['id'],))
        db.audit('feed_duplicate_grouped',observation['id'],{'primary':candidate['id'],'independent_confirmation':False})
        return True
    return False


def update_note(db, observation, item):
    previous = db.conn.execute("SELECT metadata FROM habnews_observation WHERE source_id=? AND id<>? AND (provider_id=? OR url=?) AND first_seen<=? AND first_seen>? AND stage IN ('feed_queued','feed_grouped') ORDER BY first_seen DESC LIMIT 1", (observation['source_id'],observation['id'],observation['provider_id'],observation['url'],observation['first_seen'],observation['first_seen']-86400)).fetchone()
    if not previous:
        return ''
    old = json.loads(previous['metadata'])
    # Explicitly compare source text; do not infer a numeric delta or causality.
    if norm(old.get('title','')) != norm(item['title']):
        return '\n\n↻ Kaynak başlığı güncellendi.\nÖnceki: '+old['title'][:220]
    if norm(old.get('summary','')) != norm(item.get('summary','')):
        return '\n\n↻ Kaynak özeti güncellendi.\nÖnceki özet: '+old.get('summary','')[:220]
    return ''
