from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ubuntu_app_manager.domain.models.application import AppStatus, Application, SourceType
from ubuntu_app_manager.domain.models.permissions import Permission, PermissionState
from ubuntu_app_manager.providers.base import BaseProvider


class AptProvider(BaseProvider):
    name = "APT"

    def can_handle(self) -> bool:
        return Path("/usr/bin/apt").exists()

    def discover(self) -> list[Application]:
        if not self.can_handle():
            return []
        try:
            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Architecture}\t${Status}\n"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return []

        apps: list[Application] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            name, version, arch, status = parts[:4]
            if "installed" not in status.lower():
                continue
            app = Application(
                id=f"apt:{name}",
                name=name,
                display_name=name,
                source_type=SourceType.APT,
                package_name=name,
                version=version,
                architecture=arch,
                status=AppStatus.INSTALLED,
                capabilities={"can_launch", "can_update", "can_remove"},
                permissions=[Permission("Package Management", PermissionState.ALLOWED, "Native apt/dpkg package manager")],
                metadata={"status": status},
            )
            apps.append(app)
        return apps

    def get_details(self, identifier: str) -> Application | None:
        for app in self.discover():
            if app.id == identifier or app.package_name == identifier:
                return app
        return None

    def install(self, package_name: str) -> None:
        subprocess.run(["apt", "install", "-y", package_name], check=True)

    def remove(self, package_name: str) -> None:
        subprocess.run(["apt", "remove", "-y", package_name], check=True)
