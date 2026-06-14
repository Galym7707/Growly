from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
from sqlalchemy import text

from app.config import Settings, get_settings
from app.database import session_scope
from app.services.github_models_service import GitHubModelsService
from app.services.notion_service import NotionService
from app.utils.errors import NotionServiceError
from app.utils.logging import configure_logging, redact


def check_environment(settings: Settings) -> None:
    settings.database_dsn()
    settings.github_models_key()
    settings.require_text("github_models_model", "GITHUB_MODELS_MODEL")
    settings.require_text("ai_primary_provider", "AI_PRIMARY_PROVIDER")
    settings.require_text("ai_fallback_provider", "AI_FALLBACK_PROVIDER")
    settings.groq_key()
    settings.require_text("groq_model", "GROQ_MODEL")
    settings.telegram_token()
    settings.notion_token()
    settings.require_text("notion_root_page_id", "NOTION_ROOT_PAGE_ID")
    settings.require_text("search_provider", "SEARCH_PROVIDER")
    settings.tavily_key()


def check_database() -> None:
    with session_scope() as session:
        session.execute(text("SELECT 1"))


async def check_groq(settings: Settings) -> None:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.require_text("groq_model", "GROQ_MODEL"),
                "messages": [
                    {
                        "role": "user",
                        "content": "Connection test. Reply with the single word OK.",
                    }
                ],
                "temperature": 0,
                "max_tokens": 5,
            },
        )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("choices", [{}])[0].get("message", {}).get("content"):
        raise RuntimeError("Groq returned no response.")


async def check_github_models(settings: Settings) -> None:
    content = await GitHubModelsService(settings).generate_text(
        "connection_test.md",
        {"check": "GitHub Models connectivity"},
        temperature=0,
        max_tokens=8,
    )
    if content.strip().upper() != "OK":
        raise RuntimeError("GitHub Models returned an unexpected response.")


async def check_telegram(settings: Settings) -> None:
    token = settings.telegram_token()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"https://api.telegram.org/bot{token}/getMe")
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError("Telegram getMe did not return ok=true.")


async def check_notion_api(settings: Settings) -> None:
    await NotionService(settings).check_connection()


async def check_notion_root(settings: Settings) -> None:
    await NotionService(settings).check_access()


async def main() -> int:
    configure_logging()
    settings = get_settings()
    results: list[tuple[str, bool, str | None]] = []

    checks = [
        ("Environment", lambda: asyncio.to_thread(check_environment, settings)),
        ("PostgreSQL", lambda: asyncio.to_thread(check_database)),
        ("GitHub Models primary", lambda: check_github_models(settings)),
        ("Groq fallback", lambda: check_groq(settings)),
        ("Telegram", lambda: check_telegram(settings)),
        ("Notion API", lambda: check_notion_api(settings)),
        ("Notion root page", lambda: check_notion_root(settings)),
    ]
    for name, check in checks:
        try:
            await check()
            results.append((name, True, None))
        except NotionServiceError as exc:
            results.append((name, False, str(redact(exc.safe_details()))))
        except Exception as exc:
            results.append((name, False, type(exc).__name__))

    for name, passed, error_details in results:
        if passed:
            print(f"PASS: {name}")
        else:
            print(
                f"FAIL: {name} ({error_details}). "
                "No secret value was printed; inspect configuration and service access."
            )
    return 0 if all(passed for _, passed, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
