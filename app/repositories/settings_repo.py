from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Setting


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _scoped_key(key: str, workspace_id: str | None = None) -> str:
        if workspace_id is None:
            return key
        return f"workspace:{workspace_id}:{key}"

    def get(self, key: str, workspace_id: str | None = None) -> str | None:
        scoped_key = self._scoped_key(key, workspace_id)
        setting = self.session.scalar(select(Setting).where(Setting.key == scoped_key))
        return setting.value if setting else None

    def set(
        self, key: str, value: str | None, workspace_id: str | None = None
    ) -> Setting:
        scoped_key = self._scoped_key(key, workspace_id)
        setting = self.session.scalar(select(Setting).where(Setting.key == scoped_key))
        if setting is None:
            setting = Setting(key=scoped_key, value=value, workspace_id=workspace_id)
            self.session.add(setting)
        else:
            setting.value = value
            setting.workspace_id = workspace_id
        self.session.flush()
        return setting

    def get_many(
        self, keys: list[str], workspace_id: str | None = None
    ) -> dict[str, str | None]:
        scoped_keys = {
            self._scoped_key(key, workspace_id): key
            for key in keys
        }
        rows = self.session.scalars(
            select(Setting).where(Setting.key.in_(scoped_keys))
        )
        result = {scoped_keys[row.key]: row.value for row in rows}
        return {key: result.get(key) for key in keys}
