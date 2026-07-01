from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import VideoCredit, VideoGeneration


class VideoCreditsRepository:
    """Data access for AI-video credit balances and generation records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # -- balance -----------------------------------------------------------

    def get_balance(self, workspace_id: str) -> int:
        row = self.session.scalar(
            select(VideoCredit).where(VideoCredit.workspace_id == workspace_id)
        )
        return int(row.balance) if row is not None else 0

    def add_credits(self, workspace_id: str, amount: int) -> int:
        """Add (or, with a negative amount, remove) credits. Returns balance."""
        if amount == 0:
            return self.get_balance(workspace_id)
        row = self.session.scalar(
            select(VideoCredit).where(VideoCredit.workspace_id == workspace_id)
        )
        if row is None:
            row = VideoCredit(workspace_id=workspace_id, balance=max(0, amount))
            self.session.add(row)
            self.session.flush()
            return int(row.balance)
        row.balance = max(0, int(row.balance) + amount)
        self.session.flush()
        return int(row.balance)

    def try_reserve(self, workspace_id: str, amount: int = 1) -> bool:
        """Atomically decrement the balance if it covers ``amount``.

        Returns ``True`` when the reservation succeeds. The conditional UPDATE
        means concurrent generations can never drive the balance negative.
        """
        if amount <= 0:
            return True
        result = self.session.execute(
            update(VideoCredit)
            .where(
                VideoCredit.workspace_id == workspace_id,
                VideoCredit.balance >= amount,
            )
            .values(balance=VideoCredit.balance - amount)
        )
        return bool(result.rowcount)

    def refund(self, workspace_id: str, amount: int) -> None:
        if amount <= 0:
            return
        self.add_credits(workspace_id, amount)

    # -- generations -------------------------------------------------------

    def create_generation(
        self,
        *,
        workspace_id: str,
        provider: str,
        kind: str,
        prediction_id: str | None,
        status: str,
        credits_charged: int,
    ) -> VideoGeneration:
        generation = VideoGeneration(
            workspace_id=workspace_id,
            provider=provider,
            kind=kind,
            prediction_id=prediction_id,
            status=status,
            credits_charged=credits_charged,
            refunded=False,
        )
        self.session.add(generation)
        self.session.flush()
        return generation

    def get_by_prediction(
        self, workspace_id: str, prediction_id: str
    ) -> VideoGeneration | None:
        return self.session.scalar(
            select(VideoGeneration).where(
                VideoGeneration.workspace_id == workspace_id,
                VideoGeneration.prediction_id == prediction_id,
            )
        )

    def mark_status(
        self, generation: VideoGeneration, status: str
    ) -> VideoGeneration:
        generation.status = status
        self.session.flush()
        return generation

    def mark_refunded(self, generation: VideoGeneration) -> bool:
        """Flag a generation as refunded exactly once.

        Returns ``True`` only for the first caller, so the credit is returned a
        single time even if several status polls observe the same failure.
        """
        if generation.refunded:
            return False
        generation.refunded = True
        self.session.flush()
        return True
