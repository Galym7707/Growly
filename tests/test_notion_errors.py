from app.utils.errors import NotionServiceError


def test_notion_error_exposes_safe_structured_details() -> None:
    error = NotionServiceError(
        "Request failed.",
        status=404,
        code="object_not_found",
        notion_message="Could not find page.",
    )
    assert error.safe_details() == (
        "status=404 code=object_not_found message=Could not find page."
    )
