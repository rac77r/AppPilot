from __future__ import annotations

from pathlib import Path

from ubuntu_app_manager.domain.models.application import AppStatus, Application, SourceType
from ubuntu_app_manager.domain.models.permissions import Permission, PermissionState
from ubuntu_app_manager.providers.base import BaseProvider
from ubuntu_app_manager.security.validation import executable_bit, validate_path


class AppImageProvider(BaseProvider):
    name = "APPIMAGE"

    def can_handle(self) -> bool:
        return True

    def discover(self) -> list[Application]:
        locations = [
            Path.home() / "Applications",
            Path.home() / "AppImages",
            Path.home() / "Downloads",
        ]
        apps: list[Application] = []
        for base in locations:
            if not base.exists():
                continue
            for path in sorted(base.iterdir()):
                if path.is_file() and path.suffix.lower() in {".appimage", ".AppImage"}:
                    is_exec = executable_bit(path)
                    app = Application(
                        id=f"appimage:{path.as_posix()}",
                        name=path.stem,
                        display_name=path.stem,
                        source_type=SourceType.APPIMAGE,
                        package_name=path.name,
                        version=None,
                        executable_path=path.as_posix(),
                        icon=str(path.with_suffix(".svg")) if path.with_suffix(".svg").exists() else None,
                        status=AppStatus.INSTALLED if is_exec else AppStatus.ERROR,
                        capabilities={"can_launch", "can_open_location", "can_make_executable", "can_remove"},
                        permissions=[
                            Permission("Execution", PermissionState.ALLOWED if is_exec else PermissionState.DENIED, "Executable bit"),
                            Permission("Sandbox", PermissionState.UNKNOWN, "AppImage is not sandboxed by default"),
                        ],
                        metadata={"path": str(path), "is_executable": is_exec},
                    )
                    apps.append(app)
        return apps

    def get_details(self, identifier: str) -> Application | None:
        for app in self.discover():
            if app.id == identifier or app.executable_path == identifier:
                return app
        return None

    def make_executable(self, path: str) -> None:
        if not validate_path(path):
            raise ValueError("Unsafe AppImage path")
        target = Path(path)
        target.chmod(0o755)
