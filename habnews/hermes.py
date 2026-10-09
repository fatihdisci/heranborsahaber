"""File job contract. Only isolated runner imports AIAgent; no direct model API fallback."""
import inspect,json,os,time
from pathlib import Path
from .db import uid,encode
from .schema import MODEL,PROVIDER,TRANSPORT,REASONING,lock_metadata

HERMES_REVISION='dd0e4ab81abccf7df5b11c6c16853d5e5de9db69'

class HermesUnavailable(RuntimeError):pass

def own_home():
    home=Path(os.environ.get('HERMES_HOME','')).resolve()
    if str(home) not in ('/auth/habnews','/var/lib/habnews/auth/habnews'):raise HermesUnavailable('isolated_container_home_required')
    # Default/external credentials are inaccessible by deployment mounts, not merely a profile name.
    if Path('/home/habnews/.codex/auth.json').exists():raise HermesUnavailable('external_credential_import_risk')
    for key in os.environ:
        if key.endswith('API_KEY') or key in ('OPENAI_BASE_URL','OPENROUTER_BASE_URL','HERMES_CODEX_BASE_URL','GH_TOKEN','GITHUB_TOKEN'):
            if os.environ[key]:raise HermesUnavailable('forbidden_provider_environment')
    return home

def runtime_credentials():
    home=own_home()
    if not (home/'auth.json').is_file():raise HermesUnavailable('auth_required')
    from hermes_cli.auth import resolve_codex_runtime_credentials
    creds=resolve_codex_runtime_credentials()
    if creds.get('provider')!=PROVIDER or creds.get('source')=='credential_pool' or creds.get('auth_mode')!='chatgpt':raise HermesUnavailable('own_oauth_required')
    if creds.get('base_url','').rstrip('/')!='https://chatgpt.com/backend-api/codex':raise HermesUnavailable('provider_endpoint_mismatch')
    return creds

def create_agent(reasoning=REASONING):
    if reasoning!=REASONING:raise ValueError('reasoning_lock')
    creds=runtime_credentials()
    from run_agent import AIAgent
    required={'enabled_toolsets','skip_memory','skip_context_files','credential_pool','fallback_model','reasoning_config','request_overrides'}
    if not required.issubset(inspect.signature(AIAgent).parameters):raise HermesUnavailable('hermes_signature_mismatch')
    agent=AIAgent(model=MODEL,provider=PROVIDER,api_mode=TRANSPORT,api_key=creds['api_key'],base_url=creds['base_url'],
        enabled_toolsets=[],quiet_mode=True,skip_context_files=True,skip_memory=True,load_soul_identity=False,save_trajectories=False,
        verbose_logging=False,max_iterations=1,max_tokens=8000,reasoning_config={'effort':reasoning},
        fallback_model=[],credential_pool=None,request_overrides={'max_output_tokens':8000})
    # Version-specific post-init assertions fail closed; no implicit tools or fallback survive.
    if agent.model!=MODEL or agent.provider!=PROVIDER or agent.api_mode!=TRANSPORT:raise HermesUnavailable('runtime_route_mismatch')
    if getattr(agent,'tools',[]) or getattr(agent,'_fallback_chain',[]) or getattr(agent,'_credential_pool',None):raise HermesUnavailable('runtime_tool_or_fallback_mismatch')
    if getattr(agent,'_api_max_retries',None)!=1:raise HermesUnavailable('runtime_retry_not_disabled')
    if getattr(agent,'compression_enabled',True):raise HermesUnavailable('compression_not_disabled')
    if hasattr(agent.client,"with_options"):agent.client=agent.client.with_options(max_retries=0)
    return agent

def run_job(job,reasoning=REASONING):
    if job.get('model')!=MODEL or job.get('provider')!=PROVIDER or job.get('allowed_tools')!=[]:raise ValueError('job_lock')
    if time.time()>job['deadline']:raise HermesUnavailable('deadline_expired')
    prompt=encode(job)
    if len(prompt)>64000:raise HermesUnavailable('input_limit')
    agent=create_agent(reasoning)
    from .editorial_prompt import model_policy
    result=agent.run_conversation(user_message=prompt,task_id=job['job_id'],system_message=model_policy(job))
    if result.get('failed') or result.get('completed') is False:
        reason=result.get('failure_reason')
        raise HermesUnavailable('quota_paused' if reason in ('rate_limit','billing') else 'needs_review')
    if result.get('api_calls',1)!=1:raise HermesUnavailable('unexpected_call_count')
    # Hermes return format is not assumed to disclose the backend model. Do not invent it.
    meta={'requested_model':MODEL,'provider':agent.provider,'transport':agent.api_mode,'auth_source':'habnews_own_oauth','speed':'standard',
        'server_model':None,'effective_model_limit':'Backend model not exposed by AIAgent result','request_id':result.get('request_id'),
        'run_id':job['job_id'],'hermes_revision':HERMES_REVISION,'reasoning':reasoning,'turns':result.get('api_calls',1),'input_tokens':getattr(agent,'session_input_tokens',0) or None,'output_tokens':getattr(agent,'session_output_tokens',0) or None,'retry_count':0,'tool_count':0}
    lock_metadata(meta)
    text=result['final_response']
    if len(text)>40000:raise HermesUnavailable('output_limit')
    return {'result':json.loads(text),'run_metadata':meta}

def atomic_file(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(encode(data));temp.chmod(0o600);temp.replace(path)

class JobBroker:
    def __init__(self,db,directory):self.db=db;self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    def submit_one(self):
        self.db.require_enabled()
        if self.db.state('llm_state')!='ready':return
        if self.db.conn.execute("SELECT 1 FROM habnews_budget WHERE status='reserved' AND kind='llm' LIMIT 1").fetchone():return
        self.db.recover('llm_concurrency_limit')
        row=self.db.claim('llm')
        if not row:return
        from .budget import Budget
        payload=json.loads(row['payload']);event=self.db.conn.execute('SELECT * FROM habnews_event WHERE id=?',(payload['event_id'],)).fetchone()
        from .normalizer import fresh
        item=json.loads(self.db.conn.execute('SELECT payload FROM habnews_event_version WHERE event_id=? AND version=?',(event['id'],event['version'])).fetchone()[0])
        if event['version']!=payload['event_version'] or not fresh(item)[0]:self.db.finish(row,'expired');return
        try:reservation=Budget(self.db).reserve(event['id'],event['priority'])
        except RuntimeError as exc:
            self.db.finish(row,'pending',5 if str(exc)=='llm_concurrency_limit' else 60)
            if str(exc)!='llm_concurrency_limit':self.db.incident(str(exc),'Local LLM reservation paused')
            return
        evidence=[dict(r) for r in self.db.conn.execute('SELECT * FROM habnews_evidence WHERE event_id=? AND event_version=? AND tombstone=0',(event['id'],event['version']))]
        from .normalizer import digest
        missing_full=not evidence;media_by_ref={};contract_by_ref={}
        for record in evidence:
            fullpath=self.db.path.parent/'maintext'/(record['id']+'.json')
            if not fullpath.exists():
                missing_full=True;break
            try:full=json.loads(fullpath.read_text())
            except (ValueError,OSError):missing_full=True;break
            if not isinstance(full,dict):missing_full=True;break
            binding={k:full.get(k) for k in ('text','source_title','source_url')}
            if (full.get('expires_at',0)<time.time() or full.get('digest')!=record['digest']
                or not isinstance(full.get('text'),str) or digest(full['text'])!=record['digest']
                or full.get('document_digest') and digest(encode(binding))!=full['document_digest']
                or full.get('source_url',record['url'])!=record['url']
                or full.get('content_contract')=='article-v2' and (not full.get('document_digest') or not isinstance(full.get('source_title'),str))):
                missing_full=True;break
            record['full_text']=full['text']
            record['source_title']=full.get('source_title',item['title'])
            record['preview_url']=full.get('preview_url')
            media_by_ref[record['id']]=full.get('media')
            contract_by_ref[record['id']]=full.get('content_contract')
        if missing_full:
            Budget(self.db).finish(reservation,actual=0)
            if item.get('manual_requested_at'):
                self.db.enqueue('research','research:refresh:'+row['id'],{'event_id':event['id'],'event_version':event['version'],'source_id':item['source_id'],'item':item,'manual':True,'llm_identity':'llm:refresh:'+row['id'],'repair_attempt':payload.get('repair_attempt',0),'repair_feedback':payload.get('repair_feedback'),'revision':payload.get('revision')})
                self.db.finish(row,'refresh_queued')
            else:self.db.finish(row,'needs_review')
            return
        job={'schema_version':'habnews-job-v1','job_id':row['id'],'event_id':event['id'],'event_version':event['version'],
             'evidence_refs':[e['id'] for e in evidence],'evidence':evidence,'source_title':item['title'],'model':MODEL,'provider':PROVIDER,
             'allowed_tools':[],'deadline':time.time()+180,'max_calls':1,'max_input_chars':64000,'max_output_tokens':8000,
             'revision':payload.get('revision'),
             'repair_attempt':payload.get('repair_attempt',0),'repair_feedback':payload.get('repair_feedback'),
             'output_schema':json.loads(Path('/app/schemas/result.json').read_text()) if Path('/app/schemas/result.json').exists() else {}}
        if item.get('manual_requested_at'):
            from .config import sources
            source=next(s for s in sources() if s['stable_id']==item['source_id'])
            job['manual_attribution']={'source_type':item.get('source_type','article'),'owner':source['owner'],
                                       'account':source.get('x_account'),'url':evidence[0]['url'],'requested_url':item['url']}
            job['quiet_delivery']=True
            job['source_title']=evidence[0].get('source_title') or item['title']
            job['preview_url']=evidence[0].get('preview_url')
            job['content_contract']=contract_by_ref.get(evidence[0]['id'])
        if len(encode(job))>64000:
            Budget(self.db).finish(reservation,actual=0);self.db.finish(row,'needs_review')
            self.db.audit('model_input_rejected',event['id'],{'reason':'input_limit'});return
        from .normalizer import digest
        safe_job={k:job[k] for k in ('event_id','event_version','evidence_refs','job_id','deadline')}
        if 'manual_attribution' in job:safe_job['manual_attribution']=job['manual_attribution']
        safe_job['repair_attempt']=job.get('repair_attempt',0)
        safe_job['quiet_delivery']=job.get('quiet_delivery',False)
        safe_job['preview_url']=job.get('preview_url')
        safe_job['content_contract']=job.get('content_contract')
        safe_job['source_title']=job.get('source_title')
        safe_job['media']=media_by_ref.get(evidence[0]['id']) if evidence else None
        self.db.set_state('job:'+row['id'],encode({'lease':row['lease'],'reservation':reservation,'job':safe_job,'job_hash':digest(encode(job))}))
        try:atomic_file(self.directory/(row['id']+'.job.json'),job)
        except OSError:
            Budget(self.db).finish(reservation,actual=0,uncertain=True);self.db.finish(row,'needs_review');self.db.incident('disk','Job spool write failed');raise
    def reap_stalled(self):
        from .budget import Budget
        for row in self.db.conn.execute("SELECT key,value FROM habnews_runtime_state WHERE key LIKE 'job:%'").fetchall():
            rid=row['key'][4:]
            if (self.directory/(rid+'.result.json')).exists():continue
            state=json.loads(row['value']);job=state['job']
            if time.time()<=job['deadline']+60:continue
            Budget(self.db).finish(state['reservation'],uncertain=True)
            self.db.conn.execute("UPDATE habnews_queue SET status='uncertain',lease=NULL,lease_until=NULL WHERE id=? AND status IN ('leased','uncertain')",(rid,))
            for suffix in ('.job.json','.job.running'):(self.directory/(rid+suffix)).unlink(missing_ok=True)
            for ref in job.get('evidence_refs',[]):
                if ref.isalnum():(self.db.path.parent/'maintext'/(ref+'.json')).unlink(missing_ok=True)
            self.db.conn.execute('DELETE FROM habnews_runtime_state WHERE key=?',(row['key'],))
            self.db.audit('model_job_abandoned',rid,{'reason':'deadline_and_grace_exceeded','automatic_replay':False})
    def consume(self,approval):
        from .budget import Budget
        self.reap_stalled()
        for path in self.directory.glob('*.result.json'):
            rid=path.name.split('.')[0];stored=self.db.state('job:'+rid)
            if not stored:
                path.unlink(missing_ok=True);continue
            state=json.loads(stored);response=json.loads(path.read_text())
            full_job_path=self.directory/(rid+'.job.running')
            if full_job_path.exists():
                from .normalizer import digest
                full_job=json.loads(full_job_path.read_text())
                if digest(encode(full_job))!=state.get('job_hash'):response={'error':'needs_review'}
                else:state['job']=full_job|{'media':state['job'].get('media')}
            row={'id':rid,'lease':state['lease']}
            try:
                if response.get('error'):
                    error=response['error']
                    if error in ('auth_required','quota_paused','model_unavailable'):
                        self.db.set_state('llm_state',error);self.db.incident('llm',error)
                    else:self.db.audit('model_job_failed',rid,{'code':error})
                    Budget(self.db).finish(state['reservation'],uncertain=True)
                    self.db.finish(row,'uncertain');continue
                if not self.db.enabled():
                    self.db.finish(row,'paused_result');Budget(self.db).finish(state['reservation'],1);continue
                # Only the actual article preview accompanies a draft; no name-only image search.
                response['result']['image_candidates']=[]
                approval.create(state['job'],response['result'],response['run_metadata'],image=state['job'].get('media'))
                Budget(self.db).finish(state['reservation'],1,response['run_metadata']);self.db.finish(row)
            except Exception as exc:
                from .schema import ValidationError
                code=str(exc) if isinstance(exc,ValidationError) else type(exc).__name__
                self.db.audit('result_needs_review',rid,{'type':type(exc).__name__,'code':code})
                known=response.get('run_metadata')
                Budget(self.db).finish(state['reservation'],1 if known else None,known,uncertain=not bool(known))
                repaired=False
                repairable=code in ('generic_article_headline','unreferenced_body_claim','unsupported_sentence','incomplete_source_sentence','unsupported_headline','headline_not_source_phrase','headline_unbound_number','actor_stage_required','fact_schema','schema_keys','numeric_format_needs_review','numeric_normalization_mismatch','numeric_without_raw','tweet_too_long') or code.startswith('unsupported_')
                if isinstance(exc,ValidationError) and repairable and state['job'].get('manual_attribution') and state['job'].get('repair_attempt',0)<2:
                    eid=state['job']['event_id'];version=state['job']['event_version']
                    item=json.loads(self.db.conn.execute('SELECT payload FROM habnews_event_version WHERE event_id=? AND version=?',(eid,version)).fetchone()[0])
                    from .normalizer import fresh
                    if fresh(item)[0]:
                        attempt=state['job'].get('repair_attempt',0)+1
                        self.db.enqueue('research','research:manual-repair:'+rid,{'event_id':eid,'event_version':version,'source_id':item['source_id'],'item':item,'manual':True,'repair_attempt':attempt,'repair_feedback':{'validation_code':code,'previous_result':response.get('result')},'llm_identity':'llm:manual-repair:'+rid})
                        self.db.audit('manual_format_repair',eid,{'attempt':attempt,'code':code});repaired=True
                try:self.db.finish(row,'repair_queued' if repaired else 'needs_review')
                except RuntimeError:pass
            finally:
                path.unlink(missing_ok=True)
                (self.directory/(rid+'.job.running')).unlink(missing_ok=True)
                for reference in state['job'].get('evidence_refs',[]):
                    if reference.isalnum():(self.db.path.parent/'maintext'/(reference+'.json')).unlink(missing_ok=True)
                self.db.conn.execute('DELETE FROM habnews_runtime_state WHERE key=?',('job:'+rid,))

class Runner:
    def __init__(self,directory):
        self.directory=Path(directory);smoke=self.directory/'model-smoke.json'
        self.reasoning=REASONING
    def tick(self):
        state=Path(os.environ.get('HABNEWS_SWITCH_FILE',str(self.directory/'runtime-state.json')))
        if not state.exists() or not json.loads(state.read_text()).get('enabled'):return
        for path in self.directory.glob('*.job.json'):
            # Rename before calling: crash leaves .running, never blindly replayed.
            running=path.with_suffix('.running');path.rename(running)
            job=json.loads(running.read_text());output=self.directory/(job['job_id']+'.result.json')
            try:
                if not json.loads(state.read_text()).get('enabled'):raise HermesUnavailable('paused')
                import signal
                def deadline(signum,frame):raise HermesUnavailable('deadline_expired')
                signal.signal(signal.SIGALRM,deadline);signal.alarm(max(1,min(180,int(job['deadline']-time.time()))))
                try:response=run_job(job,self.reasoning)
                finally:signal.alarm(0)
            except Exception as exc:
                code=getattr(exc,'status_code',None)
                message=str(exc) if isinstance(exc,HermesUnavailable) else ''
                error='quota_paused' if code==429 else 'auth_required' if code in (401,403) or message=='auth_required' or getattr(exc,'relogin_required',False) else 'quota_paused' if message=='quota_paused' else 'model_unavailable' if code==404 else 'needs_review'
                response={'error':error,'exception_type':type(exc).__name__}
            atomic_file(output,response)
