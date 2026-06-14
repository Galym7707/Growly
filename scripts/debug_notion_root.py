from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.notion_service import NotionService
from app.utils.errors import NotionServiceError
from app.utils.logging import configure_logging, redact


def plain_text(rich_text: list[dict[str, Any]] | None) -> str:
    return "".join(
        str(item.get("plain_text") or item.get("text", {}).get("content") or "")
        for item in rich_text or []
    ).strip()


def object_title(item: dict[str, Any]) -> str:
    object_type = item.get("object")
    if object_type in {"database", "data_source"}:
        return plain_text(item.get("title")) or "(untitled)"

    properties = item.get("properties") or {}
    for property_value in properties.values():
        if property_value.get("type") == "title":
            return plain_text(property_value.get("title")) or "(untitled)"
    return "(untitled)"


def safe_error(error: NotionServiceError) -> str:
    return str(redact(error.safe_details()))


async def try_object(
    label: str,
    operation: Any,
) -> bool:
    try:
        result = await operation
        print(f"{label}: accessible")
        print(f"  object={result.get('object', 'unknown')}")
        print(f"  id={result.get('id', 'unknown')}")
        return True
    except NotionServiceError as exc:
        print(f"{label}: inaccessible")
        print(f"  {safe_error(exc)}")
        return False


async def main() -> int:
    configure_logging()
    settings = get_settings()
    root_id = settings.require_text("notion_root_page_id", "NOTION_ROOT_PAGE_ID")
    service = NotionService(settings)

    print("Searching all pages and databases accessible to the Notion integration...")
    try:
        objects = await service.search_accessible_objects()
    except NotionServiceError as exc:
        print(f"Notion search failed: {safe_error(exc)}")
        return 1

    if not objects:
        print("No accessible pages or databases were returned by Notion search.")
    else:
        print(f"Accessible objects: {len(objects)}")
        for item in objects:
            print(f"- title={object_title(item)}")
            print(f"  object={item.get('object', 'unknown')}")
            print(f"  id={item.get('id', 'unknown')}")

    print("\nChecking configured NOTION_ROOT_PAGE_ID...")
    page_accessible = await try_object(
        "Retrieve as page", service.retrieve_page(root_id)
    )
    await try_object("Retrieve as database", service.retrieve_database(root_id))

    accessible_pages = [item for item in objects if item.get("object") == "page"]
    if page_accessible:
        print("\nConfigured NOTION_ROOT_PAGE_ID is an accessible page.")
    elif accessible_pages:
        candidate = accessible_pages[0]
        print("\nUse this in .env:")
        print(f"NOTION_ROOT_PAGE_ID={candidate['id']}")
        print(f"Suggested page title: {object_title(candidate)}")
    else:
        print(
            "\nNo accessible page can be suggested. Share a Notion page with the "
            "integration, then run this script again."
        )
    return 0 if page_accessible else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
