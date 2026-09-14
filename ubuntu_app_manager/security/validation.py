from __future__ import annotations

import os
import re
from pathlib import Path

SAFE_ROOTS = ("/usr/bin", "/usr/local/bin", "/opt", "/home", "/tmp", "/snap", "/var/lib/flatpak")


def _is_under_allowed_root(candidate: str) -> bool:
    real_path = os.path.realpath(candidate)
    for root in SAFE_ROOTS:
        root_prefix = root.rstrip("/") + "/"
        if real_path == root or real_path.startswith(root_prefix):
            return True
    return False


def validate_path(path: str | os.PathLike[str] | None) -> bool:
    if not path:
        return False

    candidate = os.fspath(path).strip()
    if not candidate or candidate in {"/", "~", "~/."}:
        return False

    try:
        expanded = os.path.expanduser(candidate)
        normalized = os.path.normpath(expanded)
        resolved = str(Path(normalized).resolve(strict=False))
    except (RuntimeError, OSError, ValueError):
        return False

    if normalized in {"/", ""}:
        return False
    if re.search(r"[\x00\n\r]", normalized):
        return False
    if normalized.startswith("/etc") or normalized.startswith("/var") or normalized.startswith("/proc"):
        return False

    if normalized.startswith(("/tmp/", "/home/")) and os.path.islink(normalized):
        return False

    if not _is_under_allowed_root(resolved):
        return False

    return True


def validate_package_name(name: str) -> bool:
    if not name or not name.strip():
        return False
    if name.strip() != name:
        return False
    if re.search(r"[;&\|`$><\\]", name):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", name))


def validate_flatpak_ref(ref: str) -> bool:
    if not ref or not ref.strip():
        return False
    if ref.strip() != ref:
        return False
    if re.search(r"[;&\|`$><\\\s]", ref):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9._-]+)+", ref))


def executable_bit(path: str | os.PathLike[str]) -> bool:
    try:
        return os.access(str(path), os.X_OK)
    except OSError:
        return False


def ensure_safe_file_target(path: str | os.PathLike[str]) -> bool:
    try:
        resolved = str(Path(path).resolve())
    except (RuntimeError, OSError):
        return False
    return validate_path(resolved)
