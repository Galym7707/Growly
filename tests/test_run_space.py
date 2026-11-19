from __future__ import annotations

import os

import run_space


def test_space_enables_background_migrations(monkeypatch) -> None:
    calls = []
    monkeypatch.delenv("RUN_DATABASE_MIGRATIONS", raising=False)
    monkeypatch.setattr(run_space.uvicorn, "run", lambda *a, **kw: calls.append((a, kw)))

    run_space.run_web_server()

    assert os.environ["RUN_DATABASE_MIGRATIONS"] == "true"
    assert calls[0][0] == ("app.main:app",)


def test_space_preserves_migration_opt_out(monkeypatch) -> None:
    monkeypatch.setenv("RUN_DATABASE_MIGRATIONS", "false")
    monkeypatch.setattr(run_space.uvicorn, "run", lambda *a, **kw: None)

    run_space.run_web_server()

    assert os.environ["RUN_DATABASE_MIGRATIONS"] == "false"
