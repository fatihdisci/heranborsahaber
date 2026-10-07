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
    import shutil
    draft=db.conn.execute('SELECT * FROM habnews_draft WHERE id=?',(draft_id,)).fetchone()
    if not draft or draft['status']!='approved':raise ValueError('exact_draft_not_approved')
    event=db.conn.execute('SELECT version FROM habnews_event WHERE id=?',(draft['event_id'],)).fetchone()
    if event[0]!=draft['event_version']:raise ValueError('approval_stale')
    decision=db.conn.execute("SELECT hash FROM habnews_decision WHERE draft_id=? AND action='approve' ORDER BY created DESC LIMIT 1",(draft_id,)).fetchone()
    if not decision or decision[0]!=draft['hash']:raise ValueError('approval_hash_mismatch')
    dest=Path(destination);dest.mkdir(mode=0o700,parents=True,exist_ok=False)
    (dest/'draft.txt').write_text(draft['body']);(dest/'metadata.json').write_text(draft['metadata'])
    meta=json.loads(draft['metadata']);image=meta.get('image')
    from .images import reusable
    if image and reusable(image.get('provenance',{})):
        file=Path(image['path']).resolve()
        if file.parent!=Path('/data/media'):raise ValueError('media_path')
        shutil.copyfile(file,dest/('original'+file.suffix))
        (dest/'attribution.txt').write_text(image['provenance']['attribution_text']+'\n'+image['provenance']['license_url'])
    elif image:(dest/'attribution.txt').write_text('Özel kaynak önizlemesi; görselin yeniden yayınlama izni doğrulanmadığı için paylaşım paketine eklenmedi.\n'+image['provenance']['landing_page_url']+'\n')
    else:(dest/'attribution.txt').write_text('text_only — Kullanım hakkı uygun görsel bulunamadı.\n')
    for file in dest.iterdir():file.chmod(0o600)
    return {'draft_id':draft_id,'hash':draft['hash'],'published':False,'package':str(dest)}
