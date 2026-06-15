from app.services.ai_service import AIService
from app.services.groq_service import GroqService


def test_ai_service_is_not_a_groq_subclass() -> None:
    assert not issubclass(AIService, GroqService)
