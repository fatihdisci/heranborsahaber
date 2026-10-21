"""One job, no tools, no API-key provider, no changes to the main Hermes bot.

Run with the existing Hermes virtualenv Python. Secrets never cross into
Cloudflare: only the resulting draft and audit are returned to our bridge.
"""
import contextlib, inspect, io, json, os, pathlib, sys, time, subprocess

def runtime(home):
    profile=pathlib.Path(home).resolve()
    if profile.name!='sectorhaber' or profile.parent.name!='profiles':raise RuntimeError('isolated_profile_required')
    os.environ['HERMES_HOME']=str(profile)
    # Do not inherit API billing routes, Telegram, MCP or custom gateways.
    for key in list(os.environ):
        if key.endswith('API_KEY') or key.startswith(('TELEGRAM_','OPENAI_','OPENROUTER_')) or key in ('HERMES_CODEX_BASE_URL','GH_TOKEN','GITHUB_TOKEN'):
            os.environ.pop(key,None)
    # Let Hermes's normal global auth resolver own refresh/locking. Refreshing
    # an inherited token from a second profile could split its rotating session.
    # The token exists only in the private pipe and this process's memory.
    broker='''import contextlib,io,json,pathlib
p=pathlib.Path.home()/'.hermes/auth.json'
s=json.loads(p.read_text()).get('providers',{}).get('openai-codex',{})
if not s.get('tokens',{}).get('refresh_token'):raise RuntimeError('own_hermes_login_required')
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
 from hermes_cli.auth import resolve_codex_runtime_credentials
 c=resolve_codex_runtime_credentials()
print(json.dumps(c))'''
    env={'HOME':str(pathlib.Path.home()),'PATH':os.environ.get('PATH',''),'PYTHONPATH':os.environ.get('PYTHONPATH',''),'HERMES_HOME':str(profile.parent.parent)}
    resolved=subprocess.run([sys.executable,'-c',broker],env=env,capture_output=True,text=True,timeout=45,check=False)
    if resolved.returncode:raise RuntimeError('hermes_auth_unavailable')
    credentials=json.loads(resolved.stdout)
    if credentials.get('provider')!='openai-codex' or credentials.get('auth_mode')!='chatgpt' or credentials.get('base_url','').rstrip('/')!='https://chatgpt.com/backend-api/codex':raise RuntimeError('subscription_route_required')
    from run_agent import AIAgent
    required={'enabled_toolsets','skip_memory','skip_context_files','credential_pool','fallback_model','reasoning_config'}
    if not required.issubset(inspect.signature(AIAgent).parameters):raise RuntimeError('hermes_version_mismatch')
    return AIAgent,credentials

def decode(value):
    value=value.strip()
    if value.startswith('```'):
        value=value.split('\n',1)[1].rsplit('```',1)[0].strip()
    data=json.loads(value)
    if not isinstance(data,dict):raise ValueError('json_object_required')
    return data

def call(job,instructions,payload):
    AIAgent,credentials=runtime(job['profile'])
    agent=AIAgent(model=job['model'],provider='openai-codex',api_mode='codex_responses',api_key=credentials['api_key'],base_url=credentials['base_url'],
        enabled_toolsets=[],quiet_mode=True,skip_context_files=True,skip_memory=True,load_soul_identity=False,save_trajectories=False,
        verbose_logging=False,max_iterations=1,max_tokens=8000,reasoning_config={'effort':'high'},fallback_model=[],credential_pool=None,
        request_overrides={'max_output_tokens':8000})
    if agent.model!=job['model'] or agent.provider!='openai-codex' or getattr(agent,'tools',[]) or getattr(agent,'_fallback_chain',[]) or getattr(agent,'_credential_pool',None) or getattr(agent,'compression_enabled',True):raise RuntimeError('unsafe_agent_configuration')
    if hasattr(agent.client,'with_options'):agent.client=agent.client.with_options(max_retries=0)
    result=agent.run_conversation(user_message=json.dumps(payload,ensure_ascii=False),system_message=instructions,task_id=job['id'])
    if result.get('failed') or result.get('completed') is False:
        reason=result.get('failure_reason')
        raise RuntimeError('quota_paused' if reason in ('rate_limit','billing') else 'subscription_turn_failed')
    if result.get('api_calls',1)!=1:raise RuntimeError('unexpected_call_count')
    return decode(result['final_response'])

def presentation_issues(draft):
    if not isinstance(draft,dict) or not isinstance(draft.get('body'),str) or not isinstance(draft.get('hashtags'),list):return []
    if not isinstance(draft.get('headline'),str) or any(not isinstance(t,str) for t in draft['hashtags']):return []
    text='\n\n'.join(p for p in [draft['headline'],draft['body'],' '.join(draft['hashtags'])] if p)
    if len(text.encode('utf-16-le'))//2>1024:return ['Başlık, gövde ve etiketleri kritik olguları koruyarak toplam 1024 UTF-16 karakter içine yeniden yaz. Metni kesme veya bölme.']
    return []

def main(job):
    if job.get('provider')!='openai-codex' or job.get('model')!='gpt-6-luna' or job.get('effort')!='high' or job.get('allowed_tools')!=[] or job.get('deadline',0)<time.time():raise RuntimeError('job_route_invalid')
    instructions=job['prompt']+'\nYalnız aşağıdaki şemaya uyan JSON nesnesini döndür, başka çıktı yazma.\n'+json.dumps(job['schema'],ensure_ascii=False)
    draft=call(job,instructions,{'documents':job['documents'],'recent_events':job.get('existing_events',[]),'editor_request':job.get('edit_request')})
    if job.get('deadline',0)<time.time():raise RuntimeError('job_expired')
    audit=call(job,job['audit_prompt'],{'documents':job['documents'],'draft':draft})
    calls=2
    layout_issues=presentation_issues(draft)
    if layout_issues:audit={'supported':False,'issues':list(audit.get('issues',[]))+layout_issues}
    if audit.get('supported') is not True or audit.get('issues'):
        if job.get('deadline',0)<time.time()+90:raise RuntimeError('repair_budget_expired')
        draft=call(job,instructions,{'documents':job['documents'],'recent_events':job.get('existing_events',[]),'editor_request':job.get('edit_request'),'previous_draft':draft,'required_corrections':audit.get('issues',[])})
        audit=call(job,job['audit_prompt'],{'documents':job['documents'],'draft':draft})
        calls=4
        layout_issues=presentation_issues(draft)
        if layout_issues:audit={'supported':False,'issues':list(audit.get('issues',[]))+layout_issues}
    return {'draft':draft,'audit':audit,'runtime':{'model':job['model'],'effort':'high','provider':'openai-codex','tool_count':0,'fallback_count':0,'calls':calls,'server_model':None}}

if __name__=='__main__':
    try:
        job=json.loads(sys.stdin.read(300_001))
        # Hermes diagnostics may contain provider details. Keep them local and
        # never serialize stdout/stderr, credentials or exceptions into logs.
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):result=main(job)
        print(json.dumps(result,ensure_ascii=False))
    except Exception as e:
        code=str(e) if isinstance(e,RuntimeError) and str(e) in ('quota_paused','hermes_auth_unavailable','subscription_turn_failed','repair_budget_expired','unsafe_agent_configuration','subscription_route_required') else type(e).__name__
        print(json.dumps({'error':code}),file=sys.stderr)
        sys.exit(1)
