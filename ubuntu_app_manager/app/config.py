from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


APP_NAME = "AppPilot"
APP_SUBTITLE = "Ubuntu Application Manager"
APP_VERSION = "0.1.0"
APP_ID = "com.example.AppPilot"


@dataclass
class AppConfig:
    app_name: str = APP_NAME
    subtitle: str = APP_SUBTITLE
    version: str = APP_VERSION
    app_id: str = APP_ID
    settings_path: Path = field(default_factory=lambda: Path.home() / ".config" / "AppPilot" / "settings.json")
    appimage_dirs: list[str] = field(default_factory=lambda: [
        str(Path.home() / "Applications"),
        str(Path.home() / "AppImages"),
        str(Path.home() / "Downloads"),
    ])

    @property
    def icon_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / "resources" / "icons" / "appilot.svg"
