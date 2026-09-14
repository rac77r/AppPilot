from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class SourceType(str, Enum):
    APT = "APT"
    SNAP = "SNAP"
    FLATPAK = "FLATPAK"
    APPIMAGE = "APPIMAGE"
    DESKTOP = "DESKTOP"
    UNKNOWN = "UNKNOWN"


class AppStatus(str, Enum):
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    UPDATE_AVAILABLE = "update_available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass
class Application:
    id: str
    name: str
    display_name: str
    source_type: SourceType = SourceType.UNKNOWN
    package_name: Optional[str] = None
    application_id: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    architecture: Optional[str] = None
    size: Optional[int] = None
    publisher: Optional[str] = None
    install_date: Optional[datetime] = None
    executable_path: Optional[str] = None
    desktop_file: Optional[str] = None
    icon: Optional[str] = None
    status: AppStatus = AppStatus.INSTALLED
    capabilities: set[str] = field(default_factory=set)
    permissions: list[Any] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_capability(self, name: str) -> None:
        self.capabilities.add(name)

    def has_capability(self, name: str) -> bool:
        return name in self.capabilities

    def package_ref(self) -> str:
        if self.application_id:
            return self.application_id
        if self.package_name:
            return self.package_name
        return self.name
