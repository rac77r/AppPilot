from __future__ import annotations

from typing import Iterable

from ubuntu_app_manager.domain.models.application import Application
from ubuntu_app_manager.providers.apt_provider import AptProvider
from ubuntu_app_manager.providers.appimage_provider import AppImageProvider
from ubuntu_app_manager.providers.desktop_provider import DesktopProvider
from ubuntu_app_manager.providers.flatpak_provider import FlatpakProvider
from ubuntu_app_manager.providers.snap_provider import SnapProvider


class InventoryService:
    """Aggregates system state from provider adapters while keeping the OS authoritative."""

    def __init__(self) -> None:
        self.providers = [
            AptProvider(),
            SnapProvider(),
            FlatpakProvider(),
            AppImageProvider(),
            DesktopProvider(),
        ]

    def discover(self) -> list[Application]:
        discovered: list[Application] = []
        for provider in self.providers:
            if not provider.can_handle():
                continue
            discovered.extend(provider.discover())
        return self._deduplicate(discovered)

    def _deduplicate(self, apps: Iterable[Application]) -> list[Application]:
        seen: set[str] = set()
        deduped: list[Application] = []
        for app in apps:
            key = f"{app.source_type}:{app.id}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(app)
        return deduped
