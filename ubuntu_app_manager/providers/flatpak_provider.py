from __future__ import annotations

import subprocess
from pathlib import Path

from ubuntu_app_manager.domain.models.application import AppStatus, Application, SourceType
from ubuntu_app_manager.providers.base import BaseProvider


class FlatpakProvider(BaseProvider):
    name = "FLATPAK"

    def can_handle(self) -> bool:
        return Path("/usr/bin/flatpak").exists()

    def discover(self) -> list[Application]:
        if not self.can_handle():
            return []
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application,name,version,origin"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return []

        apps: list[Application] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p for p in line.split("\t") if p]
            if len(parts) < 4:
                continue
            app_id, name, version, origin = parts[:4]
            app = Application(
                id=f"flatpak:{app_id}",
                name=name,
                display_name=name,
                source_type=SourceType.FLATPAK,
                application_id=app_id,
                package_name=app_id,
                version=version,
                publisher=origin,
                status=AppStatus.INSTALLED,
                capabilities={"can_launch", "can_update", "can_remove"},
                metadata={"origin": origin, "exec": f"flatpak run {app_id}"},
            )
            apps.append(app)
        return apps

    def get_details(self, identifier: str) -> Application | None:
        for app in self.discover():
            if app.id == identifier or app.application_id == identifier:
                return app
        return None
