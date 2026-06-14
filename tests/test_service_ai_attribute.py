from types import SimpleNamespace

from app.services.draft_service import DraftService


def test_draft_service_exposes_ai_attribute() -> None:
    sentinel = SimpleNamespace(name="ai")
    svc = DraftService(settings=SimpleNamespace(), ai=sentinel, notion=SimpleNamespace())
    assert svc.ai is sentinel
