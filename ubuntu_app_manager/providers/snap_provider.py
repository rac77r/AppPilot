from __future__ import annotations

import subprocess
from pathlib import Path

from ubuntu_app_manager.domain.models.application import AppStatus, Application, SourceType
from ubuntu_app_manager.providers.base import BaseProvider


class SnapProvider(BaseProvider):
    name = "SNAP"

    def can_handle(self) -> bool:
        return Path("/usr/bin/snap").exists() or Path("/snap").exists()

    def discover(self) -> list[Application]:
        if not self.can_handle():
            return []
        try:
            result = subprocess.run(
                ["snap", "list"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return []

        app_rows: list[Application] = []
        lines = result.stdout.strip().splitlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) < 5:
                continue
            name, version, revision, tracking, publisher = parts[:5]
            app = Application(
                id=f"snap:{name}",
                name=name,
                display_name=name,
                source_type=SourceType.SNAP,
                package_name=name,
                version=version,
                publisher=publisher,
                status=AppStatus.INSTALLED,
                capabilities={"can_launch", "can_update", "can_remove"},
                metadata={"revision": revision, "tracking": tracking, "exec": f"snap run {name}"},
            )
            app_rows.append(app)
        return app_rows

    def get_details(self, identifier: str) -> Application | None:
        for app in self.discover():
            if app.id == identifier or app.package_name == identifier:
                return app
        return None
