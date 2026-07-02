from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg

CONNECT_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5
# Pooled connections (Supabase/pgbouncer) enforce a statement_timeout that the
# large init.sql batch can exceed (QueryCanceled). Lift the timeouts for the
# migration batch itself; prepended to each script so it applies inside the
# same implicit transaction.
SESSION_SETUP_SQL = (
    "SET statement_timeout = 0;\n"
    "SET lock_timeout = 0;\n"
    "SET idle_in_transaction_session_timeout = 0;\n"
)

from app.config import get_settings
from app.models import Base
from app.utils.logging import configure_logging

EXPECTED_SCHEMA = {
    table.name: frozenset(column.name for column in table.columns)
    for table in Base.metadata.sorted_tables
}
REQUIRED_USERS_COLUMNS = set(EXPECTED_SCHEMA["users"])


def migration_paths() -> list[Path]:
    migrations_dir = ROOT / "migrations"
    init_path = migrations_dir / "init.sql"
    extra_paths = sorted(
        path
        for path in migrations_dir.glob("*.sql")
        if path.name != "init.sql"
    )
    return [init_path, *extra_paths]


def verify_schema(cursor: psycopg.Cursor) -> None:
    cursor.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = ANY(%s)
        ORDER BY table_name, ordinal_position
        """,
        (list(EXPECTED_SCHEMA),),
    )
    actual_schema = {table_name: set() for table_name in EXPECTED_SCHEMA}
    for table_name, column_name in cursor.fetchall():
        actual_schema[str(table_name)].add(str(column_name))

    failures: list[str] = []
    for table_name in sorted(EXPECTED_SCHEMA):
        missing_columns = EXPECTED_SCHEMA[table_name] - actual_schema[table_name]
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            print(f"FAIL: schema {table_name} missing columns: {missing}")
            failures.append(f"{table_name}: {missing}")
        else:
            print(f"PASS: schema {table_name}")

    if failures:
        raise RuntimeError("Schema verification failed for: " + "; ".join(failures))


def apply_migrations() -> None:
    with psycopg.connect(
        get_settings().database_dsn(),
        autocommit=True,
        connect_timeout=30,
    ) as connection:
        with connection.cursor() as cursor:
            for path in migration_paths():
                cursor.execute(
                    SESSION_SETUP_SQL + path.read_text(encoding="utf-8"),
                    prepare=False,
                )
                print(f"Applied migration: {path.name}")
            verify_schema(cursor)


def main() -> int:
    configure_logging()
    sql_path = ROOT / "migrations" / "init.sql"
    if not sql_path.is_file():
        print("ERROR: migrations/init.sql was not found.")
        return 1
    last_error: str = "unknown"
    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        try:
            apply_migrations()
            print(
                "Database initialization completed. All SQLAlchemy tables and "
                "columns are ready."
            )
            return 0
        except Exception as exc:
            last_error = type(exc).__name__
            print(
                f"WARNING: database initialization attempt {attempt}/"
                f"{CONNECT_ATTEMPTS} failed ({last_error}). "
                "Secret values were not printed."
            )
            if attempt < CONNECT_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
    print(
        "ERROR: database initialization failed "
        f"({last_error}). Secret values were not printed."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
