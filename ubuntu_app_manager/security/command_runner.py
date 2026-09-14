from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

from ubuntu_app_manager.security.validation import validate_package_name, validate_path


class CommandRunner:
    """Safe subprocess execution wrapper that disallows shell usage."""

    @staticmethod
    def run(args: Sequence[str], *, check: bool = True, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
        if not args:
            raise ValueError("No command specified")
        if isinstance(args, str):
            raise TypeError("use argument arrays instead of a string")
        for part in args:
            if not isinstance(part, str):
                raise TypeError("all command arguments must be strings")
        for part in args[1:]:
            if "\n" in part or "\r" in part:
                raise ValueError("Suspicious command argument")
        return subprocess.run(list(args), check=check, text=True, capture_output=True, cwd=cwd)

    @staticmethod
    def run_apt_install(package_name: str) -> subprocess.CompletedProcess[str]:
        if not validate_package_name(package_name):
            raise ValueError("Invalid package name")
        return CommandRunner.run(["apt", "install", "-y", package_name])

    @staticmethod
    def run_flatpak_install(ref: str) -> subprocess.CompletedProcess[str]:
        if not ref or " " in ref:
            raise ValueError("Invalid Flatpak reference")
        return CommandRunner.run(["flatpak", "install", "-y", ref])

    @staticmethod
    def set_executable(path: str | Path) -> None:
        candidate = str(path)
        if not validate_path(candidate):
            raise ValueError("Unsafe path")
        Path(candidate).chmod(0o755)
