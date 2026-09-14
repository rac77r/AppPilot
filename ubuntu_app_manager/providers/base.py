from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    def discover(self) -> list[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_details(self, identifier: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def can_handle(self) -> bool:
        raise NotImplementedError
