from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Setting


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: str) -> str | None:
        setting = self.session.scalar(select(Setting).where(Setting.key == key))
        return setting.value if setting else None

    def set(self, key: str, value: str | None) -> Setting:
        setting = self.session.scalar(select(Setting).where(Setting.key == key))
        if setting is None:
            setting = Setting(key=key, value=value)
            self.session.add(setting)
        else:
            setting.value = value
        self.session.flush()
        return setting

    def get_many(self, keys: list[str]) -> dict[str, str | None]:
        rows = self.session.scalars(select(Setting).where(Setting.key.in_(keys)))
        result = {row.key: row.value for row in rows}
        return {key: result.get(key) for key in keys}

