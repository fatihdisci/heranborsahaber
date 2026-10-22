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

## Publication assistant

The panel now displays the shared publication ledger: manual declarations plus successful API receipts, Istanbul daily totals, last publication time, and ready/published/deferred filters. Manual declarations do not consume the 20 API reservations. Snapshot fields remain backwards compatible. Panel buttons open owner-authenticated Telegram deep links for mark/undo/defer/time correction; the cloud Worker still has no database mutation or publishing endpoint. A panel action requires opening/starting the editor bot; allow roughly 30 seconds for the next sync. Manual declarations are not independently verified X publications.

Telegram card controls: 🔗 source, 📋 copy, ✏️ edit, 🎨 redesign, 🚀 API publish, ✅ manual declaration, ⏸ defer, 📊 history/cadence. Published manual items offer 🕒 time correction and ↩️ undo. `/yayinlar` shows overall counts and the separate API budget. Deferring never schedules an automatic publication. Native Telegram copy buttons cannot also trigger a callback; use 📊 for guidance before copying. Historical manual X posts are not silently backfilled.

Rollback: restore the prior news and panel releases plus the previous Worker version. Keep the additive publication tables; no destructive down migration is required. API receipts stay in their original ledger.

The report-aligned advisory uses 45–75 minutes for routine posts and 60–90 for substantial tables, plus daily total guidance at 8/12/16/20 and a lighter weekend plan. These are editorial experiment ranges, never algorithm thresholds; no new hard cap, automatic publishing, reminder job, or paid X read calls. `/yayinplani` returns the plan; `/yayinraporu` downloads 28 days of recorded publications as UTF-8 CSV. Missing analytics/manual post URLs and unassigned experiment/urgency fields stay blank. CSV metadata is explicitly the current draft, not an immutable copy of the historical X post; validate against the post before evaluating outcomes. Unrecorded manual posts are absent. Spreadsheet formula prefixes are escaped.
