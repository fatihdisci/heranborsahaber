"""Run in each built role container before operator readiness attestation."""
import json,os,socket,sys
from pathlib import Path
expected=sys.argv[1]
if expected not in ('collector','runner','approval'):raise SystemExit('role required')
if not Path('/.dockerenv').exists() or os.geteuid()!=11001:raise SystemExit('Wrong container/user')
if expected=='runner':
    for path in ('/data/habnews.sqlite','/run/secrets/telegram.json','/home/habnews/.codex/auth.json','/home/habnews/.ssh'):
        if Path(path).exists():raise SystemExit('Runner forbidden access: '+path)
    if not Path('/auth/habnews').is_dir():raise SystemExit('New auth home missing')
else:
    if Path('/auth/habnews/auth.json').exists():raise SystemExit('OAuth visible outside runner')
if expected=='collector' and Path('/run/secrets/telegram.json').exists():raise SystemExit('Bot token visible to collector')
for name in ('OPENAI_API_KEY','OPENROUTER_API_KEY','NOUS_API_KEY','CLOUDFLARE_API_TOKEN','TELEFLOW_MASTER_KEY'):
    if os.getenv(name):raise SystemExit('Forbidden credential environment')
# Public IP socket checks bypass DNS and verify internal-network direct egress is absent.
for ip in ('1.1.1.1','8.8.8.8'):
    try:
        conn=socket.create_connection((ip,443),timeout=2);conn.close()
    except OSError:pass
    else:raise SystemExit('Direct internet egress unexpectedly available')
mounts=Path('/proc/self/mountinfo').read_text()
for forbidden in ('docker.sock','/Users/','/.ssh','/.codex','heranborsacode','telegram.enc'):
    if forbidden in mounts:raise SystemExit('Forbidden mount detected')
print(json.dumps({'role':expected,'checks':'passed','uid':os.geteuid(),'direct_internet':'blocked','secrets_visibility':'role_scoped'}))
