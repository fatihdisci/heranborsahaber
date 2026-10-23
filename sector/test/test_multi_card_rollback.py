import importlib.util,json,pathlib,sqlite3,tempfile,unittest
spec=importlib.util.spec_from_file_location('hold_multi_cards',pathlib.Path(__file__).parents[1]/'scripts/hold_multi_cards.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class MultiCardRollback(unittest.TestCase):
    def seed(self,path):
        db=sqlite3.connect(path);db.executescript((pathlib.Path(__file__).parents[1]/'migrations/0001_sector.sql').read_text());db.execute('PRAGMA application_id=1397048148')
        for name,state in [('single',None),('queued','queued'),('uploading','uploading'),('posting','posting'),('sent','sent'),('uncertain','uncertain'),('manual',None)]:
            key='drafts/'+name+'/1.png';db.execute("INSERT INTO drafts(id,event_key,fingerprint,content,documents,verification,created_at,expires_at,media_key,message_id,delivery_state) VALUES(?,?,?,'{}','[]','verified',1,9999999999,?,9,'sent')",(name,name,name,key))
            if name!='single':db.execute('INSERT INTO system_state VALUES(?,?)',('draft_media:'+key,json.dumps({'version':1,'pages':[{'key':key},{'key':key+'2'}]})))
            if state:db.execute("INSERT INTO x_posts(id,draft_id,revision,day,state,content,media_key,created_at) VALUES(?,?,1,'2026-10-23',?,'unchanged',?,1)",(name,name,state,key))
        db.execute("INSERT INTO publication_marks VALUES('manual','published',1,1)");db.execute("INSERT INTO news_interest_actions VALUES(1,'owner','news','like',1)");db.commit();return db
    def test_dry_run_is_read_only_and_does_not_touch_single_or_published_products(self):
        with tempfile.TemporaryDirectory() as directory:
            path=pathlib.Path(directory)/'db.sqlite';db=self.seed(path);before='\n'.join(db.iterdump());result=module.hold(path)
            self.assertEqual(result['drafts'],4);self.assertEqual(result['queued_uploads_held'],2);self.assertEqual(result['posts_made_uncertain'],1);self.assertEqual('\n'.join(db.iterdump()),before);db.close()
    def test_apply_holds_pending_multi_media_without_rewriting_receipts_manifests_or_votes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=pathlib.Path(directory)/'db.sqlite';db=self.seed(path)
            protected={t:db.execute('SELECT * FROM '+t).fetchall() for t in ('news_interest_actions','publication_marks')};manifests=db.execute("SELECT * FROM system_state WHERE key LIKE 'draft_media:%'").fetchall();receipts=db.execute("SELECT * FROM x_posts WHERE state IN ('sent','uncertain')").fetchall()
            module.hold(path,True,123)
            self.assertEqual(dict(db.execute('SELECT id,state FROM drafts')),{name:'pending' if name in ('single','sent','manual') else 'needs_review' for name in ('single','queued','uploading','posting','sent','uncertain','manual')})
            self.assertEqual(dict(db.execute('SELECT id,state FROM x_posts')),{'queued':'failed','uploading':'failed','posting':'uncertain','sent':'sent','uncertain':'uncertain'})
            self.assertEqual(db.execute("SELECT * FROM system_state WHERE key LIKE 'draft_media:%'").fetchall(),manifests)
            self.assertEqual(db.execute("SELECT * FROM x_posts WHERE id IN ('sent','uncertain')").fetchall(),receipts)
            for table,rows in protected.items():self.assertEqual(db.execute('SELECT * FROM '+table).fetchall(),rows)
            module.hold(path,True,124);self.assertEqual(db.execute("SELECT count(*) FROM system_state WHERE key LIKE 'multi_card_rollback:%'").fetchone()[0],4);db.close()
    def test_namespace_failure_never_writes_an_unrelated_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path=pathlib.Path(directory)/'other.sqlite';db=sqlite3.connect(path);db.execute('CREATE TABLE untouched(value)');db.commit();db.close()
            before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'database_namespace'):module.hold(path,True)
            self.assertEqual(path.read_bytes(),before)
