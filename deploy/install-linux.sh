#!/usr/bin/env bash
set -euo pipefail
# Run ONLY on the intended host. Creates exclusively new habnews resources.
[[ "$(uname -s)" == Linux ]] || { echo 'Linux container host required; no existing Hermes will be changed.'; exit 2; }
command -v docker >/dev/null || { echo 'Docker/Compose missing. This script does not install or restart a daemon.'; exit 2; }
docker compose version >/dev/null
[[ $EUID -eq 0 ]] || { echo 'Run as root to create the separate OS user and directories.'; exit 2; }
[[ ! -e /opt/habnews && ! -e /var/lib/habnews && ! -e /etc/systemd/system/heranborsa-hermes-news.service ]] || { echo 'Target already exists; refusing overwrite.'; exit 2; }
if id heranborsa-hermes-news >/dev/null 2>&1; then echo 'OS user already exists; refusing adoption.'; exit 2; fi
if getent passwd 11001 >/dev/null; then echo 'UID 11001 already assigned; choose isolated UID and update manifest.'; exit 2; fi
useradd --system --uid 11001 --user-group --home-dir /var/lib/habnews --shell /usr/sbin/nologin heranborsa-hermes-news
install -d -m 0700 -o 11001 -g 11001 /opt/habnews /var/lib/habnews
package_dir="$(cd "$(dirname "$0")/.." && pwd)"
# Deliberate allowlist: do not copy .env, test state, secrets, old repo or local sessions.
for name in habnews schemas deploy tests reports sources.yaml pyproject.toml README.md RUNBOOK.md ISOLATION.md SOURCE_VALIDATION.md ACCEPTANCE.md COSTS.md .env.example .dockerignore .gitignore; do
  cp -R "$package_dir/$name" /opt/habnews/
done
install -d -m 0700 -o 11001 -g 11001 /opt/habnews/private /opt/habnews/state /opt/habnews/state/{data,jobs,auth,broker,control}
chown -R 11001:11001 /opt/habnews
install -m 0644 /opt/habnews/deploy/heranborsa-hermes-news.service /etc/systemd/system/heranborsa-hermes-news.service
# Daemon reload registers the new unit; it does not restart any existing service.
systemctl daemon-reload
cd /opt/habnews
printf '%s\n' '{"enabled":false}' > state/control/runtime-state.json
chown 11001:11001 state/control/runtime-state.json
chmod 0600 state/control/runtime-state.json
docker compose -f deploy/compose.yaml config --quiet
echo 'Files installed. No service started/enabled. Complete new-bot, OAuth, model/source/isolation acceptance in RUNBOOK.md.'
