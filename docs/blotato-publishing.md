# Blotato social publishing

Growly publishes to social networks (Instagram, Threads, TikTok, YouTube Shorts,
Facebook, LinkedIn, X/Twitter, and any other platform returned by Blotato)
through **Blotato**. Telegram continues to publish through the Telegram Bot API,
and Notion sync is unchanged.

## Architecture

- The **frontend never** calls Blotato and never sees `BLOTATO_API_KEY`.
- The **backend** is the single source of business logic and the only caller of
  the Blotato API (`blotato-api-key` request header).
- **n8n** triggers backend endpoints; it never calls Blotato directly.
- Publication status is persisted in Supabase (`publications`, `social_accounts`,
  `publication_targets`, `integrations`, `manual_publish_packages`).

## Required environment variables

### Hugging Face Space (backend secrets)

Add these as **Secrets** on the Space (Settings → Variables and secrets).
They are backend-only and must never be added to Vercel.

| Secret | Required | Notes |
| --- | --- | --- |
| `BLOTATO_ENABLED` | yes | `true` to enable auto-publishing |
| `BLOTATO_API_KEY` | yes | Blotato API key (secret) |
| `BLOTATO_BASE_URL` | optional | defaults to `https://backend.blotato.com/v2` |
| `BLOTATO_INSTAGRAM_ACCOUNT_ID` | optional | fallback account id |
| `BLOTATO_THREADS_ACCOUNT_ID` | optional | fallback account id |
| `BLOTATO_TIKTOK_ACCOUNT_ID` | optional | fallback account id |
| `BLOTATO_YOUTUBE_ACCOUNT_ID` | optional | fallback account id |
| `BLOTATO_FACEBOOK_ACCOUNT_ID` | optional | fallback account id |
| `BLOTATO_FACEBOOK_PAGE_ID` | optional | fallback page id |
| `BLOTATO_LINKEDIN_ACCOUNT_ID` | optional | fallback account id |
| `BLOTATO_LINKEDIN_PAGE_ID` | optional | fallback page id |
| `BLOTATO_X_ACCOUNT_ID` | optional | fallback account id |

Also required (already used by Growly): `GROWLY_WEB_API_KEY`, `DATABASE_URL`.

### Vercel (frontend)

| Variable | Notes |
| --- | --- |
| `NEXT_PUBLIC_GROWLY_API_URL` | backend base URL (Hugging Face Space) |
| `GROWLY_API_KEY` | server-only proxy key (matches `GROWLY_WEB_API_KEY`) |

Do **not** add `BLOTATO_API_KEY` to Vercel.

## Backend endpoints

All require the Growly web API key header (`X-Growly-API-Key`) and resolve the
workspace from `X-Growly-Workspace-Id` (defaults to `default`).

| Method & path | Purpose |
| --- | --- |
| `GET /api/integrations/status` | Telegram / Notion / Blotato status |
| `GET /api/integrations/blotato/status` | safe Blotato status (no key) |
| `GET /api/integrations/blotato/accounts` | connected accounts (safe) |
| `POST /api/integrations/blotato/test` | test connection |
| `GET /api/integrations/blotato/mappings` | saved platform→account mappings |
| `POST /api/integrations/blotato/mappings` | save mappings |
| `GET /api/drafts/{id}` | draft detail |
| `POST /api/drafts/{id}/publish-blotato` | publish draft now/scheduled |
| `POST /api/drafts/{id}/schedule-blotato` | schedule draft |
| `POST /api/drafts/{id}/manual-package` | manual package for platforms |
| `POST /api/content-items/{id}/create-manual-package` | manual package (alias) |
| `GET /api/publications/{id}/status` | publication status (Supabase + Blotato) |

The API key is never returned and never logged.

## Operating Growly

1. **Test the connection** — Settings → Integrations → Blotato → *Проверить подключение*.
2. **Refresh accounts** — *Обновить аккаунты* pulls connected accounts from Blotato.
3. **Map accounts** — Settings → Integrations → *Настроить публикацию*: choose which
   Blotato account each platform uses, then *Сохранить сопоставление*.
4. **Publish a draft** — open a draft (`/drafts/{id}`), select platforms, choose
   *Опубликовать сейчас* and press the button.
5. **Schedule a draft** — choose *Запланировать*, pick a date/time, press the button.
6. **Manual package** — choose *Пакет для ручной публикации*; Growly adapts the
   draft per platform and saves it, even when Blotato is not connected.

### Automatic vs manual platforms

- **Automatic (Blotato):** Instagram, Threads, TikTok, YouTube Shorts, Facebook,
  LinkedIn, X/Twitter, and any platform returned by the Blotato accounts API —
  only when an account is connected and mapped.
- **Telegram:** published via the Telegram Bot API (not Blotato).
- **Not connected:** Growly generates a manual publishing package instead.

## n8n integration

n8n calls the backend, not Blotato. The backend remains the source of truth and
records every publication.

### n8n environment

| Variable | Value |
| --- | --- |
| `GROWLY_API_URL` | backend base URL (Hugging Face Space) |
| `GROWLY_WEB_API_KEY` | the Growly web API key |

### Workflow

1. **Trigger** — approved draft or scheduled publishing task.
2. **HTTP Request** node →
   `POST {{$env.GROWLY_API_URL}}/api/drafts/{{ $json.draft_id }}/publish-blotato`
   - Header: `X-Growly-API-Key: {{$env.GROWLY_WEB_API_KEY}}`
   - Header: `Content-Type: application/json`
   - Body:
     ```json
     {
       "platforms": ["instagram", "threads"],
       "publish_now": true,
       "scheduled_time": null,
       "media_urls": [],
       "language": "ru"
     }
     ```
3. The backend calls Blotato and stores publication status in Supabase.
4. n8n receives the response:
   ```json
   {
     "status": "submitted",
     "publication_ids": ["..."],
     "blotato_submissions": [
       {"platform": "instagram", "post_submission_id": "...", "status": "submitted"}
     ]
   }
   ```
5. **Log the run.** To poll status later, call
   `GET {{$env.GROWLY_API_URL}}/api/publications/{{ id }}/status`.

### Retry & error handling

- Per-platform failures are returned in `blotato_submissions` with
  `status: "failed"` and a safe `error` message (no secrets); other platforms in
  the same request still succeed.
- For transient provider errors, configure the n8n HTTP node to retry, or re-call
  the publish endpoint — each call records a fresh publication row.
- If Blotato is disabled the endpoint returns a friendly Russian error; fall back
  to `POST /api/drafts/{id}/manual-package`.
