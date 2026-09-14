from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PermissionState(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        labels = {
            PermissionState.ALLOWED: "Allowed",
            PermissionState.DENIED: "Denied",
            PermissionState.UNKNOWN: "Unknown",
        }
        return labels[self]


@dataclass
class Permission:
    name: str
    state: PermissionState = PermissionState.UNKNOWN
    details: str = ""
