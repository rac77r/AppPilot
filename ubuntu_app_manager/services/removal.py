from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from ubuntu_app_manager.domain.errors import InvalidPackage, RemovalFailed
from ubuntu_app_manager.security.validation import ensure_safe_file_target, executable_bit, validate_package_name


class RemovalService:
    def remove_appimage(self, path: str) -> list[str]:
        target = Path(path).expanduser()
        allowed_dirs = (
            Path.home() / "Applications",
            Path.home() / "AppImages",
            Path.home() / "Downloads",
        )
        if target.suffix.lower() != ".appimage" or not target.is_file() or not ensure_safe_file_target(target):
            raise RemovalFailed("AppImage path is invalid or unsafe")
        if not any(target.parent == allowed_dir for allowed_dir in allowed_dirs):
            raise RemovalFailed("AppImage is outside the managed user directories")
        target.unlink()
        return [str(target)]

    def remove_desktop(self, desktop_file: str, exec_command: str | None = None) -> list[str]:
        desktop_path = Path(desktop_file).expanduser()
        user_applications = Path.home() / ".local" / "share" / "applications"
        try:
            desktop_path.relative_to(user_applications)
        except ValueError as exc:
            raise RemovalFailed("Only user-owned desktop entries can be removed") from exc

        if desktop_path.suffix != ".desktop" or not desktop_path.is_file() or not ensure_safe_file_target(desktop_path):
            raise RemovalFailed("Desktop entry path is invalid or unsafe")

        removed: list[str] = []
        if exec_command:
            try:
                command = shlex.split(exec_command)
            except ValueError as exc:
                raise RemovalFailed("Desktop Exec command is invalid") from exc

            if len(command) == 1:
                resolved_target = command[0] if os.path.isabs(command[0]) else shutil.which(command[0])
                target = Path(resolved_target).expanduser() if resolved_target else None
                try:
                    if target is not None:
                        target.relative_to(Path.home())
                except ValueError:
                    target = None
                if target and target.is_file() and executable_bit(target) and ensure_safe_file_target(target):
                    target.unlink()
                    removed.append(str(target))

        desktop_path.unlink()
        removed.append(str(desktop_path))
        return removed

    def remove_apt(self, package_name: str) -> None:
        if not validate_package_name(package_name):
            raise InvalidPackage("Invalid APT package name")
        try:
            subprocess.run(["apt", "remove", "-y", package_name], check=True)
        except subprocess.CalledProcessError as exc:
            raise RemovalFailed(f"APT removal failed: {exc}") from exc

    def remove_snap(self, name: str) -> None:
        if not validate_package_name(name):
            raise InvalidPackage("Invalid Snap name")
        try:
            subprocess.run(["snap", "remove", name], check=True)
        except subprocess.CalledProcessError as exc:
            raise RemovalFailed(f"Snap removal failed: {exc}") from exc

    def remove_flatpak(self, app_id: str) -> None:
        if not app_id or " " in app_id:
            raise InvalidPackage("Invalid Flatpak app ID")
        try:
            subprocess.run(["flatpak", "uninstall", "-y", app_id], check=True)
        except subprocess.CalledProcessError as exc:
            raise RemovalFailed(f"Flatpak removal failed: {exc}") from exc
