from pathlib import Path

from scripts.init_db import EXPECTED_SCHEMA, REQUIRED_USERS_COLUMNS


ROOT = Path(__file__).resolve().parents[1]


def test_users_model_columns_are_required_by_schema_verification() -> None:
    assert REQUIRED_USERS_COLUMNS == {
        "id",
        "telegram_chat_id",
        "telegram_username",
        "full_name",
        "role",
        "is_active",
        "created_at",
        "updated_at",
    }


def test_users_repair_migration_is_idempotent() -> None:
    migration = (ROOT / "migrations" / "init.sql").read_text(encoding="utf-8")
    repair_columns = {
        "telegram_username": "text",
        "full_name": "text",
        "role": "text DEFAULT 'user'",
        "is_active": "boolean DEFAULT true",
        "created_at": "timestamptz DEFAULT now()",
        "updated_at": "timestamptz DEFAULT now()",
    }
    for column, definition in repair_columns.items():
        assert (
            f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} {definition};"
            in migration
        )


def test_every_sqlalchemy_column_has_idempotent_repair_statement() -> None:
    migration = (ROOT / "migrations" / "init.sql").read_text(encoding="utf-8")
    for table_name, columns in EXPECTED_SCHEMA.items():
        for column_name in columns:
            assert (
                f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} "
                in migration
            ), f"Missing repair for {table_name}.{column_name}"


def test_drafts_repair_contains_full_model_schema() -> None:
    assert EXPECTED_SCHEMA["drafts"] == {
        "id",
        "content_plan_id",
        "draft_type",
        "channel",
        "title",
        "draft_text",
        "version",
        "status",
        "approved_by",
        "telegram_message_id",
        "notion_page_id",
        "ai_model",
        "prompt_name",
        "original_context_json",
        "generation_metadata_json",
        "created_at",
        "updated_at",
    }


def test_market_scan_jobs_schema_tracks_long_tasks() -> None:
    assert EXPECTED_SCHEMA["market_scan_jobs"] == {
        "id",
        "user_id",
        "status",
        "current_step",
        "query",
        "sources_count",
        "report_id",
        "error_message",
        "created_at",
        "updated_at",
    }


def test_publications_have_duplicate_prevention_index() -> None:
    migration = (ROOT / "migrations" / "init.sql").read_text(encoding="utf-8")
    assert "CREATE UNIQUE INDEX uq_publications_draft_channel" in migration
    assert "HAVING count(*) > 1" in migration


def test_repair_migration_does_not_delete_existing_data() -> None:
    migration = (ROOT / "migrations" / "init.sql").read_text(encoding="utf-8")
    assert "DELETE FROM" not in migration.upper()
    assert "DROP TABLE" not in migration.upper()
