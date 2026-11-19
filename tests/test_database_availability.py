from __future__ import annotations

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, TimeoutError as PoolTimeout

from app import database_lifecycle
from app.main import app


@pytest.mark.asyncio
async def test_migration_outage_retries_then_recovers_without_restarting(monkeypatch, caplog):
    calls = []

    def migrate():
        calls.append(True)
        if len(calls) == 1:
            raise RuntimeError("postgresql://user:private-password@db.invalid/db")

    monkeypatch.setattr(database_lifecycle, "apply_migrations", migrate)
    monkeypatch.setattr(database_lifecycle, "DATABASE_RETRY_SECONDS", 0)
    runtime = FastAPI()
    runtime.state.database_initializing = True
    await asyncio.wait_for(database_lifecycle.initialize_database(runtime), timeout=2)
    assert len(calls) == 2
    assert runtime.state.database_initializing is False
    assert "private-password" not in caplog.text


@pytest.mark.asyncio
async def test_lifespan_serves_health_before_schema_is_ready_and_cancels_on_shutdown(monkeypatch):
    monkeypatch.setenv("RUN_DATABASE_MIGRATIONS", "true")
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def initialize(runtime):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    monkeypatch.setattr(database_lifecycle, "initialize_database", initialize)
    async with database_lifecycle.database_lifespan(app):
        await asyncio.wait_for(started.wait(), timeout=2)
        client = TestClient(app)
        assert client.get("/health").status_code == 200
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["database"] == "initializing"
        assert client.get("/api/dashboard").status_code == 503
    assert stopped.is_set()
    assert app.state.database_initializing is False


@pytest.mark.parametrize("error", [
    OperationalError("SELECT 1", {}, RuntimeError("private-password")),
    PoolTimeout("private-password"),
])
def test_database_outage_is_retryable_and_recovers_on_next_request(monkeypatch, error, caplog):
    calls = []

    @contextmanager
    def scope():
        calls.append(True)
        if len(calls) == 1:
            raise error
        yield SimpleNamespace(execute=lambda statement: None)

    monkeypatch.setattr("app.main.session_scope", scope)
    client = TestClient(app)
    failed = client.get("/ready")
    assert failed.status_code == 503
    assert failed.headers["Retry-After"] == "10"
    assert failed.json()["code"] == "database_unavailable"
    assert "private-password" not in failed.text
    assert "private-password" not in caplog.text
    assert client.get("/ready").json() == {"status": "ready", "database": "connected"}


def test_readiness_does_not_hide_schema_errors(monkeypatch):
    from sqlalchemy.exc import ProgrammingError

    @contextmanager
    def scope():
        raise ProgrammingError("SELECT broken", {}, RuntimeError("missing table"))
        yield

    monkeypatch.setattr("app.main.session_scope", scope)
    response = TestClient(app, raise_server_exceptions=False).get("/ready")
    assert response.status_code == 500
