#!/bin/bash
set -euo pipefail
HABNEWS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
/usr/bin/caffeinate -i -w "$$" &
"$HABNEWS_ROOT/deploy/macos.sh" vm-start
"$HABNEWS_ROOT/deploy/macos.sh" compose up -d provider-egress telegram-egress approval collector source-egress
# News/model remain gated by their persisted readiness state. No old services touched.
if "$HABNEWS_ROOT/deploy/macos.sh" compose run --rm --no-deps --entrypoint python collector -c 'from pathlib import Path; import json; p=Path("/jobs/model-smoke.json"); assert p.exists() and json.loads(p.read_text()).get("status")=="passed"' >/dev/null 2>&1; then
 "$HABNEWS_ROOT/deploy/macos.sh" compose up -d runner
fi
while "$HABNEWS_ROOT/deploy/macos.sh" vm-status >/dev/null 2>&1; do sleep 30; done
exit 1
