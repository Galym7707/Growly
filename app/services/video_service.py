"""Orchestration for pay-per-video AI generation.

Blotato and Replicate are the two AI-video providers. Blotato generation is
handled by :class:`SocialPublishingService`; this service adds the Replicate
provider, which is gated by a credit balance ("pay, then receive"):

* a credit is *reserved* (atomically deducted) before a Replicate prediction
  starts, so a user with no credits cannot generate;
* the credit is *settled* (kept) when the video is delivered;
* the credit is *refunded* exactly once if the provider ultimately fails.

Credits are granted by the frontend Polar webhook when a credit-pack order is
paid, keyed on the same workspace id the backend consumes them with.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import Settings, get_settings
from app.database import session_scope
from app.repositories.video_credits_repo import VideoCreditsRepository
from app.services.replicate_service import (
    DONE_STATUS,
    FAILED_STATUSES,
    ReplicateService,
)
from app.services.social_publishing_service import SocialPublishingService
from app.utils.errors import InsufficientCreditsError, ReplicateServiceError

logger = logging.getLogger(__name__)


class VideoGenerationService:
    def __init__(
        self,
        settings: Settings | None = None,
        replicate: ReplicateService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.replicate = replicate or ReplicateService(self.settings)

    # -- providers / credits ----------------------------------------------

    async def providers_status(self, workspace_id: str | None) -> dict[str, Any]:
        blotato = await SocialPublishingService(self.settings).blotato_status(
            workspace_id
        )
        balance = await asyncio.to_thread(self._balance, workspace_id)
        return {
            "blotato": {"enabled": bool(blotato.get("enabled"))},
            "replicate": {"enabled": self.replicate.is_enabled()},
            "credits": {
                "balance": balance,
                "video_cost": self.settings.replicate_video_credit_cost,
            },
        }

    async def credits_status(self, workspace_id: str | None) -> dict[str, Any]:
        balance = await asyncio.to_thread(self._balance, workspace_id)
        return {
            "balance": balance,
            "video_cost": self.settings.replicate_video_credit_cost,
        }

    def _balance(self, workspace_id: str | None) -> int:
        with session_scope() as session:
            return VideoCreditsRepository(session).get_balance(
                _workspace_key(workspace_id)
            )

    async def add_credits(self, workspace_id: str | None, amount: int) -> int:
        return await asyncio.to_thread(self._add_credits, workspace_id, amount)

    def _add_credits(self, workspace_id: str | None, amount: int) -> int:
        with session_scope() as session:
            return VideoCreditsRepository(session).add_credits(
                _workspace_key(workspace_id), amount
            )

    # -- replicate generation ---------------------------------------------

    async def start_replicate_video(
        self,
        workspace_id: str | None,
        *,
        kind: str,
        prompt: str,
    ) -> dict[str, Any]:
        workspace = _workspace_key(workspace_id)
        cost = self.settings.replicate_video_credit_cost

        # Reserve first: a user without enough credits never reaches Replicate.
        reserved = await asyncio.to_thread(self._reserve, workspace, cost)
        if not reserved:
            balance = await asyncio.to_thread(self._balance, workspace_id)
            raise InsufficientCreditsError(balance=balance, required=cost)

        try:
            visual = await self.replicate.create_prediction(kind=kind, prompt=prompt)
        except Exception:
            # Creation never started a paid job -> return the reserved credit.
            await asyncio.to_thread(self._refund, workspace, cost)
            raise

        await asyncio.to_thread(
            self._record_generation,
            workspace,
            kind,
            visual,
            cost,
        )

        # A prediction that fails instantly is refunded right away.
        if visual["status"] in FAILED_STATUSES and visual.get("id"):
            await asyncio.to_thread(
                self._refund_generation, workspace, str(visual["id"]), cost
            )
        return self._public(visual)

    async def replicate_video_status(
        self, workspace_id: str | None, prediction_id: str
    ) -> dict[str, Any]:
        visual = await self.replicate.get_prediction(prediction_id)
        workspace = _workspace_key(workspace_id)
        if visual["status"] in FAILED_STATUSES:
            await asyncio.to_thread(
                self._refund_generation,
                workspace,
                prediction_id,
                self.settings.replicate_video_credit_cost,
            )
        elif visual["status"] == DONE_STATUS:
            await asyncio.to_thread(self._settle, workspace, prediction_id)
        return self._public(visual)

    @staticmethod
    def _public(visual: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": visual.get("id"),
            "status": visual.get("status"),
            "media_urls": visual.get("media_urls", []),
        }

    # -- credit/generation persistence ------------------------------------

    def _reserve(self, workspace: str, cost: int) -> bool:
        with session_scope() as session:
            return VideoCreditsRepository(session).try_reserve(workspace, cost)

    def _refund(self, workspace: str, cost: int) -> None:
        with session_scope() as session:
            VideoCreditsRepository(session).refund(workspace, cost)

    def _record_generation(
        self,
        workspace: str,
        kind: str,
        visual: dict[str, Any],
        cost: int,
    ) -> None:
        with session_scope() as session:
            VideoCreditsRepository(session).create_generation(
                workspace_id=workspace,
                provider="replicate",
                kind=kind,
                prediction_id=(str(visual["id"]) if visual.get("id") else None),
                status=str(visual.get("status") or "starting"),
                credits_charged=cost,
            )

    def _refund_generation(
        self, workspace: str, prediction_id: str, cost: int
    ) -> None:
        with session_scope() as session:
            repo = VideoCreditsRepository(session)
            generation = repo.get_by_prediction(workspace, prediction_id)
            if generation is None:
                return
            repo.mark_status(generation, "failed")
            if repo.mark_refunded(generation):
                repo.refund(workspace, generation.credits_charged or cost)

    def _settle(self, workspace: str, prediction_id: str) -> None:
        with session_scope() as session:
            repo = VideoCreditsRepository(session)
            generation = repo.get_by_prediction(workspace, prediction_id)
            if generation is not None and generation.status != DONE_STATUS:
                repo.mark_status(generation, DONE_STATUS)


def _workspace_key(workspace_id: str | None) -> str:
    value = (workspace_id or "").strip()
    return value or "default"
