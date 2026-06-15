from app.models import Publication


def test_publication_has_scheduled_for_column() -> None:
    assert "scheduled_for" in Publication.__table__.columns
