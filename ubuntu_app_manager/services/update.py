from __future__ import annotations

import subprocess

from ubuntu_app_manager.domain.errors import InvalidPackage, UpdateFailed
from ubuntu_app_manager.security.validation import validate_flatpak_ref, validate_package_name


class UpdateService:
    def update_apt(self) -> None:
        subprocess.run(["apt", "update"], check=True)
        subprocess.run(["apt", "upgrade", "-y"], check=True)

    def update_apt_package(self, package_name: str) -> None:
        if not validate_package_name(package_name):
            raise InvalidPackage("Invalid APT package name")
        try:
            subprocess.run(["apt", "install", "--only-upgrade", "-y", package_name], check=True)
        except subprocess.CalledProcessError as exc:
            raise UpdateFailed(f"APT update failed: {exc}") from exc

    def update_flatpak(self) -> None:
        subprocess.run(["flatpak", "update", "-y"], check=True)

    def update_flatpak_package(self, ref: str) -> None:
        if not validate_flatpak_ref(ref):
            raise InvalidPackage("Invalid Flatpak reference")
        try:
            subprocess.run(["flatpak", "update", "-y", ref], check=True)
        except subprocess.CalledProcessError as exc:
            raise UpdateFailed(f"Flatpak update failed: {exc}") from exc

    def update_snap(self) -> None:
        subprocess.run(["snap", "refresh"], check=True)

    def update_snap_package(self, name: str) -> None:
        if not validate_package_name(name):
            raise InvalidPackage("Invalid Snap name")
        try:
            subprocess.run(["snap", "refresh", name], check=True)
        except subprocess.CalledProcessError as exc:
            raise UpdateFailed(f"Snap update failed: {exc}") from exc

    def update_all(self) -> None:
        try:
            self.update_apt()
            self.update_flatpak()
            self.update_snap()
        except subprocess.CalledProcessError as exc:
            raise UpdateFailed(f"System update failed: {exc}") from exc
