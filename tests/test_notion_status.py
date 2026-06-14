from app.services.notion_service import _status_label


def test_published_status_is_client_friendly() -> None:
    assert _status_label("published") == "Published"
