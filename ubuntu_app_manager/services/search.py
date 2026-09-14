from __future__ import annotations

from ubuntu_app_manager.domain.models.application import Application
from ubuntu_app_manager.services.inventory import InventoryService


def _normalize(value: object) -> str:
    return " ".join(str(value or "").casefold().replace("_", " ").replace("-", " ").split())


class SearchService:
    def __init__(self, inventory: InventoryService | None = None) -> None:
        self.inventory = inventory or InventoryService()

    def search(self, query: str, apps: list[Application] | None = None) -> list[Application]:
        source_apps = apps if apps is not None else self.inventory.discover()
        if not query or not query.strip():
            return list(source_apps)

        needle = _normalize(query)
        results: list[Application] = []
        for app in source_apps:
            haystack_parts = [
                app.name or "",
                app.display_name or "",
                app.package_name or "",
                app.application_id or "",
                app.source_type.value if app.source_type else "",
                app.description or "",
                app.publisher or "",
            ]
            haystack = " ".join(_normalize(part) for part in haystack_parts)
            if needle in haystack:
                results.append(app)
        return results
