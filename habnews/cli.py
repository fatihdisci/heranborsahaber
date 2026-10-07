import argparse, getpass,json,os,time
from pathlib import Path
from .db import DB,encode
from .config import ROOT,sources


def secret_setup(directory):
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=directory/'telegram.json'
    if path.exists():raise RuntimeError('existing_new_bot_configuration_not_overwritten')
    token=getpass.getpass('YENİ Telegram bot tokenı (gizli): ')
    user=int(input('Numeric allowed_user_id: '));chat=int(input('Numeric private chat_id: '));bot=int(input('Yeni bot numeric ID (tokenın ilk bölümü): '))
    if input('Bu bot mevcut Her An Borsa botundan ayrı mı? EVET yaz: ').strip()!='EVET':raise RuntimeError('new_bot_identity_not_confirmed')
    from .telegram import Telegram
    Telegram(token).preflight(bot)
    if user<=0 or chat<=0:raise ValueError('private_numeric_ids')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(encode({'token':token,'user_id':user,'chat_id':chat,'bot_id':bot,'operator_confirmed_new_bot':True}))
    recipient=directory/'recipient.json'
    recipient.write_text(encode({'user_id':user,'chat_id':chat}));recipient.chmod(0o600)
    print('Yeni bot bilgileri 0600 izinleriyle kaydedildi; token yazdırılmadı.')

def dry_run(path):
    import tempfile
    from .collector import Collector
    from .approval import Approval
    from .normalizer import digest
    from .telegram import Outbox
    if Path(path).exists():raise ValueError('dry_run_requires_new_database')
    db=DB(path);db.set_state('enabled','true')
    source={'stable_id':'fixture-central-bank','source_family':'fixture-central-bank','priority':'A'}
    collector=Collector(db,[source]);collector.observe(source,[])
    now=time.time()
    item={'source_id':source['stable_id'],'provider_id':'synthetic-1','url':'https://fixture.invalid/test','title':'TEST — TCMB faiz kararı','summary':'TEST politika faizi yüzde 40 olarak karar verildi.','published_at':now,'time_precision':'second','first_seen_at':now}
    collector.observe(source,[item]);event=db.conn.execute('SELECT * FROM habnews_event ORDER BY first_seen DESC LIMIT 1').fetchone()
    ev='synthetic-evidence-'+event['id'];passage='TEST — gerçek haber değildir. TCMB politika faizini yüzde 40 olarak belirledi.'
    db.conn.execute('INSERT INTO habnews_evidence VALUES(?,?,?,?,?,?,?,?,?,?,0)',(ev,event['id'],event['version'],source['stable_id'],source['source_family'],1,item['url'],passage,digest(passage),now))
    fact=dict(text='TCMB politika faizini yüzde 40 olarak belirledi.',source_ref=ev,value_raw='40',normalized_value=40,unit='yüzde',currency=None,scale=None,period=None,scope='politika',stage='belirledi',actor='TCMB',quote=None)
    headline='TEST TCMB politika faizi'
    result=dict(schema_version='habnews-v1',event_id=event['id'],event_version=event['version'],relevance_reason='TEST — sentetik kabul paketi; gerçek haber değildir.',priority='P0',verification_state='official_primary',facts=[fact],ambiguities=[],headline=headline,proposed_body=headline+'\n\n'+fact['text'],verified_tags=[],image_candidates=[])
    job={'event_id':event['id'],'event_version':event['version'],'evidence_refs':[ev]}
    meta={'requested_model':'gpt-6-luna','provider':'openai-codex','transport':'codex_responses','auth_source':'habnews_own_oauth','speed':'standard','server_model':None,'fixture':True,'real_llm_called':False}
    approval=Approval(db,123456,123456);did=approval.create(job,result,meta)
    class Mock:
        def __init__(self):self.calls=[]
        def call(self,method,payload):self.calls.append({'method':method,'payload':payload});return {'message_id':100+len(self.calls)}
    mock=Mock();out=Outbox(db,mock);out.send_one();out.send_one()
    nonce=db.conn.execute("SELECT nonce,message_id FROM habnews_callback WHERE draft_id=? AND action='approve'",(did,)).fetchone()
    response=approval.callback({'update_id':1,'callback_query':{'id':'test-callback','data':nonce['nonce'],'from':{'id':123456},'message':{'message_id':nonce['message_id'],'chat':{'id':123456,'type':'private'}}}})
    db.set_state('enabled','false')
    return {'test_label':'TEST / SENTETİK — gerçek haber ve gerçek LLM değildir','telegram_mock_calls':mock.calls,'approval_response':response,'draft_id':did,'health':db.health()}

def service(db,role,directory,credentials):
    if role=='runner':
        from .hermes import Runner
        runner=Runner(directory)
        while True:runner.tick();time.sleep(1)
    if role=='collector':
        from .collector import Collector
        from .hermes import JobBroker
        from .approval import Approval
        from .maintenance import cleanup
        collector=Collector(db,sources());broker=JobBroker(db,directory)
        recipient=json.loads(Path('/config/recipient.json').read_text())
        approval=Approval(db,recipient['user_id'],recipient['chat_id']);last_cleanup=0
        while True:
            try:
                from .hermes import atomic_file
                if not os.getenv('HABNEWS_SWITCH_FILE'):atomic_file(Path(directory)/'runtime-state.json',{'enabled':db.enabled(),'updated_at':time.time()})
                broker.consume(approval)
                if db.enabled():
                    from .editorial import process_revision,process_image
                    collector.poll()
                    from .live_feed import process_live_feed,notify_manual_failures
                    process_live_feed(db,approval,collector.sources)
                    collector.research_one();process_revision(db);process_image(db,approval);broker.submit_one();notify_manual_failures(db,approval)
                if time.time()-last_cleanup>3600:cleanup(db,'/data/media');last_cleanup=time.time()
                db.set_state('collector_heartbeat',time.time());db.recover('collector')
                critical=db.conn.execute("SELECT id FROM habnews_queue WHERE status='pending' AND created<? LIMIT 1",(time.time()-180,)).fetchone()
                if critical:db.incident('queue_age','Pending work older than 3 minutes')
                else:db.recover('queue_age')
            except Exception as exc:
                if str(exc)!='paused':db.incident('collector',type(exc).__name__)
            time.sleep(1)
    if role=='approval':
        from .approval import Approval
        from .telegram import Telegram,ApprovalService,polling_owner
        config=json.loads(Path(credentials).read_text());tg=Telegram(config['token']);tg.preflight(config['bot_id'])
        db.set_state('telegram_verified','true')
        svc=ApprovalService(db,Approval(db,config['user_id'],config['chat_id']),tg,config['bot_id'])
        with polling_owner(str(db.path.parent/'telegram-polling.lock')):
            while True:
                try:svc.tick();db.set_state('approval_heartbeat',time.time());db.recover('approval')
                except Exception as exc:
                    db.incident('approval',type(exc).__name__);time.sleep(5)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--db',default='state/habnews.sqlite');sub=parser.add_subparsers(dest='command',required=True)
    for name in ('init','status','stop','start','health'):sub.add_parser(name)
    dry=sub.add_parser('dry-run');dry.add_argument('--output',default='reports/DRY_RUN.json')
    secret=sub.add_parser('configure-telegram');secret.add_argument('--directory',default='private')
    validate=sub.add_parser('validate-sources');validate.add_argument('--output',default='reports/source-smoke.json')
    reconcile=sub.add_parser('reconcile-delivery');reconcile.add_argument('outbox_id');reconcile.add_argument('--not-received',action='store_true',required=True);reconcile.add_argument('--reason',required=True)
    export=sub.add_parser('export-approved');export.add_argument('draft_id');export.add_argument('destination')
    backup=sub.add_parser('backup');backup.add_argument('destination');backup.add_argument('--media',default='state/media')
    restore=sub.add_parser('restore');restore.add_argument('source');restore.add_argument('destination')
    serve=sub.add_parser('serve');serve.add_argument('role',choices=['collector','approval','runner']);serve.add_argument('--jobs',default='/jobs');serve.add_argument('--credentials',default='/run/secrets/telegram.json')
    args=parser.parse_args()
    if args.command=='configure-telegram':secret_setup(args.directory);return
    if args.command=='validate-sources':
        from .source_validation import validate_sources
        print(encode(validate_sources(args.output)));return
    if args.command=='restore':
        from .maintenance import restore
        print(encode(restore(args.source,args.destination)));return
    if args.command=='dry-run':
        import tempfile
        with tempfile.TemporaryDirectory(prefix='habnews-dry-') as temp:
            report=dry_run(Path(temp)/'habnews.sqlite')
        Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2));print('Dry-run tamamlandı; gerçek gönderim/model çağrısı yapılmadı.');return
    db=DB(args.db)
    if args.command in ('init','status','health'):print(encode(db.health()))
    elif args.command=='stop':db.set_state('setup_activation_requested','false');db.set_state('enabled','false');db.audit('kill_switch','local');print('habnews durduruldu.')
    elif args.command=='start':
        from .readiness import check_ready
        active=[s for s in sources() if s['enabled']]
        missing=check_ready(db,require_llm=not active or any(s.get('delivery_mode')!='live_feed' for s in active))
        if not any(s['enabled'] for s in sources()):missing.append('no_validated_enabled_source')
        if missing:print(encode({'started':False,'missing':missing}));raise SystemExit(2)
        db.set_state('enabled','true');db.audit('start','local');print('habnews başlatıldı.')
    elif args.command=='reconcile-delivery':
        with db.transaction() as c:
            row=c.execute("SELECT * FROM habnews_outbox WHERE id=? AND status='uncertain'",(args.outbox_id,)).fetchone()
            if not row:raise ValueError('uncertain_delivery_not_found')
            c.execute("UPDATE habnews_outbox SET status='pending',next_at=?,lease=NULL WHERE id=?",(time.time(),args.outbox_id))
            db.audit('operator_resend',args.outbox_id,{'reason':args.reason[:200]})
        print('Tekrar gönderim kuyruğa alındı; tazelik kontrolü zorunlu.')
    elif args.command=='export-approved':
        from .editorial import export_approved
        print(encode(export_approved(db,args.draft_id,args.destination)))
    elif args.command=='backup':
        from .maintenance import backup
        print(encode(backup(db,args.media,args.destination)))
    elif args.command=='serve':service(db,args.role,args.jobs,args.credentials)

if __name__=='__main__':main()
