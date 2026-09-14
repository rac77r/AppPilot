from __future__ import annotations

import shutil
from pathlib import Path


class AuthorizationService:
    """Tiny wrapper around system authorization primitives."""

    def __init__(self) -> None:
        self.pkexec = shutil.which("pkexec")
        self.pkcheck = shutil.which("pkcheck")

    def available(self) -> bool:
        return self.pkexec is not None

    def require_authorization(self, reason: str) -> str:
        if not self.available():
            raise RuntimeError("Authorization mechanism unavailable")
        return reason

    def ensure_file_is_safe_for_write(self, file_path: str | Path) -> bool:
        candidate = Path(file_path)
        if not candidate.exists():
            return False
        return candidate.is_file()
