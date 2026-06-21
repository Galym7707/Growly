from __future__ import annotations

import run_space


def test_prepare_database_runs_idempotent_migration(monkeypatch) -> None:
    calls: list[bool] = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://configured")
    monkeypatch.delenv("RUN_DATABASE_MIGRATIONS", raising=False)
    monkeypatch.setattr(run_space, "initialize_database", lambda: calls.append(True) or 0)

    run_space.prepare_database()

    assert calls == [True]


def test_prepare_database_can_be_disabled(monkeypatch) -> None:
    calls: list[bool] = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://configured")
    monkeypatch.setenv("RUN_DATABASE_MIGRATIONS", "false")
    monkeypatch.setattr(run_space, "initialize_database", lambda: calls.append(True) or 0)

    run_space.prepare_database()

    assert calls == []
