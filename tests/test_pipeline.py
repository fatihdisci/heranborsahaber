import json,time
from habnews.collector import Collector
from habnews.hermes import JobBroker,Runner
from habnews.approval import Approval


def test_full_pipeline_reads_main_text_and_removes_raw_spool(db,tmp_path,monkeypatch):
    source={'stable_id':'fixture','source_family':'fixture','priority':'A','allowed_hosts':['fixture.invalid']}
    c=Collector(db,[source]);c.observe(source,[])
    item={'provider_id':'TEST-1','url':'https://fixture.invalid/test','title':'TEST TCMB politika faiz kararı','summary':'TCMB politika faizini yüzde 40 olarak belirledi.','published_at':time.time(),'time_precision':'second','first_seen_at':time.time()}
    c.observe(source,[item])
    sentence='TEST: TCMB politika faizini yüzde 40 olarak belirledi.'
    main=sentence+' Bu metin sentetik bir testtir, gerçek haber değildir. '*5
    html=('<article><p>'+main+'</p></article>').encode()
    monkeypatch.setattr('habnews.collector.Fetcher.get',lambda *a,**k:(html,{'content-type':'text/html'},item['url'],200))
    c.research_one();db.set_state('llm_state','ready')
    directory=tmp_path/'jobs';broker=JobBroker(db,directory);broker.submit_one()
    job_path=next(directory.glob('*.job.json'));job=json.loads(job_path.read_text())
    assert ' '.join(main.split()) == job['evidence'][0]['full_text']
    assert 'full_text' not in db.state('job:'+job['job_id'])
    def mock_run(job,reasoning):
        ref=job['evidence_refs'][0]
        fact={'text':sentence,'source_ref':ref,'value_raw':'40','normalized_value':40,'unit':'yüzde','currency':None,'scale':None,'period':None,'scope':'politika','stage':'belirledi','actor':'TCMB','quote':None}
        result={'schema_version':'habnews-v1','event_id':job['event_id'],'event_version':job['event_version'],'relevance_reason':'TEST fixture','priority':'P0','verification_state':'official_primary','facts':[fact],'ambiguities':[],'headline':'TEST TCMB politika faizi','proposed_body':'TEST TCMB politika faizi\n\n'+sentence,'verified_tags':[],'image_candidates':[]}
        meta={'requested_model':'gpt-6-luna','provider':'openai-codex','transport':'codex_responses','auth_source':'habnews_own_oauth','speed':'standard','server_model':None,'fixture':True}
        return {'result':result,'run_metadata':meta}
    monkeypatch.setattr('habnews.hermes.run_job',mock_run)
    monkeypatch.setattr('habnews.images.CommonsCandidates.search',lambda *a:[])
    (directory/'runtime-state.json').write_text('{"enabled":true}')
    Runner(directory).tick();broker.consume(Approval(db,123,123))
    assert db.conn.execute("SELECT count(*) FROM habnews_draft WHERE status='pending'").fetchone()[0]==1
    assert db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]==2
    assert not list(directory.glob('*.job.running'))
    assert not list((db.path.parent/'maintext').glob('*.json'))
    assert db.state('job:'+job['job_id']) is None
