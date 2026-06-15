from app.integrations.bitrix.client import anonymize_deal


def test_anonymize_strips_names_and_hides_amount_without_consent() -> None:
    payload = {
        "deal_id": "42",
        "category": "Недвижимость",
        "city": "Алматы",
        "asset_type": "Квартира",
        "result": "Обмен на авто + доплата",
        "amount": 5000000,
        "client_name": "Иван Петров",
        "publish_amount": False,
    }
    clean = anonymize_deal(payload)
    assert "client_name" not in clean
    assert clean["amount"] is None
    assert clean["category"] == "Недвижимость"
    assert clean["asset_type"] == "Квартира"


def test_anonymize_keeps_amount_with_consent() -> None:
    clean = anonymize_deal({"amount": 100, "publish_amount": True})
    assert clean["amount"] == 100
