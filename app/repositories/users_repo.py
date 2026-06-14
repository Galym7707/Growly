from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UsersRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_chat_id(self, telegram_chat_id: str) -> User | None:
        return self.session.scalar(
            select(User).where(User.telegram_chat_id == telegram_chat_id)
        )

    def upsert_telegram_user(
        self,
        telegram_chat_id: str,
        telegram_username: str | None,
        full_name: str | None,
    ) -> User:
        user = self.get_by_chat_id(telegram_chat_id)
        if user is None:
            user = User(
                telegram_chat_id=telegram_chat_id,
                telegram_username=telegram_username,
                full_name=full_name,
            )
            self.session.add(user)
        else:
            user.telegram_username = telegram_username
            user.full_name = full_name
            user.is_active = True
        self.session.flush()
        return user

