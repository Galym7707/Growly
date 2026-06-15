---
title: Growly
sdk: docker
app_port: 7860
---

# Growly

Growly is an AI-powered content factory, marketing intelligence, and approval
workflow for businesses. It monitors curated competitor and reference sources,
collects public market evidence through Tavily, builds content plans, and
generates drafts through GitHub Models with Groq fallback. Drafts can be
reviewed in Telegram or on the web before publishing, while technical state is
stored in Supabase PostgreSQL and client-facing data is synchronized to Notion.

The repository contains the Python backend, Telegram bot, and a Next.js web
application. Both interfaces call the same Python services; AI, search, and
Notion logic is not duplicated in React.

## Interface languages

The website and Telegram bot support Russian, English, and Kazakh.

- The website switcher is available on the landing page, login page, and in the
  workspace sidebar. The choice is stored in `localStorage` and a
  `growly_locale` cookie.
- In Telegram, use `/language` or open `Settings` and choose `Language`. The
  choice is stored per chat in the `settings` table under
  `telegram_language:<chat_id>`.
- Existing reports, drafts, and other generated content remain in the language
  in which they were created. The switcher localizes the product interface and
  system controls.

## Architecture

```text
Next.js web app ----\
                     > FastAPI web adapter -> shared Python services
Telegram bot -------/                         |
                                               +-- Tavily public search
                                               +-- GitHub Models primary AI
                                               +-- Groq fallback AI
                                               +-- Notion workspace
                                               +-- Supabase PostgreSQL

APScheduler -> optional weekly report and planning jobs
```

Main modules:

- `app/bot`: Telegram commands, conversations, menus, and callbacks.
- `app/web_api.py`: authenticated JSON adapter used by the website.
- `app/services`: shared AI, search, reporting, draft, and Notion logic.
- `app/repositories`: transactional SQLAlchemy data access.
- `app/source_collectors`: manual-first source collection architecture.
- `app/integrations`: reserved Instagram, Bitrix24, ERPNext, and CRM adapters.
- `frontend`: Next.js 16, React 19, Supabase Auth, responsive dashboard, and
  server-side proxy to FastAPI.
- `migrations/init.sql`: idempotent PostgreSQL schema initialization.

## Frontend Audit

The repository did not contain the static files named in the original frontend
brief: `index.html`, `style.css`, `script.js`, `api/waitlist.js`, `package.json`,
or `vercel.json`. There was no mock dashboard to retain or remove.

The implemented frontend is therefore a new Next.js application connected to the
existing backend. It retains the Growly name, Russian-first product language,
Python services, Supabase database, Telegram bot, and Notion synchronization.

The visual system uses:

- warm neutral background and white working surfaces;
- black text and muted gray secondary text;
- restrained borders and one deep green accent;
- system typography and inline SVG icons;
- real API data or explicit empty states.

It contains no emoji UI, purple/pink gradients, fake business metrics, countdown
blocks, or decorative AI effects.

## Requirements

- Python 3.12+
- Node.js 22+
- Supabase PostgreSQL and a database connection string
- Telegram bot token
- GitHub token with `models:read`
- Groq API key for fallback generation
- Tavily API key
- Notion integration with access to the configured root page

## Setup

1. Create and activate a Python environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

2. Install web dependencies:

   ```powershell
   npm install
   ```

3. Keep backend secrets in the root `.env`. Use `.env.example` only as a list
   of variable names.

4. Create `frontend/.env.local` from `frontend/.env.example`.

5. Use the same random value for backend `GROWLY_WEB_API_KEY` and frontend
   server-only `GROWLY_API_KEY`.

6. Share `NOTION_ROOT_PAGE_ID` with the configured Notion integration.

7. Initialize PostgreSQL:

   ```powershell
   python scripts/init_db.py
   ```

8. Verify external connections:

   ```powershell
   python scripts/test_connections.py
   ```

9. Create or reuse the Notion workspace:

   ```powershell
   python scripts/init_notion.py
   ```

## Environment Variables

Backend variables are documented in `.env.example`.

Required for the complete workflow:

| Variable | Purpose |
| --- | --- |
| `TELEGRAM_BOT_API_KEY` | Telegram bot token |
| `GITHUB_MODELS_TOKEN` | GitHub Models token |
| `GITHUB_MODELS_MODEL` | Primary model ID |
| `GROQ_API_KEY` | Fallback AI key |
| `GROQ_MODEL` | Fallback model |
| `TAVILY_API_KEY` | Public web search |
| `DATABASE_URL` | PostgreSQL connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_PUBLISHABLE_API_KEY` | Supabase publishable key |
| `SUPABASE_SECRET_API_KEY` | Backend Supabase secret key |
| `NOTION_API_KEY` | Notion integration token |
| `NOTION_ROOT_PAGE_ID` | Shared parent page |
| `GROWLY_WEB_API_KEY` | Server-to-server web API key |

Important optional backend variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `WEB_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated browser origins |
| `TELEGRAM_PUBLISH_CHAT_ID` | empty | Preferred Telegram publication target |
| `SCHEDULER_ENABLED` | `false` | Enables weekly jobs |
| `TIMEZONE` | `Asia/Almaty` | Scheduler timezone |
| `SEARCH_MAX_RESULTS` | `10` | Tavily results per query |

Frontend variables are documented in `frontend/.env.example`:

| Variable | Visibility | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_GROWLY_API_URL` | public | FastAPI origin |
| `NEXT_PUBLIC_SUPABASE_URL` | public | Supabase project URL for Auth |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | public | Publishable/anon key for Auth |
| `NEXT_PUBLIC_AUTH_REQUIRED` | public | Protect workspace routes when `true` |
| `GROWLY_API_KEY` | server only | Sent to FastAPI as `X-Growly-API-Key` |

Never expose service-role, Notion, Telegram, GitHub Models, Groq, Tavily, or
`GROWLY_API_KEY` values with a `NEXT_PUBLIC_` prefix.

## Run Locally

Start FastAPI:

```powershell
python run_api.py
```

It listens on `http://localhost:8000`.

Start Next.js in another terminal:

```powershell
npm run dev
```

Open `http://localhost:3000`.

Start the Telegram bot separately:

```powershell
python run_bot.py
```

## Web Routes

- `/`: public landing page
- `/login`: Supabase password login or explicit local mode
- `/dashboard`: workspace overview
- `/chat`: command-style interface over backend actions
- `/market-scan`: market scan workflow
- `/reports`: report list
- `/reports/[id]`: structured report view
- `/content-plan`: weekly plan and draft generation
- `/drafts`: approval, regeneration, and Notion sync
- `/sources`: manual sources, discovery, and monitoring
- `/settings`: business profile
- `/tg`: mobile entry prepared for a future Telegram Mini App

## Web API

Operational endpoints:

- `GET /health`
- `GET /ready`

Website endpoints:

- `GET /api/health`
- `GET /api/dashboard`
- `POST /api/market-scan`
- `POST /api/competitor-report`
- `GET|POST /api/content-plan`
- `POST /api/content-plan/{id}/draft`
- `POST /api/create-post`
- `GET /api/drafts`
- `PATCH /api/drafts/{id}`
- `GET /api/reports`
- `GET /api/reports/{id}`
- `GET|POST /api/sources`
- `POST /api/sources/discover`
- `POST /api/sources/monitor`
- `POST /api/notion/sync`
- `GET|PATCH /api/settings`
- `POST /api/chat`

When `GROWLY_WEB_API_KEY` is set, all `/api/*` routes require the matching
`X-Growly-API-Key` header. The browser never receives this secret. The Next.js
route handler reads server-only `GROWLY_API_KEY` and adds the header.

## Notion

`python scripts/init_notion.py` creates or reuses:

- Growly Dashboard
- Sources
- Content Calendar
- Drafts
- Reports
- Source Items
- Reviews and Market Insights
- Publications
- Integration Status

Web actions call the backend:

- reports use `POST /api/notion/sync` with target `report`;
- drafts use the same endpoint with target `draft`;
- the dashboard/chat can sync recent data with target `recent`.

The Notion token never enters the frontend. Supabase remains the source of truth;
Notion is the presentation and workflow layer.

## Telegram Bot

Management commands remain private-chat only. Existing commands include:

- `/create_post`, `/create_case`
- `/add_source`, `/sources`, `/disable_source`
- `/import_source_items`, `/discover_sources`, `/monitor_sources`
- `/web_search`, `/market_scan`, `/retry_analysis`, `/status`
- `/content_plan`, `/generate_from_plan`
- `/competitor_report`, `/review_analysis`, `/performance_report`
- `/drafts`, `/reports`, `/sync_notion`
- `/update_publication_metrics`, `/new_business`

Web implementation does not change Telegram handlers. Both interfaces reuse the
same services.

## Data Policy

Growly supports Tavily public search and manually supplied evidence. It does not
bypass captchas, access private accounts, automate unauthorized logins, or claim
complete Instagram, TikTok, YouTube, or Telegram collection.

Market scan saves public result URLs and snippets before AI analysis. Reports
retain evidence URLs and explicitly show missing data or limitations.

## Testing

Backend:

```powershell
python -m pytest
python -m compileall app scripts tests run_api.py run_bot.py
```

Frontend:

```powershell
npm run lint
npm run build
npm run test:web
npm audit --omit=dev
```

The frontend tests check:

- structured competitor report normalization from mock JSON;
- no emoji glyphs in UI source;
- no purple/pink decorative gradients;
- no public environment names for server credentials.

Live backend verification:

```powershell
python scripts/test_connections.py
```

The script checks environment loading, PostgreSQL, GitHub Models, Groq, Telegram,
and Notion without printing credentials.

## Vercel

1. Import `galym7707/growly` into Vercel.
2. Keep the repository root as the project root.
3. `vercel.json` runs the npm workspace build and outputs `frontend/.next`.
4. Add all variables from `frontend/.env.example`.
5. Set `NEXT_PUBLIC_GROWLY_API_URL` to the deployed FastAPI origin.
6. Set server-only `GROWLY_API_KEY` to the backend `GROWLY_WEB_API_KEY`.
7. Add the Vercel origin to backend `WEB_ALLOWED_ORIGINS`.

The backend remains a separate Python deployment. Vercel hosts the Next.js app.

## Telegram Mini App Later

The `/tg` route is mobile-first and uses normal web authentication today. A future
Mini App integration must:

1. receive Telegram `initData`;
2. send it to the backend;
3. validate the signature and freshness on the server;
4. map the verified Telegram user to a Growly workspace;
5. never trust `initDataUnsafe` directly.

## Current Limitations

- The database schema is single-workspace. Supabase Auth protects the web session,
  but true multi-company isolation requires `workspace_id` on all business tables
  and enforcement in repositories or PostgreSQL RLS.
- Long web operations are synchronous HTTP requests. The UI shows a pending state,
  but streaming progress and resumable web jobs are not implemented.
- Instagram publishing is not implemented and must use an official API.
- Bitrix24, ERPNext, and CRM adapters are disabled placeholders.
- Telegram publication metrics are not collected automatically.
- Telegram Mini App server validation is not enabled yet.

## Repository

Remote:

```text
https://github.com/Galym7707/Growly
```

Before publishing:

```powershell
git status
git check-ignore .env
python -m pytest
npm run lint
npm run build
npm run test:web
```

Never force-add `.env` or paste credentials into logs, issues, or commits.
