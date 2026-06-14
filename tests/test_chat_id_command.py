from app.bot.handlers import GROUP_BOT_COMMANDS, PRIVATE_BOT_COMMANDS


def test_private_command_list_contains_management_commands() -> None:
    commands = {command.command for command in PRIVATE_BOT_COMMANDS}
    assert {
        "start",
        "create_post",
        "create_case",
        "content_plan",
        "discover_sources",
        "monitor_sources",
        "web_search",
        "market_scan",
        "retry_analysis",
        "status",
        "competitor_report",
        "review_analysis",
        "drafts",
        "reports",
        "sync_notion",
        "new_business",
        "help",
        "cancel",
    } <= commands
    assert "menu" not in commands
    assert "chat_id" not in commands


def test_group_command_list_is_empty() -> None:
    assert GROUP_BOT_COMMANDS == []
