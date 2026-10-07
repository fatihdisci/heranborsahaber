"""Operator acceptance, after real container checks; cannot run on this unisolated host."""
import json,time,sys
from pathlib import Path
sys.path.insert(0,'/app')
from habnews.db import DB
from habnews.config import sources
from habnews.schema import lock_metadata
if not Path('/.dockerenv').exists():raise SystemExit('Target container required')
if input('Role mount/negative-egress checks passed on this host? Type HABNEWS_ISOLATED: ')!='HABNEWS_ISOLATED':raise SystemExit('Isolation acceptance missing')
smoke=json.loads(Path('/jobs/model-smoke.json').read_text())
if smoke['status']!='passed' or time.time()-smoke['tested_at']>86400:raise SystemExit('Current real OAuth model smoke required')
for run in smoke['results']:lock_metadata(run)
rows=sources()
if not any(s['enabled'] for s in rows):raise SystemExit('No validated enabled source')
db=DB('/data/habnews.sqlite')
if db.state('telegram_verified')!='true':raise SystemExit('New bot preflight missing')
if input('Backend output cap verified, plus labelled private Telegram callback acceptance completed? Type CAPS_AND_LIVE_PASSED: ')!='CAPS_AND_LIVE_PASSED':raise SystemExit('Output cap/live acceptance required; remain paused')
for key in ('isolation_verified','sources_verified','output_cap_verified','live_acceptance_verified'):db.set_state(key,'true')
db.set_state('model_smoke',json.dumps(smoke));db.set_state('llm_state','ready');db.audit('operator_acceptance','habnews',{'checked_at':time.time()})
print('Readiness recorded. Still paused. Use /haber_baslat or local start after labelled Telegram acceptance test.')
