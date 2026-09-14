from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SettingsStore:
    """Simple JSON-backed settings for AppPilot preferences."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else Path.home() / ".config" / "AppPilot" / "settings.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.write({"theme": "follow-system", "show_system_components": False, "check_for_updates": True})

    def read(self) -> dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return {}

    def write(self, data: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)

    def get(self, key: str, default: Any = None) -> Any:
        return self.read().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self.read()
        data[key] = value
        self.write(data)
