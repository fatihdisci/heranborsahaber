"""Rollback prerequisite, after the news consumer has stopped.

Dry-run by default. Hold only unsent multi-media products; never restore a DB,
delete media/manifests, replay a queue, or mark an external delivery successful.
The returned control IDs are for an operator to remove inline buttons safely.
"""
import argparse,json,sqlite3,time

def hold(database,apply=False,at=None):
    at=int(time.time()*1000) if at is None else at
    connection=sqlite3.connect('file:'+str(database)+'?mode='+('rw' if apply else 'ro'),uri=True)
    connection.row_factory=sqlite3.Row
    try:
        connection.execute('PRAGMA busy_timeout=5000')
        if not apply:connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
        if connection.execute('PRAGMA application_id').fetchone()[0]!=0x53454354:raise ValueError('database_namespace')
        rows=connection.execute("""SELECT d.id,d.revision,d.message_id,d.state,s.value FROM drafts d
          JOIN system_state s ON s.key='draft_media:'||d.media_key
          WHERE NOT EXISTS(SELECT 1 FROM x_posts x WHERE x.draft_id=d.id AND x.state='sent')
          AND NOT EXISTS(SELECT 1 FROM publication_marks m WHERE m.draft_id=d.id AND m.state='published')""").fetchall()
        selected=[]
        for row in rows:
            manifest=json.loads(row['value'])
            if manifest.get('version')!=1 or not isinstance(manifest.get('pages'),list):raise ValueError('media_manifest_invalid')
            if len(manifest['pages'])>1:selected.append(row)
        result={'apply':apply,'drafts':len(selected),'queued_uploads_held':0,'posts_made_uncertain':0,'controls':[],'unknown_control':0}
        for row in selected:
            if row['message_id']:result['controls'].append({'draft_id':row['id'],'revision':row['revision'],'message_id':row['message_id']})
            else:result['unknown_control']+=1
            result['queued_uploads_held']+=connection.execute("SELECT count(*) FROM x_posts WHERE draft_id=? AND state IN ('queued','uploading')",(row['id'],)).fetchone()[0]
            result['posts_made_uncertain']+=connection.execute("SELECT count(*) FROM x_posts WHERE draft_id=? AND state='posting'",(row['id'],)).fetchone()[0]
            if apply:
                connection.execute("UPDATE drafts SET state='needs_review' WHERE id=? AND revision=? AND state IN ('pending','deferred')",(row['id'],row['revision']))
                connection.execute("UPDATE x_posts SET state='failed',error='multi_card_rollback_hold' WHERE draft_id=? AND state IN ('queued','uploading')",(row['id'],))
                connection.execute("UPDATE x_posts SET state='uncertain',error='rollback_interrupted_post' WHERE draft_id=? AND state='posting'",(row['id'],))
                connection.execute('INSERT OR IGNORE INTO system_state(key,value) VALUES(?,?)',('multi_card_rollback:'+row['id']+':'+str(row['revision']),json.dumps({'at':at,'previous_state':row['state']})))
        connection.commit() if apply else connection.rollback()
        return result
    finally:connection.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('database');parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    print(json.dumps(hold(args.database,args.apply)))
