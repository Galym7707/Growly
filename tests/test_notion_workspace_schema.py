from app.services.notion_service import NotionService


def test_notion_workspace_contains_intelligence_databases_and_properties() -> None:
    specs = NotionService.database_specs
    assert {
        "Sources",
        "Source Items",
        "Content Calendar",
        "Drafts",
        "Reports",
        "Reviews and Market Insights",
        "Publications",
    } <= set(specs)
    assert {"Frequency", "Last Checked"} <= set(specs["Sources"])
    assert {
        "URL",
        "Provider",
        "Query",
        "Source Type",
        "Snippet",
        "AI Summary",
        "Topics",
        "Offers",
        "CTAs",
        "Pains",
        "Content Gaps",
        "Status",
        "Created At",
        "Topic",
        "Format",
        "Offer",
        "CTA",
        "Pain",
        "Hook",
        "Summary",
        "Source ID",
    } <= set(specs["Source Items"])
    assert {"CTA", "Source Idea", "Why Recommended"} <= set(
        specs["Content Calendar"]
    )
    assert {"Prompt", "AI Model", "Content Plan ID"} <= set(specs["Drafts"])
    assert {
        "Report Type",
        "Query",
        "Sources Count",
        "Summary",
        "Recommendations",
        "Created At",
    } <= set(specs["Reports"])
    assert {
        "Telegram Message ID",
        "Published At",
        "Views",
        "Reactions",
        "Comments",
        "Clicks",
        "Leads",
    } <= set(specs["Publications"])
