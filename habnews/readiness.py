import json,time

def check_ready(db,require_llm=True):
    missing=[]
    for key in ('isolation_verified','telegram_verified','sources_verified','output_cap_verified','live_acceptance_verified'):
        if db.state(key)!='true':missing.append(key)
    if require_llm:
        if db.state('llm_state')!='ready':missing.append(db.state('llm_state','auth_required'))
        smoke=json.loads(db.state('model_smoke','{}'))
        if smoke.get('requested_model')!='gpt-6-luna' or smoke.get('status')!='passed' or smoke.get('selected_reasoning')!='high':missing.append('exact_model_oauth_smoke_required')
        if time.time()-smoke.get('tested_at',0)>86400:missing.append('model_smoke_expired')
    from .config import sources
    if not any(source["enabled"] for source in sources()):missing.append("no_validated_enabled_source")
    return sorted(set(missing))


def activate_requested_setup(db):
    """One initial activation authorized by installation; a manual stop cancels it."""
    if db.state('setup_activation_requested')!='true' or check_ready(db):return False
    with db.transaction():
        if db.state('setup_activation_requested')!='true':return False
        db.set_state('setup_activation_requested','false')
        db.set_state('enabled','true')
        db.audit('initial_setup_activated','habnews')
    return True
