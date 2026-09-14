from __future__ import annotations

import configparser
import re
import shlex
import shutil
from pathlib import Path

from ubuntu_app_manager.domain.models.application import AppStatus, Application, SourceType
from ubuntu_app_manager.providers.base import BaseProvider


class DesktopProvider(BaseProvider):
    name = "DESKTOP"

    def can_handle(self) -> bool:
        return True

    def _read_desktop_entry(self, desktop: Path) -> dict[str, str]:
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        try:
            parser.read(desktop, encoding="utf-8")
            values = dict(parser.items("Desktop Entry"))
        except (configparser.Error, OSError, UnicodeError):
            return {}

        exec_command = values.get("Exec", "").strip()
        values["Exec"] = re.sub(r"\s+%[fFuUdDnNickvm]", "", exec_command)
        return values

    def discover(self) -> list[Application]:
        entries: list[Application] = []
        paths = [
            Path("/usr/share/applications"),
            Path.home() / ".local/share/applications",
        ]
        seen: set[str] = set()
        for base in paths:
            if not base.exists():
                continue
            for desktop in sorted(base.glob("*.desktop")):
                if desktop.name in seen:
                    continue
                seen.add(desktop.name)
                metadata = self._read_desktop_entry(desktop)
                exec_command = metadata.get("Exec") or None
                user_owned = base == Path.home() / ".local" / "share" / "applications"
                remove_target = None
                if user_owned and exec_command:
                    try:
                        command = shlex.split(exec_command)
                    except ValueError:
                        command = []
                    if len(command) == 1:
                        target_name = command[0]
                        resolved_target = target_name if target_name.startswith("/") else shutil.which(target_name)
                        target = Path(resolved_target).expanduser() if resolved_target else None
                    else:
                        target = None
                    if target:
                        try:
                            target.relative_to(Path.home())
                            if target.is_file():
                                remove_target = str(target)
                        except ValueError:
                            pass
                app_metadata = {"path": desktop.as_posix()}
                if exec_command:
                    app_metadata["exec"] = exec_command
                if remove_target:
                    app_metadata["remove_target"] = remove_target
                app = Application(
                    id=f"desktop:{desktop.as_posix()}",
                    name=desktop.stem,
                    display_name=metadata.get("Name") or desktop.stem,
                    source_type=SourceType.DESKTOP,
                    description=metadata.get("Comment"),
                    desktop_file=desktop.as_posix(),
                    icon=metadata.get("Icon"),
                    status=AppStatus.INSTALLED,
                    capabilities={"can_open_location"}
                    | ({"can_launch"} if exec_command else set())
                    | ({"can_remove"} if user_owned else set()),
                    metadata=app_metadata,
                )
                entries.append(app)
        return entries

    def get_details(self, identifier: str) -> Application | None:
        for app in self.discover():
            if app.id == identifier or app.desktop_file == identifier:
                return app
        return None
