"""Trusted entry point, never an LLM shell tool. Only the new container home is visible."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'/app');sys.path.insert(0,'/opt/hermes')
from habnews.hermes import HERMES_REVISION,Runner,own_home,create_agent,runtime_credentials,atomic_file
if Path('/opt/hermes/REVISION').read_text()!=HERMES_REVISION:raise SystemExit('Hermes revision mismatch')
profile=own_home();profile.mkdir(mode=0o700,parents=True,exist_ok=True)
# Configuration is protected in the read-only image. Auth flow may create a config;
# restore the policy only in this isolated home before any inference.
(profile/'config.yaml').write_bytes(Path('/app/hermes-config.yaml').read_bytes())
os.chmod(profile/'config.yaml',0o600)
import logging
logging.disable(logging.CRITICAL) # No raw requests, token-bearing URLs, prompts or trajectories.
command=sys.argv[1] if len(sys.argv)>1 else 'serve'
if command=='login':
    from hermes_cli.auth import _login_openai_codex,PROVIDER_REGISTRY
    _login_openai_codex(None,PROVIDER_REGISTRY['openai-codex'],force_new_login=True)
    raise SystemExit(0)
if command=='smoke':
    # Raw account catalog, not synthetic forward-compat model aliases.
    import httpx
    creds=runtime_credentials()
    response=httpx.get('https://chatgpt.com/backend-api/codex/models?client_version=1.0.0',headers={'Authorization':'Bearer '+creds['api_key']},timeout=15)
    if response.status_code!=200:raise SystemExit('Account catalog unavailable; do not fallback')
    catalog=response.json().get('models',[])
    matching=[m for m in catalog if m.get('slug')=='gpt-6-luna' and m.get('visibility') not in ('hide','hidden')]
    if not matching:raise SystemExit('gpt-6-luna unavailable in live account catalog')
    results=[]
    for effort in ('high',):
        agent=create_agent(effort);start=time.monotonic()
        result=agent.run_conversation(user_message='TEST — sentetik testtir, gerçek haber değildir. Sadece TEST_OK yaz.',task_id='habnews-smoke-'+effort)
        if result.get('final_response','').strip()!='TEST_OK':raise SystemExit('Smoke output mismatch')
        results.append({'reasoning':effort,'duration_seconds':round(time.monotonic()-start,3),'requested_model':agent.model,'provider':agent.provider,'transport':agent.api_mode,'auth_source':'habnews_own_oauth','speed':'standard','server_model':None,'request_id':result.get('request_id'),'input_tokens':getattr(agent,'session_input_tokens',0) or None,'output_tokens':getattr(agent,'session_output_tokens',0) or None,'api_calls':result.get('api_calls'),'retry_count':0,'tool_count':0})
    atomic_file(Path('/jobs/model-smoke.json'),{'status':'passed','tested_at':time.time(),'requested_model':'gpt-6-luna','selected_reasoning':'high','reason':'User-selected GPT-6 Luna with high reasoning; no automatic effort reduction.','results':results,'effective_model_limit':'AIAgent return does not expose server effective model.'})
    raise SystemExit(0)
if command!='serve':raise SystemExit('Unsupported runner command')
smoke_path=Path('/jobs/model-smoke.json')
if not smoke_path.exists():raise SystemExit('Exact-model OAuth smoke required before runner service')
smoke=json.loads(smoke_path.read_text())
if smoke.get('status')!='passed' or smoke.get('requested_model')!='gpt-6-luna' or smoke.get('selected_reasoning')!='high':raise SystemExit('Model smoke not passed')
runner=Runner('/jobs')
while True:runner.tick();time.sleep(1)
