from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg

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


def main() -> int:
    configure_logging()
    sql_path = ROOT / "migrations" / "init.sql"
    if not sql_path.is_file():
        print("ERROR: migrations/init.sql was not found.")
        return 1
    try:
        with psycopg.connect(get_settings().database_dsn(), autocommit=True) as connection:
            with connection.cursor() as cursor:
                for path in migration_paths():
                    cursor.execute(path.read_text(encoding="utf-8"), prepare=False)
                    print(f"Applied migration: {path.name}")
                verify_schema(cursor)
        print(
            "Database initialization completed. All SQLAlchemy tables and columns "
            "are ready."
        )
        return 0
    except Exception as exc:
        print(
            "ERROR: database initialization failed "
            f"({type(exc).__name__}). Secret values were not printed."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
