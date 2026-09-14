from __future__ import annotations

import subprocess
from pathlib import Path

from ubuntu_app_manager.domain.errors import InvalidPackage
from ubuntu_app_manager.security.validation import validate_flatpak_ref, validate_package_name, validate_path


class InstallationService:
    def install_apt(self, package_name: str) -> None:
        if not validate_package_name(package_name):
            raise InvalidPackage("Invalid APT package name")
        subprocess.run(["apt", "install", "-y", package_name], check=True)

    def install_deb(self, path: str) -> None:
        target = Path(path)
        if not target.exists() or not target.name.endswith(".deb"):
            raise InvalidPackage("Unsupported .deb file")
        if not validate_path(str(target)):
            raise InvalidPackage("Unsafe package path")
        subprocess.run(["apt", "install", "-y", str(target)], check=True)

    def install_snap(self, name: str) -> None:
        if not validate_package_name(name):
            raise InvalidPackage("Invalid Snap name")
        subprocess.run(["snap", "install", name], check=True)

    def install_flatpak(self, ref: str) -> None:
        if not validate_flatpak_ref(ref):
            raise InvalidPackage("Invalid Flatpak reference")
        subprocess.run(["flatpak", "install", "-y", ref], check=True)
