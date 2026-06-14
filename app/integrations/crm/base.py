from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CRMClient(ABC):
    @abstractmethod
    async def create_lead(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError

