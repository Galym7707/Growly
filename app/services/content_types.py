from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContentTypeSpec:
    key: str
    label: str
    prompt_name: str
    aliases: tuple[str, ...]


CONTENT_TYPES = (
    ContentTypeSpec(
        key="promo_post",
        label="Promo post",
        prompt_name="promo_post.md",
        aliases=(
            "promo post",
            "promo_post",
            "promotional post",
            "sales post",
            "рекламный пост",
        ),
    ),
    ContentTypeSpec(
        key="pain_point_post",
        label="Pain-point post",
        prompt_name="pain_point_post.md",
        aliases=(
            "pain-point post",
            "pain point post",
            "pain_point_post",
            "болевой пост",
            "пост о боли",
        ),
    ),
    ContentTypeSpec(
        key="asset_post",
        label="Asset post",
        prompt_name="asset_post.md",
        aliases=(
            "asset post",
            "asset/product post",
            "product post",
            "asset_post",
            "продуктовый пост",
            "пост о продукте",
        ),
    ),
    ContentTypeSpec(
        key="case_post",
        label="Client result post",
        prompt_name="case_post.md",
        aliases=(
            "client result post",
            "result story",
            "пост о результате клиента",
            "case post",
            "case_post",
            "кейс",
            "пост-кейс",
            "история результата",
        ),
    ),
    ContentTypeSpec(
        key="educational_post",
        label="Educational post",
        prompt_name="educational_post.md",
        aliases=(
            "educational post",
            "educational_post",
            "обучающий пост",
            "образовательный пост",
            "экспертный пост",
        ),
    ),
    ContentTypeSpec(
        key="faq_post",
        label="FAQ post",
        prompt_name="faq_post.md",
        aliases=(
            "faq post",
            "faq_post",
            "frequently asked questions",
            "questions and answers",
            "faq-пост",
        ),
    ),
    ContentTypeSpec(
        key="news_post",
        label="News post",
        prompt_name="news_post.md",
        aliases=(
            "news post",
            "news_post",
            "announcement post",
            "company news",
            "новостной пост",
        ),
    ),
    ContentTypeSpec(
        key="comparison_post",
        label="Comparison post",
        prompt_name="comparison_post.md",
        aliases=(
            "comparison post",
            "comparison_post",
            "сравнительный пост",
            "пост-сравнение",
        ),
    ),
    ContentTypeSpec(
        key="weekly_digest",
        label="Weekly digest",
        prompt_name="weekly_digest.md",
        aliases=(
            "weekly digest",
            "weekly_digest",
            "недельный дайджест",
            "еженедельный дайджест",
            "дайджест",
        ),
    ),
    ContentTypeSpec(
        key="reels_shorts_script",
        label="Reels/Shorts script",
        prompt_name="reels_shorts_script.md",
        aliases=(
            "reels/shorts script",
            "reels script",
            "shorts script",
            "reels_shorts_script",
            "сценарий reels",
            "сценарий shorts",
            "сценарий короткого видео",
        ),
    ),
    ContentTypeSpec(
        key="whatsapp_template",
        label="WhatsApp template",
        prompt_name="whatsapp_template.md",
        aliases=(
            "whatsapp template",
            "whatsapp message",
            "whatsapp_template",
            "шаблон whatsapp",
            "сообщение whatsapp",
        ),
    ),
)

CONTENT_TYPE_BY_KEY = {spec.key: spec for spec in CONTENT_TYPES}


def _normalized(value: str) -> str:
    return re.sub(r"[\s_-]+", " ", value.strip().lower())


def normalize_content_type(
    value: str | None, *, default: str = "asset_post"
) -> ContentTypeSpec:
    clean = _normalized(value or "")
    for spec in CONTENT_TYPES:
        if clean == _normalized(spec.key) or clean == _normalized(spec.label):
            return spec
        if any(clean == _normalized(alias) for alias in spec.aliases):
            return spec
    return CONTENT_TYPE_BY_KEY[default]


def detect_content_type(brief: str, *, default: str = "asset_post") -> ContentTypeSpec:
    explicit = re.search(
        r"(?im)^\s*(?:тип\s+контента|content\s+type)\s*[:\-]\s*(.+?)\s*$",
        brief,
    )
    if explicit:
        return normalize_content_type(explicit.group(1), default=default)

    clean = _normalized(brief)
    for spec in CONTENT_TYPES:
        candidates = (spec.key, spec.label, *spec.aliases)
        if any(_normalized(candidate) in clean for candidate in candidates):
            return spec
    return CONTENT_TYPE_BY_KEY[default]


def content_type_label(value: str | None) -> str:
    spec = normalize_content_type(value)
    return {
        "promo_post": "Рекламный пост",
        "pain_point_post": "Пост о проблеме клиента",
        "asset_post": "Пост о продукте",
        "case_post": "Пост о результате клиента",
        "educational_post": "Обучающий пост",
        "faq_post": "FAQ-пост",
        "news_post": "Новостной пост",
        "comparison_post": "Сравнительный пост",
        "weekly_digest": "Недельный дайджест",
        "reels_shorts_script": "Сценарий короткого видео",
        "whatsapp_template": "Шаблон сообщения WhatsApp",
    }.get(spec.key, spec.label)
