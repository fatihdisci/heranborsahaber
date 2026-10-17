"""Deterministic revision/image routing. Model output never writes state directly."""
import json,time
from .db import uid,encode
from .images import CommonsCandidates
from .normalizer import fresh


def process_revision(db):
    db.require_enabled();row=db.claim('revision')
    if not row:return
    payload=json.loads(row['payload']);event=db.conn.execute('SELECT * FROM habnews_event WHERE id=?',(payload['event_id'],)).fetchone()
    item=json.loads(db.conn.execute('SELECT payload FROM habnews_event_version WHERE event_id=? AND version=?',(event['id'],event['version'])).fetchone()[0])
    if not fresh(item)[0]:db.finish(row,'expired');return
    with db.transaction():
        obs=db.conn.execute('SELECT o.* FROM habnews_observation o JOIN habnews_event_observation eo ON eo.observation_id=o.id WHERE eo.event_id=? ORDER BY o.first_seen DESC LIMIT 1',(event['id'],)).fetchone()
        if not obs:db.finish(row,'needs_review');return
        item_for_revision=json.loads(obs['metadata'])
        if item.get('manual_requested_at'):item_for_revision.update(manual_requested_at=time.time(),source_id=obs['source_id'])
        db.enqueue('research','research:revision:'+row['id'],{'event_id':event['id'],'event_version':event['version'],'source_id':obs['source_id'],'observation_id':obs['id'],'item':item_for_revision,'revision':{'instruction':payload['instruction'],'previous_draft_id':payload['draft_id']},'llm_identity':'llm:revision:'+row['id']})
        db.finish(row)

def process_image(db,approval):
    db.require_enabled();row=db.claim('image')
    if not row:return
    payload=json.loads(row['payload']);draft=db.conn.execute('SELECT * FROM habnews_draft WHERE id=?',(payload['draft_id'],)).fetchone()
    event=db.conn.execute('SELECT * FROM habnews_event WHERE id=?',(draft['event_id'],)).fetchone()
    if event['version']!=draft['event_version']:db.finish(row,'stale');return
    meta=json.loads(draft['metadata']);result=meta['validated_result']
    try:
        candidates=CommonsCandidates(db.require_enabled).search(result['facts'][0]['actor'][:80])
        result['image_candidates']=candidates
        job={'event_id':event['id'],'event_version':event['version'],'evidence_refs':[f['source_ref'] for f in result['facts']]}
        if meta.get('manual_attribution'):job['manual_attribution']=meta['manual_attribution']
        approval.create(job,result,meta['run']);db.finish(row)
    except Exception as exc:
        db.audit('image_needs_review',row['id'],{'type':type(exc).__name__});db.finish(row,'needs_review')

def export_approved(db,draft_id,destination):
    from pathlib import Path
    import hashlib
    draft=db.conn.execute('SELECT * FROM habnews_draft WHERE id=?',(draft_id,)).fetchone()
    if not draft or draft['status']!='approved':raise ValueError('exact_draft_not_approved')
    event=db.conn.execute('SELECT version FROM habnews_event WHERE id=?',(draft['event_id'],)).fetchone()
    if event[0]!=draft['event_version']:raise ValueError('approval_stale')
    decision=db.conn.execute("SELECT hash FROM habnews_decision WHERE draft_id=? AND action='approve' ORDER BY created DESC LIMIT 1",(draft_id,)).fetchone()
    if not decision or decision[0]!=draft['hash']:raise ValueError('approval_hash_mismatch')
    meta=json.loads(draft['metadata']);image=meta.get('image')
    from .images import reusable
    export_image=bool(image and reusable(image.get('provenance',{})))
    if export_image:
        file=Path(image['path']).resolve()
        if file.parent!=Path('/data/media'):raise ValueError('media_path')
        blob=file.read_bytes()
        if hashlib.sha256(blob).hexdigest()!=image['provenance'].get('sha256'):raise ValueError('media_digest')
    dest=Path(destination);dest.mkdir(mode=0o700,parents=True,exist_ok=False)
    (dest/'draft.txt').write_text(draft['body']);(dest/'metadata.json').write_text(draft['metadata'])
    if export_image:
        (dest/('original'+file.suffix)).write_bytes(blob)
        (dest/'attribution.txt').write_text(image['provenance']['attribution_text']+'\n'+image['provenance']['license_url'])
    elif image:(dest/'attribution.txt').write_text('Özel kaynak önizlemesi; görselin yeniden yayınlama izni doğrulanmadığı için paylaşım paketine eklenmedi.\n'+image['provenance']['landing_page_url']+'\n')
    else:(dest/'attribution.txt').write_text('text_only — Kullanım hakkı uygun görsel bulunamadı.\n')
    for file in dest.iterdir():file.chmod(0o600)
    return {'draft_id':draft_id,'hash':draft['hash'],'published':False,'package':str(dest)}


def process_draft_edit(db, approval):
    """Re-render retained validated facts; model work is used only if needed."""
    from .schema import validate_result, ValidationError
    db.require_enabled()
    row = db.claim('draft_edit')
    if not row:
        return
    payload = json.loads(row['payload'])
    draft = db.conn.execute('SELECT * FROM habnews_draft WHERE id=?', (payload['draft_id'],)).fetchone()
    event = db.conn.execute('SELECT * FROM habnews_event WHERE id=?', (payload['event_id'],)).fetchone()
    latest = db.conn.execute('SELECT max(version) FROM habnews_draft WHERE event_id=?', (payload['event_id'],)).fetchone()[0]
    if not draft or not event or event['version'] != payload['event_version'] or draft['hash'] != payload['hash'] or draft['version'] != latest or draft['status'] != 'pending':
        db.finish(row, 'stale')
        return
    item = json.loads(db.conn.execute('SELECT payload FROM habnews_event_version WHERE event_id=? AND version=?', (event['id'], event['version'])).fetchone()[0])
    if not fresh(item)[0]:
        db.finish(row, 'expired')
        approval._out(None, 0, 'Bu taslak için düzenleme süresi doldu. Haber kartından yeniden taslak isteyebilirsin.')
        return
    meta = json.loads(draft['metadata'])
    result = meta['validated_result']
    options = dict(meta.get('editorial_context', {}).get('editorial_options', {}))
    if payload['mode'] == 'no_tags':
        options['no_tags'] = True
    job = dict(meta.get('editorial_context', {})) | {
        'event_id': event['id'], 'event_version': event['version'],
        'evidence_refs': list({f['source_ref'] for f in result['facts']}),
        'manual_attribution': meta['manual_attribution'], 'quiet_delivery': True,
        'edit_controls': True, 'controlled_rewrite': True, 'editorial_options': options,
    }
    if payload['mode']=='no_tags':
        job['controlled_rewrite']=meta.get('editorial_context',{}).get('controlled_rewrite',False)
    evidence = {r['id']: dict(r) for r in db.conn.execute('SELECT * FROM habnews_evidence WHERE event_id=? AND event_version=? AND tombstone=0', (event['id'], event['version']))}
    candidates = [result]
    if payload['mode'] in ('shorten', 'headline'):
        headings = [job.get('source_title', '')] + [f['text'].rstrip('.!?') for f in result['facts']]
        for heading in headings:
            if heading and heading != result['headline']:
                candidates.append(result | {'headline': heading, 'proposed_body': heading + '\n\n' + '\n\n'.join(f['text'] for f in result['facts'])})
    valid = []
    for candidate in candidates:
        try:
            text = validate_result(candidate, job, evidence)
        except ValidationError:
            continue
        if text == draft['body']:
            continue
        if payload['mode'] == 'shorten' and len(text) >= len(draft['body']):
            continue
        if payload['mode'] == 'headline' and candidate['headline'] == result['headline']:
            continue
        valid.append((candidate, text))
    if valid:
        chosen = min(valid, key=lambda value: len(value[1]))[0]
        try:
            approval.create(job, chosen, meta['run'], image=meta.get('image'))
        except Exception as exc:
            db.audit('draft_edit_failure', draft['id'], {'type': type(exc).__name__})
            db.finish(row, 'needs_review')
            db.conn.execute('UPDATE habnews_callback SET used=0 WHERE draft_id=?', (draft['id'],))
            approval._out(None, 0, 'Düzenlenmiş taslak hazırlanamadı. Aynı düzenleme düğmesinden tekrar deneyebilirsin.')
            return
        db.audit('draft_edited', draft['id'], {'mode': payload['mode'], 'model_calls': 0})
        db.finish(row)
        return
    if payload['mode'] == 'no_tags':
        db.conn.execute('UPDATE habnews_callback SET used=0 WHERE draft_id=?', (draft['id'],))
        approval._out(None, 0, 'Bu taslakta kaldırılacak etiket yok.')
        db.finish(row)
        return
    instructions = {
        'shorten': 'Aynı gelişmeyi daha kısa anlat. Gerekli koşul, dönem, yalanlama ve atfı çıkarma. Tam kaynak cümleleri kullan; başlık tekrarını önle.',
        'simplify': 'Aynı gelişme için daha sade ve kendi başına anlaşılır kaynak cümleleri seç. Teknik ayrıntıyı azaltırken anlamı ve gerekli koşulları koru.',
        'headline': 'Aynı gelişme için önceki başlıktan farklı, kaynakta birebir bulunan açık bir başlık veya tam cümle seç. Olguların anlamını değiştirme.',
    }
    if db.state('llm_state') != 'ready':
        db.conn.execute('UPDATE habnews_callback SET used=0 WHERE draft_id=?', (draft['id'],))
        approval._out(None, 0, 'Tweet motoru şu anda hazır değil. Mevcut taslağın korunuyor; düzenlemeyi daha sonra deneyebilirsin.')
        db.finish(row)
        return
    db.enqueue('llm', 'llm:edit:' + row['id'], {
        'event_id': event['id'], 'event_version': event['version'], 'editorial_options': options,
        'revision': {'instruction': instructions[payload['mode']], 'previous_draft_id': draft['id'], 'previous_headline': result['headline']},
        'edit_request': {'draft_id':draft['id'],'hash':draft['hash'],'mode':payload['mode'],'previous_text':draft['body']},
    })
    db.finish(row)
