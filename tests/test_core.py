import logging
import json
from pathlib import Path

import pytest

from ubuntu_app_manager.app.application import application_icon_name, sort_applications
from ubuntu_app_manager.domain.models.application import AppStatus, Application, SourceType
from ubuntu_app_manager.domain.models.permissions import PermissionState
from ubuntu_app_manager.diagnostics import log_event
from ubuntu_app_manager.providers.desktop_provider import DesktopProvider
from ubuntu_app_manager.security.validation import validate_path, validate_package_name
from ubuntu_app_manager.services.launch import LaunchService
from ubuntu_app_manager.services.installation import InstallationService
from ubuntu_app_manager.services.removal import RemovalService
from ubuntu_app_manager.services.search import SearchService
from ubuntu_app_manager.services.update import UpdateService


def test_application_has_expected_fields():
    app = Application(
        id="firefox",
        name="Firefox",
        display_name="Firefox",
        source_type=SourceType.APT,
        version="1.0",
        status=AppStatus.INSTALLED,
        executable_path="/usr/bin/firefox",
    )
    assert app.name == "Firefox"
    assert app.source_type == SourceType.APT
    assert app.status == AppStatus.INSTALLED


def test_permission_state_helpers():
    assert PermissionState.ALLOWED.label == "Allowed"
    assert PermissionState.DENIED.label == "Denied"


def test_validate_path_rejects_system_root():
    assert validate_path("/") is False
    assert validate_path("/usr/bin/firefox") is True


def test_validate_package_name_rejects_invalid_names():
    assert validate_package_name("firefox") is True
    assert validate_package_name("bad;rm -rf /") is False


def test_validate_path_rejects_symlink_escape(tmp_path):
    safe_dir = tmp_path / "safe"
    safe_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "secret.txt").write_text("owned", encoding="utf-8")
    link = safe_dir / "escape"
    link.symlink_to(outside_dir / "secret.txt")

    assert validate_path(str(link)) is False


def test_update_service_rejects_invalid_package_names():
    service = UpdateService()

    with pytest.raises(ValueError):
        service.update_apt_package("bad;rm -rf /")

    with pytest.raises(ValueError):
        service.update_snap_package("bad&&whoami")


def test_installation_service_supports_apt_install(monkeypatch):
    calls = []

    def fake_run(command, check):
        calls.append((command, check))
        return None

    monkeypatch.setattr("subprocess.run", fake_run)

    InstallationService().install_apt("firefox")

    assert calls == [(["apt", "install", "-y", "firefox"], True)]


def test_update_service_runs_full_update_cycle(monkeypatch):
    calls = []

    def fake_run(command, check):
        calls.append((command, check))
        return None

    monkeypatch.setattr("subprocess.run", fake_run)

    UpdateService().update_all()

    assert calls == [
        (["apt", "update"], True),
        (["apt", "upgrade", "-y"], True),
        (["flatpak", "update", "-y"], True),
        (["snap", "refresh"], True),
    ]


def test_sort_applications_prioritizes_updates_then_installed():
    apps = [
        Application(id="b", name="B", display_name="B", status=AppStatus.INSTALLED),
        Application(id="a", name="A", display_name="A", status=AppStatus.UPDATE_AVAILABLE),
        Application(id="c", name="C", display_name="C", status=AppStatus.INSTALLED),
    ]

    ordered = [app.name for app in sort_applications(apps)]

    assert ordered == ["A", "B", "C"]


def test_search_service_matches_calculator_entries_case_insensitive():
    apps = [
        Application(
            id="gnome-calculator",
            name="gnome-calculator",
            display_name="gnome-calculator",
            source_type=SourceType.APT,
            description=None,
        ),
        Application(
            id="org.gnome.Calculator",
            name="org.gnome.Calculator",
            display_name="org.gnome.Calculator",
            source_type=SourceType.DESKTOP,
            description=None,
        ),
    ]

    results = SearchService().search("calculator", apps)

    assert len(results) == 2
    assert {app.id for app in results} == {"gnome-calculator", "org.gnome.Calculator"}


def test_search_service_matches_partial_fragments_and_package_ids():
    apps = [
        Application(id="calculator", name="Calculator", display_name="Calculator"),
        Application(id="calc-237", name="calc-237", display_name="Calc Utility"),
        Application(id="unrelated", name="Editor", display_name="Editor"),
    ]

    results = SearchService().search("calc", apps)

    assert {app.id for app in results} == {"calculator", "calc-237"}


def test_application_icon_name_uses_source_fallbacks():
    assert application_icon_name(Application(id="apt", name="apt", display_name="APT", source_type=SourceType.APT)) == "package-x-generic-symbolic"
    assert application_icon_name(Application(id="snap", name="snap", display_name="Snap", source_type=SourceType.SNAP)) == "security-high-symbolic"
    assert application_icon_name(Application(id="custom", name="custom", display_name="Custom", source_type=SourceType.UNKNOWN, icon="custom-icon")) == "applications-system-symbolic"


def test_launch_service_accepts_system_command_names(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda command: "/usr/bin/gnome-calculator" if command == "gnome-calculator" else None)
    monkeypatch.setattr("os.access", lambda path, mode: path == "/usr/bin/gnome-calculator")

    service = LaunchService()

    assert service.can_launch("gnome-calculator") is True
    assert service.resolve_command("gnome-calculator") == ["/usr/bin/gnome-calculator"]


def test_launch_service_accepts_desktop_exec_with_arguments(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda command: "/usr/bin/flatpak" if command == "flatpak" else None)
    monkeypatch.setattr("os.access", lambda path, mode: path == "/usr/bin/flatpak")

    service = LaunchService()

    assert service.can_launch("flatpak run org.gnome.Calculator") is True
    assert service.resolve_command("flatpak run org.gnome.Calculator") == [
        "/usr/bin/flatpak",
        "run",
        "org.gnome.Calculator",
    ]


def test_log_event_writes_structured_success_status(caplog):
    logger = logging.getLogger("test-apppilot-logging")

    with caplog.at_level(logging.INFO, logger="test-apppilot-logging"):
        log_event(logger, "search_changed", query="calculator", result_count=3)

    payload = json.loads(caplog.records[-1].message)
    assert payload["event"] == "search_changed"
    assert payload["success"] is True
    assert payload["context"] == {"query": "calculator", "result_count": 3}


def test_desktop_provider_reads_launch_command_and_removes_field_codes(tmp_path):
    desktop_file = tmp_path / "calculator.desktop"
    desktop_file.write_text(
        "[Desktop Entry]\nName=Calculator\nComment=Calculate\nExec=gnome-calculator %U\n",
        encoding="utf-8",
    )

    values = DesktopProvider()._read_desktop_entry(desktop_file)

    assert values["Name"] == "Calculator"
    assert values["Exec"] == "gnome-calculator"


def test_removal_service_removes_user_desktop_and_executable(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    applications_dir = tmp_path / ".local" / "share" / "applications"
    applications_dir.mkdir(parents=True)
    executable = tmp_path / "Applications" / "calculator-1.1.1"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)
    desktop_file = applications_dir / "calculator.desktop"
    desktop_file.write_text("[Desktop Entry]\nName=Calculator\n", encoding="utf-8")

    removed = RemovalService().remove_desktop(str(desktop_file), str(executable))

    assert removed == [str(executable), str(desktop_file)]
    assert not executable.exists()
    assert not desktop_file.exists()


def test_removal_service_resolves_path_command_for_user_executable(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    applications_dir = tmp_path / ".local" / "share" / "applications"
    applications_dir.mkdir(parents=True)
    executable = tmp_path / ".local" / "bin" / "calculator-1.1.1"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)
    desktop_file = applications_dir / "calculator.desktop"
    desktop_file.write_text("[Desktop Entry]\nName=Calculator\n", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda command: str(executable) if command == "calculator-1.1.1" else None)

    removed = RemovalService().remove_desktop(str(desktop_file), "calculator-1.1.1")

    assert removed == [str(executable), str(desktop_file)]
    assert not executable.exists()
    assert not desktop_file.exists()


def test_removal_service_removes_managed_appimage(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    appimage = tmp_path / "Applications" / "demo.AppImage"
    appimage.parent.mkdir(parents=True)
    appimage.write_text("binary", encoding="utf-8")

    removed = RemovalService().remove_appimage(str(appimage))

    assert removed == [str(appimage)]
    assert not appimage.exists()
