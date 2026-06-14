from datetime import UTC, datetime

from telegram import Bot, Chat, Message, MessageEntity, Update, User

from app.bot.bot import build_application
from app.config import Settings


def command_update(command: str, chat_type: str) -> Update:
    chat_id = 12345 if chat_type == "private" else -10012345
    message = Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=chat_id, type=chat_type, title="Growly_Test_group"),
        from_user=User(id=77, first_name="Tester", is_bot=False),
        text=command,
        entities=[
            MessageEntity(
                type=MessageEntity.BOT_COMMAND,
                offset=0,
                length=len(command),
            )
        ],
    )
    bot = Bot(token="123:test-token")
    bot._bot_user = User(  # type: ignore[attr-defined]
        id=123,
        first_name="Growly",
        is_bot=True,
        username="GrowlyBot",
    )
    message.set_bot(bot)
    return Update(update_id=1, message=message)


def command_handler(application: object, callback_name: str) -> object:
    for handlers in application.handlers.values():  # type: ignore[attr-defined]
        for handler in handlers:
            callback = getattr(handler, "callback", None)
            if getattr(callback, "__name__", "") == callback_name:
                return handler
    raise AssertionError(f"Handler {callback_name} was not found.")


def any_handler_matches(application: object, update: Update) -> bool:
    return any(
        bool(handler.check_update(update))
        for handlers in application.handlers.values()  # type: ignore[attr-defined]
        for handler in handlers
    )


def test_start_matches_private_but_not_supergroup() -> None:
    application = build_application(
        Settings(_env_file=None, TELEGRAM_BOT_API_KEY="123:test-token")
    )
    handler = command_handler(application, "start")
    assert handler.check_update(command_update("/start", "private"))
    assert not handler.check_update(command_update("/start", "supergroup"))


def test_removed_commands_match_no_handler() -> None:
    application = build_application(
        Settings(_env_file=None, TELEGRAM_BOT_API_KEY="123:test-token")
    )
    for command in ("menu", "chat_id"):
        assert not any_handler_matches(
            application,
            command_update(f"/{command}", "private"),
        )
        assert not any_handler_matches(
            application,
            command_update(f"/{command}", "supergroup"),
        )


def test_all_management_commands_are_private_only() -> None:
    application = build_application(
        Settings(_env_file=None, TELEGRAM_BOT_API_KEY="123:test-token")
    )
    commands = (
        "start",
        "add_source",
        "sources",
        "disable_source",
        "import_source_items",
        "discover_sources",
        "monitor_sources",
        "web_search",
        "market_scan",
        "retry_analysis",
        "status",
        "debug_notion_status",
        "create_post",
        "create_case",
        "content_plan",
        "generate_from_plan",
        "competitor_report",
        "review_analysis",
        "update_publication_metrics",
        "performance_report",
        "drafts",
        "reports",
        "sync_notion",
        "new_business",
        "help",
        "cancel",
    )
    for command in commands:
        assert any_handler_matches(application, command_update(f"/{command}", "private"))
        assert not any_handler_matches(
            application, command_update(f"/{command}", "supergroup")
        )


def test_polling_retries_transient_bootstrap_failures(
    monkeypatch: object,
) -> None:
    from app.bot import bot

    captured: dict[str, object] = {}

    class FakeApplication:
        def run_polling(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(  # type: ignore[union-attr]
        bot,
        "build_application",
        lambda: FakeApplication(),
    )

    bot.run_bot()

    assert captured["bootstrap_retries"] == -1
    assert captured["timeout"] == 30
