from __future__ import annotations

import json
import re
from typing import Any


def truncate(value: str | None, limit: int = 1900) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def split_telegram_text(value: str, limit: int = 3900) -> list[str]:
    text = value.strip()
    if not text:
        return [""]
    chunks: list[str] = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = text.rfind(" ", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text:
        chunks.append(text)
    return chunks


def strip_code_fence(value: str) -> str:
    text = value.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    return match.group(1).strip() if match else text


def parse_json_response(value: str) -> Any:
    """Parse an AI JSON reply, tolerating code fences and surrounding prose.

    Truncated or malformed output raises AIServiceError (reason
    "invalid_response") instead of a bare JSONDecodeError, so pipelines
    report a readable failure and can retry the generation.
    """
    from app.utils.errors import AIServiceError

    text = strip_code_fence(value)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        start_candidates = [index for index in (text.find("{"), text.find("[")) if index >= 0]
        if not start_candidates:
            raise AIServiceError(
                "The AI response was not valid JSON.",
                reason="invalid_response",
            ) from exc
        start = min(start_candidates)
        end = max(text.rfind("}"), text.rfind("]"))
        if end <= start:
            raise AIServiceError(
                "The AI response was not valid JSON.",
                reason="invalid_response",
            ) from exc
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError as inner:
            raise AIServiceError(
                "The AI response was not valid JSON (likely truncated).",
                reason="invalid_response",
            ) from inner

