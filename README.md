---
title: Growly Telegram Bot
sdk: docker
app_port: 7860
---

# Growly

Growly is an AI-powered content factory, marketing intelligence, and approval
automation backend for businesses. It maintains a manually curated list of
competitor and reference sources, collects public market evidence from them
automatically via Tavily, builds content plans, generates drafts through GitHub
Models with Groq fallback, and routes every draft through human approval in
Telegram before publishing. It stores technical state in Supabase PostgreSQL and
presents client-facing data in Notion.

This version intentionally has no custom website, n8n workflow, or Google Sheets
dependency.

## Architecture

```text
AI generation: GitHub Models openai/gpt-5-mini primary, Groq fallback
Telegram bot ── commands, generation, approvals, report delivery
      │
      ├── Tavily ── public web search and source discovery
      ├── GitHub Models ── primary content and analysis generation
      ├── Groq ── fallback content and analysis generation
      ├── Notion ── dashboard and client-facing databases
      └── Supabase PostgreSQL ── source of truth and status history

FastAPI ── health and database readiness endpoints
APScheduler ── optional weekly report and planning jobs
```

Main modules:

- `app/bot`: Telegram commands, conversations, menus, and approval callbacks.
- `app/services`: AI routing, GitHub Models, Groq fallback, Notion, content
  planning, reports, reviews, and scheduling.
- `app/repositories`: transactional database access.
- `app/source_collectors`: manual-first source collection architecture.
- `app/integrations`: disabled future adapters for Instagram, Bitrix24, ERPNext, and CRM.
- `migrations/init.sql`: idempotent PostgreSQL schema initialization.

## Requirements

- Python 3.12+
- A Supabase PostgreSQL project and database connection string
- A Telegram bot token
- A GitHub token with `models:read` permission
- A Groq API key for fallback generation
- A Tavily API key
- A Notion integration with access to the configured root page

## Setup

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

2. Keep the existing root `.env` file. Do not commit it. Use `.env.example` only
   as a reference for variable names.

3. Share the Notion root page with the Notion integration configured by
   `NOTION_API_KEY`.

4. Initialize PostgreSQL:

   ```powershell
   python scripts/init_db.py
   ```

   The initializer is idempotent. It creates missing tables, repairs missing columns
   on existing legacy tables without deleting rows, and prints a schema `PASS` or
   `FAIL` result for every SQLAlchemy table.

5. Verify all connections:

   ```powershell
   python scripts/test_connections.py
   ```

6. Create or reuse the Notion workspace:

   ```powershell
   python scripts/init_notion.py
   ```

7. Optionally add clearly marked synthetic source data:

   ```powershell
   python scripts/seed_demo_data.py
   ```

## Environment Variables

Required for the complete workflow:

| Variable | Purpose |
| --- | --- |
| `APP_NAME` | Application name; use `Growly` |
| `ENVIRONMENT` | Runtime environment |
| `TELEGRAM_BOT_API_KEY` | Telegram bot token |
| `GITHUB_MODELS_TOKEN` | GitHub token with `models:read` permission |
| `GITHUB_MODELS_BASE_URL` | GitHub Models OpenAI-compatible endpoint |
| `GITHUB_MODELS_MODEL` | Primary GitHub Models model ID |
| `AI_PRIMARY_PROVIDER` | Primary provider; use `github_models` |
| `AI_FALLBACK_PROVIDER` | Fallback provider; use `groq` |
| `GROQ_API_KEY` | Groq fallback API key |
| `GROQ_MODEL` | Fallback model available to the Groq account |
| `SEARCH_PROVIDER` | Web search provider; use `tavily` |
| `TAVILY_API_KEY` | Tavily API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_PUBLISHABLE_API_KEY` | Supabase publishable key |
| `SUPABASE_SECRET_API_KEY` | Supabase secret key |
| `SUPABASE_DB_PASSWORD` | Supabase database password |
| `DATABASE_URL` | PostgreSQL connection string |
| `NOTION_API_KEY` | Notion integration token |
| `NOTION_ROOT_PAGE_ID` | Parent page shared with the integration |

Optional:

| Variable | Default | Purpose |
| --- | --- | --- |
| `TELEGRAM_PUBLISH_CHAT_ID` | empty | Preferred target group/supergroup/channel chat ID |
| `TELEGRAM_CHANNEL_ID` | empty | Legacy publishing target used as fallback |
| `INSTAGRAM_ENABLED` | `false` | Reserved official API adapter |
| `BITRIX_ENABLED` | `false` | Reserved Bitrix24 adapter |
| `ERPNEXT_ENABLED` | `false` | Reserved ERPNext adapter |
| `CRM_PROVIDER` | `none` | Reserved CRM selection |
| `SCHEDULER_ENABLED` | `false` | Enables weekly jobs |
| `WEEKLY_REPORT_DAY` | `monday` | Weekly scheduler day |
| `WEEKLY_REPORT_HOUR` | `9` | Scheduler hour |
| `WEEKLY_REPORT_MINUTE` | `0` | Scheduler minute |
| `TIMEZONE` | `Asia/Almaty` | Scheduler timezone |
| `SEARCH_MAX_RESULTS` | `10` | Tavily results per query |
| `SEARCH_DEPTH` | `basic` | Tavily search depth |
| `SEARCH_SAVE_RAW` | `true` | Store provider result JSON without secrets |

Missing required variables produce a clear variable-name error. Secret values are
represented by `SecretStr`, are redacted from structured logs, and are never printed
by the operational scripts.

## Notion Workspace

`python scripts/init_notion.py` checks access to `NOTION_ROOT_PAGE_ID`, then creates
or reuses:

- Growly Dashboard
- Sources
- Content Calendar
- Drafts
- Reports
- Source Items
- Reviews and Market Insights
- Publications
- Integration Status

The initializer is idempotent. It detects child pages/databases and stores Notion
database and data source IDs in the Supabase `settings` table.

## Run

Telegram bot:

```powershell
python run_bot.py
```

FastAPI:

```powershell
python run_api.py
```

API endpoints:

- `GET /health`: process health and environment name.
- `GET /ready`: verifies PostgreSQL with `SELECT 1`.

No frontend is served.

## Telegram Commands

Growly's management workflow is private-chat only. Subscribers in publishing groups
cannot invoke content generation, approvals, reports, or synchronization commands.

Private-chat commands:

- `/start`: register the Telegram user and show the menu.
- `/create_post`: collect a brief and generate an asset/product post.
- `/create_case`: create a client-result post from the starting situation,
  completed actions, and verified outcome; client/company names stay private
  unless explicitly approved for publication.
- `/add_source`: register a manual intelligence source and sync it to Notion.
- `/sources`: list active sources grouped by type and priority.
- `/disable_source`: disable a source by ID or exact name.
- `/import_source_items`: paste public/manual competitor materials for structured AI analysis.
- `/discover_sources`: find public candidate websites and platform profiles with Tavily and save them as `requires_review`.
- `/sources`: show sources grouped by platform type and review status, with approve/disable controls.
- `/monitor_sources`: search public information about active sources, save findings, and generate an AI summary.
- `/web_search`: search public web sources with Tavily and save them to Supabase and Notion.
- `/market_scan`: save Tavily evidence first, then analyze it through the AI router and save a report.
- `/retry_analysis`: retry AI analysis for the latest saved pending market scan.
- `/status`: show the latest Market Scan job step, saved-source count, report status, and last error.
- `/content_plan`: collect a weekly objective and create posts, videos, WhatsApp, and digest items.
- `/generate_from_plan`: generate a channel-specific draft from a draft plan item.
- `/competitor_report`: build an evidence-backed report from saved source items and market scans.
- `/review_analysis`: extract pains, objections, triggers, customer language, FAQ ideas, and risks.
- `/update_publication_metrics`: store views, reactions, comments, clicks, leads, and notes.
- `/performance_report`: generate the weekly performance report.
- `/drafts`: show pending drafts with approval controls.
- `/reports`: show recent reports.
- `/sync_notion`: force a recent-data sync.
- `/debug_notion_status`: hidden developer status for configured Notion IDs, recent database counts, and last sync counts.
- `/new_business`: confirm and clear the current business context before onboarding another business.
- `/help`: list commands.
- `/cancel`: stop the active input flow.

Management commands are ignored outside private chat. Group command menus are empty.

`/new_business` requires explicit inline confirmation. It hard-deletes business
sources, source items, reports, reviews, plans, drafts, approvals, publication rows,
and `business_*` settings from PostgreSQL, then archives linked Notion pages.
Telegram posts already sent to a publishing group, Telegram users, API keys, and
integration configuration are preserved.

Draft actions are `Approve`, `Regenerate`, `Reject`, and `Save to Notion`.
Approval happens only in private chat and does not publish automatically. After
approval, `Publish to Telegram Group` sends the complete approved text to
`TELEGRAM_PUBLISH_CHAT_ID`. If that variable is empty, Growly falls back to the
legacy `TELEGRAM_CHANNEL_ID`. Long text is split at safe Telegram message
boundaries. Publication rows are reused by draft and channel, so repeated callbacks
do not publish duplicates. Successful publishing changes the draft and publication
status to `published`, synchronizes the Notion status as `Published`, and confirms
success in the private chat.

When neither publishing variable is configured, approval only marks the draft as
approved and no publishing button is shown. Every approval action is recorded in
PostgreSQL.

## Data and Source Policy

Growly supports Tavily public web search and manual user-supplied evidence.
`/import_source_items` accepts pasted public posts, captions, links, observations,
metrics, comments, CSV/text exports, and other user-supplied evidence.
`/web_search` and `/market_scan` save public result URLs and snippets before AI
analysis so reports and content plans can cite their evidence.

Content Plan prompts use a bounded evidence context: at most eight direct source
items with 300-character snippets, eight evidence URLs, report summaries instead
of full report bodies, and no `raw_json`. Larger evidence sets are summarized in
batches of eight and persisted as `content_plan_source_summary` reports. If an AI provider
still rejects the payload with HTTP 413, generation retries with report summaries
only and Telegram states that detailed evidence was reduced.

Market Scan runs as a tracked background job. Progress is stored in
`market_scan_jobs` and exposed through `/status`; `/cancel` cancels the active
async task when possible. Tavily queries have a 30-second timeout, AI
generations have a 60-second timeout, and each Market Scan Notion operation has
a 30-second timeout.

Source discovery and monitoring do not claim full Instagram, TikTok, YouTube, or
Telegram collection. Tavily supplies public search evidence only. Full Telegram
post collection requires a separate public Telegram collector, and complete
YouTube Shorts metrics require the YouTube Data API. Growly does not access private
accounts, bypass captchas, or bypass platform limits.
The project does not bypass captchas, access private accounts, automate logins, or
perform unauthorized Instagram/TikTok scraping.

The competitor report distinguishes source metadata from collected source items.
When no source items exist, it states that recent competitor activity cannot be
confirmed.

## Scheduling

Weekly jobs are configured through APScheduler for:

- competitor report
- content plan
- content performance report

They remain disabled unless `SCHEDULER_ENABLED=true`. This prevents development
runs from triggering external API calls unexpectedly.

## Tests and Verification

Run local tests and syntax checks:

```powershell
pytest
pytest tests/test_ai_router.py
python -m compileall app scripts tests run_api.py run_bot.py
```

Run the rollback-safe MVP workflow checks:

```powershell
python scripts/qa_mvp.py
```

The QA script checks all 12 workflow stages without retaining temporary rows or
publishing a test post. An intentional real publication can be tested only with
`--live-publish-draft-id ID`.

Run live integration verification:

```powershell
python scripts/test_connections.py
```

The live script checks environment loading, PostgreSQL, minimal GitHub Models and
Groq completions, Telegram `getMe`, and access to the configured Notion root page.
It does not print credentials.

## Current Limitations

- Source ingestion is manual; automated collectors are intentionally disabled.
- Instagram publishing is not implemented. A future version must use an official API.
- Bitrix24 and ERPNext adapters are disabled placeholders.
- CRM support is a disabled provider interface.
- Telegram group publishing records message IDs but does not collect performance
  metrics automatically.
- Notion is a presentation and workflow layer; Supabase remains the source of truth.
- The API exposes operational health only and has no public business-data endpoints.

## GitHub

The local repository is configured for:

```text
https://github.com/Galym7707/Growly
```

Review before publishing:

```powershell
git status
git check-ignore .env
git add .
git status
git commit -m "Build Growly backend, bot, Notion sync, and database"
git push -u origin main
```

Never use `git add -f .env`, never paste credentials into issues or logs, and rotate
any secret that is accidentally exposed. This project does not push automatically.
