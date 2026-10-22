# ENDEKS HABER Mini App

Private, read-only editorial panel. **No Telegram update handlers, webhooks, AI calls, publishing endpoints or production database writes.** Existing news/KAP/Hermes services remain unchanged.

## Components

- `public/`: mobile timeline, KAP/news/draft tabs, topic/date/state/search filters, device-local read/bookmark flags, tweet copy and authenticated image preview.
- `src/miniapp/worker.ts`: a separate Cloudflare Worker with its own private R2 bucket. Owner Telegram initData HMAC validation (one-hour TTL); no public data/image endpoint. A separate sync credential accepts bounded snapshots/PNG uploads. Fourteen-day media cleanup only touches this bucket.
- `scripts/panel_snapshot.ts`: opens existing databases with SQLite **readOnly=true** and checks their application IDs. Exports allowlisted fields; never exports credentials, raw evidence, model prompts or internal errors. Up to 750 records per source family (news/KAP/drafts), last seven days. UI explicitly flags truncation. Source cards already represented by a draft are collapsed by URL.
- `scripts/panel_sync.ts`: separate process; pushes snapshots about every 30 seconds. At most twelve new images each pass, so initial image warmup may take several minutes. No inbound ports/tunnel on the Mac. Independent health file. Missing sync leaves last snapshot visible with a stale-data warning.
- `scripts/install_panel.py`: stages a self-contained release, npm-ci/typechecks, verifies first sync, then activates **only** `com.endekshaber.panel`. Existing owner chat menu is saved before replacing it with a Mini App button. Global bot settings and getUpdates/webhook remain untouched.

## Deploy / enable

From `sector/`: `npx wrangler deploy --config miniapp/wrangler.toml`.
Secrets are `BOT_TOKEN`, `OWNER_ID`, `SYNC_TOKEN`; populate through Wrangler secret input, never in Git. The local private file `~/Library/Application Support/sector-haber/miniapp/config.json` contains the HTTPS panel URL and matching sync token (0600).

`python3 scripts/install_panel.py` validates and enables sync plus the owner-only menu. It does not start another Telegram consumer. News production, editing and X publication continue in the existing Telegram cards, including the same 20-per-day quota; the panel only displays a snapshot of that counter.

## Rollback

`python3 scripts/install_panel.py --disable` restores the saved owner chat menu, stops/removes only the panel LaunchAgent, then disables the panel's cloud data/UI through its authenticated switch. Does not delete news/KAP data, queues, media or credentials. The dedicated cloud bucket is retained for recovery. Re-running installation enables the panel again. Main news/KAP services do not need a restart.

Cloud-only emergency disable: deploy this separate Worker with `--var ENABLED:false`. Never deploy the production `wrangler.toml` to undo this panel.

Tests: `npm run check`, `npm test`, `python3 -m unittest discover -s test -p 'test_panel_install.py'`; dry-run: `npx wrangler deploy --config miniapp/wrangler.toml --dry-run`. Local visual fixtures live only under `/tmp`, not in the deployed bundle.
