from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from ubuntu_app_manager.security.validation import executable_bit, validate_path


class LaunchService:
    def resolve_command(self, command: str | None) -> list[str] | None:
        if not command or not command.strip():
            return None

        candidate = command.strip()
        if os.path.isabs(candidate):
            if not validate_path(candidate):
                return None
            return [candidate]

        try:
            parts = shlex.split(candidate, posix=True)
        except ValueError:
            return None
        if not parts:
            return None

        executable = parts[0]
        if executable.startswith("/"):
            if not validate_path(executable):
                return None
            return parts

        resolved = shutil.which(executable)
        if not resolved:
            return None
        if not validate_path(resolved):
            return None
        return [resolved, *parts[1:]]

    def can_launch(self, path: str | None) -> bool:
        if not path:
            return False

        resolved = self.resolve_command(path)
        if not resolved:
            return False

        target = resolved[0]
        if not os.path.isabs(target):
            return False
        if not validate_path(target):
            return False
        return executable_bit(target)

    def launch(self, path: str | None) -> None:
        resolved = self.resolve_command(path)
        if not resolved or not self.can_launch(path):
            raise ValueError("Application path is invalid or not executable")
        subprocess.Popen(resolved, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
