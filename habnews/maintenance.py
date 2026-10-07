import json, shutil,time
from pathlib import Path
from .db import encode


def cleanup(db,media_dir,now=None):
    now=now or time.time()
    maintext=db.path.parent/'maintext'
    if maintext.exists():
        for path in maintext.glob('*.json'):
            try:expired=json.loads(path.read_text()).get('expires_at',0)<now
            except (ValueError,OSError):expired=True
            if expired:path.unlink(missing_ok=True)
    with db.transaction() as c:
        # Any active review protects all evidence/provenance for that event.
        active="SELECT event_id FROM habnews_draft WHERE status IN ('pending','needs_review')"
        c.execute(f"UPDATE habnews_evidence SET passage='',tombstone=1 WHERE retrieved<? AND event_id NOT IN ({active})",(now-30*86400,))
        c.execute("UPDATE habnews_observation SET metadata='{}',stage='tombstone' WHERE first_seen<? AND id NOT IN (SELECT eo.observation_id FROM habnews_event_observation eo JOIN habnews_draft d ON d.event_id=eo.event_id WHERE d.status IN ('pending','needs_review'))",(now-90*86400,))
        c.execute("UPDATE habnews_draft SET body='',status='tombstone' WHERE created<? AND status NOT IN ('pending','needs_review')",(now-180*86400,))
        c.execute('DELETE FROM habnews_update WHERE created<?',(now-180*86400,))
        c.execute("DELETE FROM habnews_audit WHERE created<? AND subject NOT IN (SELECT id FROM habnews_draft WHERE status IN ('pending','needs_review')) AND subject NOT IN (SELECT id FROM habnews_event WHERE status IN ('pending','needs_review','verification_pending'))",(now-180*86400,))
        c.execute("DELETE FROM habnews_decision WHERE created<? AND draft_id IN (SELECT id FROM habnews_draft WHERE status='tombstone')",(now-180*86400,))
        root=Path(media_dir).resolve()
        for row in c.execute(f"SELECT * FROM habnews_image_candidate WHERE created<? AND tombstone=0 AND event_id NOT IN ({active})",(now-30*86400,)).fetchall():
            if row['path']:
                file=Path(row['path']).resolve()
                if file.parent!=root:raise ValueError('media_path_outside_namespace')
                file.unlink(missing_ok=True)
                file.with_suffix('.json').unlink(missing_ok=True)
                file.with_suffix('.attribution.txt').unlink(missing_ok=True)
            c.execute('UPDATE habnews_image_candidate SET tombstone=1,path=NULL WHERE id=?',(row['id'],))
        db.audit('retention','habnews',{'completed_at':now})

def backup(db,media_dir,destination):
    from .normalizer import digest
    dest=Path(destination);dest.mkdir(parents=True,mode=0o700,exist_ok=False)
    db.backup(dest/'habnews.sqlite')
    src=Path(media_dir)
    if src.exists():
        if any(p.is_symlink() for p in src.rglob('*')):raise ValueError('backup_symlink_denied')
        shutil.copytree(src,dest/'media',symlinks=False)
    manifest=[]
    for path in dest.rglob('*'):
        if path.is_file():
            if path.is_symlink():raise ValueError('backup_symlink_denied')
            import hashlib
            path.chmod(0o600);manifest.append({'path':str(path.relative_to(dest)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (dest/'manifest.json').write_text(encode(manifest));(dest/'manifest.json').chmod(0o600)
    return manifest

def restore(source,destination):
    import hashlib
    src=Path(source).resolve(); dest=Path(destination)
    if dest.exists():raise ValueError('restore_destination_must_be_new')
    for row in json.loads((src/'manifest.json').read_text()):
        file=(src/row['path']).resolve()
        if not file.is_relative_to(src) or file.is_symlink() or hashlib.sha256(file.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('backup_integrity')
    shutil.copytree(src,dest)
    from .db import DB
    db=DB(dest/'habnews.sqlite')
    # Restored copies are offline; never write the running instance's control mount.
    db.conn.execute("UPDATE habnews_runtime_state SET value='false' WHERE key IN ('enabled','setup_activation_requested')")
    if db.conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('restore_integrity')
    db.audit('restore','habnews');return db.health()
