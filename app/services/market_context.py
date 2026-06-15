from __future__ import annotations

import re
from typing import Any

NEUTRAL_OFFER_EXAMPLE = (
    "Например: консультация, услуга, набор товаров, пробный тариф или акция недели."
)

_HEALTHY_FOOD_MARKERS = (
    "пп",
    "правильн",
    "здоров",
    "рацион",
    "питан",
    "meal prep",
    "healthy food",
)
_LANGUAGE_MARKERS = {
    "ru": ("русский", "русском", "russian", "ru"),
    "kk": ("казахский", "казахском", "қазақ", "kazakh", "kk"),
    "en": ("английский", "английском", "english", "en"),
}
_KNOWN_REGIONS = (
    "Алматы",
    "Астана",
    "Шымкент",
    "Караганда",
    "Казахстан",
)


def build_market_context(
    topic: str,
    region_language: str = "",
    *,
    report_id: int | None = None,
    source_item_ids: list[int] | None = None,
    source_urls: list[str] | None = None,
    sources_count: int = 0,
) -> dict[str, Any]:
    clean_topic = topic.strip()
    region = detect_region(clean_topic, region_language)
    return {
        "topic": clean_topic,
        "region": region,
        "language": detect_language(clean_topic, region_language),
        "category": detect_category(clean_topic),
        "category_code": detect_category_code(clean_topic),
        "region_language": region_language.strip(),
        "report_id": report_id,
        "source_item_ids": source_item_ids or [],
        "source_urls": source_urls or [],
        "sources_count": sources_count,
    }


def detect_category(topic: str) -> str:
    if detect_category_code(topic) == "healthy_food_delivery":
        return "доставка здорового и правильного питания"
    return topic.strip() or "продукт или услуга"


def detect_category_code(topic: str) -> str:
    lowered = topic.casefold()
    if any(marker in lowered for marker in _HEALTHY_FOOD_MARKERS):
        return "healthy_food_delivery"
    return "generic"


def detect_language(*values: str) -> str:
    text = " ".join(values).casefold()
    for language, markers in _LANGUAGE_MARKERS.items():
        if any(
            re.search(rf"(?<!\w){re.escape(marker)}(?!\w)", text)
            for marker in markers
        ):
            return language
    return "ru" if re.search(r"[а-яё]", text) else "en"


def detect_region(topic: str, region_language: str = "") -> str:
    combined = f"{topic} {region_language}".casefold()
    for region in _KNOWN_REGIONS:
        if region.casefold() in combined:
            return region

    cleaned = region_language
    for markers in _LANGUAGE_MARKERS.values():
        for marker in markers:
            cleaned = re.sub(
                rf"(?<!\w){re.escape(marker)}(?!\w)",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
    return re.sub(r"^[\s,;/|-]+|[\s,;/|-]+$", "", cleaned).strip()


def offer_prompt_example(market_context: dict[str, Any] | None) -> str:
    if not market_context or not str(market_context.get("topic") or "").strip():
        return NEUTRAL_OFFER_EXAMPLE

    if market_context.get("category_code") == "healthy_food_delivery":
        region = str(market_context.get("region") or "").strip()
        delivery_region = f" по {region}" if region else ""
        return "\n".join(
            [
                "Например:",
                f"- Рацион правильного питания на 7 дней с доставкой{delivery_region}",
                "- Пробный день ПП-питания со скидкой",
                "- Индивидуальное меню для похудения или набора массы",
            ]
        )

    topic = str(market_context["topic"]).strip()
    return (
        f"Например: основной продукт или услуга для ниши «{topic}», "
        "пробный тариф или акция недели."
    )


def market_topics_match(first: str | None, second: str | None) -> bool:
    left = _normalize_topic(first)
    right = _normalize_topic(second)
    if not left or not right:
        return left == right
    if left == right or left in right or right in left:
        return True

    left_category = detect_category_code(left)
    right_category = detect_category_code(right)
    if left_category != "generic" and left_category == right_category:
        left_region = detect_region(first or "")
        right_region = detect_region(second or "")
        return not left_region or not right_region or left_region == right_region

    left_tokens = _topic_tokens(left)
    right_tokens = _topic_tokens(right)
    overlap = left_tokens & right_tokens
    largest_topic = max(len(left_tokens), len(right_tokens))
    return bool(overlap) and len(overlap) / largest_topic >= 0.5


def _normalize_topic(value: str | None) -> str:
    return " ".join(re.findall(r"[\w]+", (value or "").casefold()))


def _topic_tokens(value: str) -> set[str]:
    return {
        token[:6]
        for token in value.split()
        if len(token) > 2 and token not in {"для", "или", "the", "and"}
    }
