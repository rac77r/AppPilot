from __future__ import annotations

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, Gtk

from ubuntu_app_manager.app.config import APP_ID, APP_NAME, APP_SUBTITLE, APP_VERSION
from ubuntu_app_manager.domain.models.application import Application, AppStatus, SourceType
from ubuntu_app_manager.diagnostics import get_logger, log_event
from ubuntu_app_manager.persistence.settings import SettingsStore
from ubuntu_app_manager.services.installation import InstallationService
from ubuntu_app_manager.services.inventory import InventoryService
from ubuntu_app_manager.services.launch import LaunchService
from ubuntu_app_manager.services.removal import RemovalService
from ubuntu_app_manager.services.search import SearchService
from ubuntu_app_manager.services.update import UpdateService
from ubuntu_app_manager.ui.dialogs import create_about_dialog, create_install_dialog, create_confirm_dialog, create_progress_dialog


def sort_applications(apps: list[Application]) -> list[Application]:
    return sorted(
        apps,
        key=lambda app: (
            0 if app.status == AppStatus.UPDATE_AVAILABLE else 1 if app.status == AppStatus.INSTALLED else 2,
            app.display_name.lower() if app.display_name else app.name.lower(),
        ),
    )


def application_icon_name(app: Application) -> str:
    return {
        SourceType.APT: "package-x-generic-symbolic",
        SourceType.SNAP: "security-high-symbolic",
        SourceType.FLATPAK: "application-x-addon-symbolic",
        SourceType.APPIMAGE: "drive-removable-media-symbolic",
        SourceType.DESKTOP: "desktop-symbolic",
        SourceType.UNKNOWN: "applications-system-symbolic",
    }.get(app.source_type, "application-x-executable-symbolic")


def set_application_icon(image: Gtk.Image, app: Application) -> None:
    if app.icon:
        icon_path = Path(app.icon).expanduser()
        if icon_path.is_file():
            image.set_from_file(str(icon_path))
            return
        if not app.icon.startswith("/"):
            image.set_from_icon_name(app.icon)
            return
    image.set_from_icon_name(application_icon_name(app))


class AppPilotApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.window: Gtk.Window | None = None
        self.logger = get_logger()
        log_event(self.logger, "application_initialized", version=APP_VERSION)
        self.settings = SettingsStore()
        self.search_service = SearchService()
        self._apply_global_css()

    def _apply_global_css(self) -> None:
        css = b"""
        * {
            color: #d7dae0;
        }

        window,
        dialog {
            background-color: #1f2023;
        }

        headerbar {
            min-height: 54px;
            background-color: #2b2d30;
            border-bottom: 1px solid #3b3e43;
        }

        headerbar windowtitle,
        headerbar windowtitle title {
            color: #f2f3f5;
        }

        entry,
        searchentry {
            min-height: 34px;
            border: 1px solid #45484e;
            border-radius: 6px;
            background-color: #303236;
            color: #f2f3f5;
            caret-color: #ffcc66;
        }

        entry:focus,
        searchentry:focus-within {
            border-color: #5b8def;
            box-shadow: 0 0 0 1px #5b8def;
        }

        button {
            min-height: 32px;
            border: 1px solid #45484e;
            border-radius: 6px;
            background-color: #36383d;
            color: #e5e7eb;
        }

        button:hover {
            background-color: #41444a;
        }

        button:active {
            background-color: #4b4e55;
        }

        .suggested-action {
            border-color: #5b8def;
            background-color: #3e6fca;
            color: #ffffff;
        }

        .suggested-action:hover {
            background-color: #4b80df;
        }

        .workspace {
            background-color: #1f2023;
        }

        .sidebar {
            background-color: #25272b;
            border-right: 1px solid #3b3e43;
        }

        .sidebar-title {
            color: #8f96a3;
            font-size: 11px;
            font-weight: 700;
        }

        .nav-button {
            min-height: 34px;
            border: 0;
            border-radius: 5px;
            background-color: transparent;
            color: #b9bec8;
        }

        .nav-button:hover {
            background-color: #303338;
            color: #f2f3f5;
        }

        .content-panel,
        .details-panel {
            background-color: #1f2023;
        }

        .details-panel {
            border-left: 1px solid #3b3e43;
        }

        listbox {
            background-color: #1f2023;
        }

        .app-row {
            min-height: 70px;
            border-bottom: 1px solid #2d2f34;
            background-color: #1f2023;
        }

        .app-row:hover {
            background-color: #292b30;
        }

        .app-row:selected {
            background-color: #2f405d;
        }

        .app-title {
            color: #f2f3f5;
            font-weight: 600;
        }

        .detail-title {
            color: #f2f3f5;
            font-size: 20px;
            font-weight: 700;
        }

        .section-title {
            color: #f2f3f5;
            font-weight: 700;
        }

        .metadata-key {
            color: #8f96a3;
        }

        .pill {
            border: 1px solid #4a4e56;
            border-radius: 12px;
            background-color: #303236;
            color: #c9ced8;
        }

        .dim-label {
            color: #969da9;
        }

        .caption {
            color: #a8aeb9;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def do_activate(self) -> None:
        log_event(self.logger, "application_activate", existing_window=self.window is not None)
        if self.window is None:
            self.window = AppPilotWindow(application=self)
            self.window.present()
        else:
            self.window.present()

    def do_shutdown(self) -> None:
        log_event(self.logger, "application_shutdown")
        super().do_shutdown()


class AppPilotWindow(Adw.ApplicationWindow):
    def __init__(self, application: AppPilotApplication) -> None:
        super().__init__(application=application)
        self.logger = application.logger
        self.set_title(APP_NAME)
        self.set_default_size(1200, 620)

        self.inventory = InventoryService()
        self.search_service = SearchService(self.inventory)
        self.launch_service = LaunchService()
        self.installation_service = InstallationService()
        self.removal_service = RemovalService()
        self.update_service = UpdateService()
        self.all_apps = list(self.inventory.discover())
        self.current_apps = list(self.all_apps)
        self.current_filter = "all"
        self.current_query = ""
        self.filter_buttons: dict[str, Gtk.Button] = {}

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=APP_NAME, subtitle=APP_SUBTITLE))

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search applications")
        self.search_entry.set_halign(Gtk.Align.CENTER)
        self.search_entry.connect("search-changed", self._on_search_changed)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        install_button = Gtk.Button.new_with_label("+ Install")
        install_button.add_css_class("suggested-action")
        install_button.connect("clicked", self._show_install_dialog)

        update_button = Gtk.Button.new_with_label("Update all")
        update_button.add_css_class("suggested-action")
        update_button.connect("clicked", self._update_all)

        sources_button = Gtk.MenuButton(label="Sources")
        sources_button.set_tooltip_text("Filter applications by source")
        sources_popover = Gtk.Popover()
        sources_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sources_box.set_margin_top(8)
        sources_box.set_margin_bottom(8)
        sources_box.set_margin_start(8)
        sources_box.set_margin_end(8)
        sources_popover.set_child(sources_box)
        sources_button.set_popover(sources_popover)

        header.pack_start(self.search_entry)
        header.pack_end(sources_button)
        header.pack_end(update_button)
        header.pack_end(install_button)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        content.add_css_class("workspace")
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sidebar.add_css_class("sidebar")
        sidebar.set_size_request(220, -1)
        sidebar.set_valign(Gtk.Align.START)

        sidebar_title = Gtk.Label(label="APPLICATIONS")
        sidebar_title.add_css_class("sidebar-title")
        sidebar_title.set_halign(Gtk.Align.START)
        sidebar_title.set_margin_start(12)
        sidebar_title.set_margin_top(8)
        sidebar.append(sidebar_title)

        for label in ["All", "Installed", "Updates", "Settings"]:
            row = Gtk.Button(label=label)
            row.add_css_class("nav-button")
            row.set_halign(Gtk.Align.FILL)
            row.set_hexpand(True)
            row.add_css_class("flat")
            row.connect("clicked", self._on_filter_selected, label)
            self.filter_buttons[label] = row
            sidebar.append(row)

        for label in ["APT", "Snap", "Flatpak", "AppImage", "Unknown"]:
            row = Gtk.Button(label=label)
            row.add_css_class("nav-button")
            row.set_halign(Gtk.Align.FILL)
            row.set_hexpand(True)
            row.connect("clicked", self._on_filter_selected, label)
            self.filter_buttons[label] = row
            sources_box.append(row)

        self._apply_filter_style("All")

        self.app_list = Gtk.ListBox()
        self.app_list.add_css_class("app-list")
        self.app_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.app_list.connect("row-selected", self._on_row_selected)

        self.details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.details_box.add_css_class("details-panel")
        self.details_box.set_size_request(360, -1)
        self.details_box.set_margin_top(8)
        self.details_box.set_margin_bottom(8)
        self.details_box.set_margin_start(8)
        self.details_box.set_margin_end(8)

        list_scroll = Gtk.ScrolledWindow()
        list_scroll.set_min_content_width(420)
        list_scroll.set_hexpand(True)
        list_scroll.set_vexpand(True)
        list_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        list_scroll.set_child(self.app_list)

        details_scroll = Gtk.ScrolledWindow()
        details_scroll.set_min_content_width(360)
        details_scroll.set_vexpand(True)
        details_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        details_scroll.set_child(self.details_box)

        main_split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        main_split.add_css_class("content-panel")
        main_split.set_hexpand(True)
        main_split.set_vexpand(True)
        main_split.append(list_scroll)
        main_split.append(details_scroll)

        content.append(sidebar)
        content.append(main_split)

        toolbar.set_content(content)
        self.set_content(toolbar)

        self._refresh_app_list()
        log_event(self.logger, "window_ready", app_count=len(self.all_apps))

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.current_query = entry.get_text() or ""
        self._refresh_app_list(self.current_query)
        log_event(
            self.logger,
            "search_changed",
            query=self.current_query,
            result_count=len(self.current_apps),
        )

    def _on_key_pressed(self, controller: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> bool:
        key_name = Gdk.keyval_name(keyval) or str(keyval)
        modifiers = []
        for modifier, name in (
            (Gdk.ModifierType.CONTROL_MASK, "Ctrl"),
            (Gdk.ModifierType.ALT_MASK, "Alt"),
            (Gdk.ModifierType.SHIFT_MASK, "Shift"),
            (Gdk.ModifierType.SUPER_MASK, "Super"),
        ):
            if state & modifier:
                modifiers.append(name)
        log_event(
            self.logger,
            "key_pressed",
            key=key_name,
            keycode=keycode,
            modifiers=modifiers,
        )
        return False

    def _on_filter_selected(self, button: Gtk.Button, label: str) -> None:
        self.current_filter = label.lower()
        self._apply_filter_style(label)
        self._refresh_app_list(self.current_query)
        log_event(
            self.logger,
            "filter_selected",
            filter=label,
            query=self.current_query,
            result_count=len(self.current_apps),
        )

    def _apply_filter_style(self, label: str) -> None:
        for name, btn in self.filter_buttons.items():
            if name == label:
                btn.add_css_class("suggested-action")
            else:
                btn.remove_css_class("suggested-action")

    def _matches_filter(self, app: Application) -> bool:
        filter_key = self.current_filter
        if filter_key == "all":
            return True
        if filter_key == "installed":
            return app.status == AppStatus.INSTALLED
        if filter_key == "updates":
            return app.status == AppStatus.UPDATE_AVAILABLE
        if filter_key == "apt":
            return app.source_type == SourceType.APT
        if filter_key == "snap":
            return app.source_type == SourceType.SNAP
        if filter_key == "flatpak":
            return app.source_type == SourceType.FLATPAK
        if filter_key == "appimage":
            return app.source_type == SourceType.APPIMAGE
        if filter_key == "unknown":
            return app.source_type == SourceType.UNKNOWN
        if filter_key == "settings":
            return True
        return True

    def _status_text(self, app: Application) -> str:
        if app.status == AppStatus.UPDATE_AVAILABLE:
            return "Update available"
        if app.status == AppStatus.ERROR:
            return "Needs attention"
        if app.status == AppStatus.NOT_INSTALLED:
            return "Not installed"
        if app.status == AppStatus.UNAVAILABLE:
            return "Unavailable"
        return "Installed"

    def _on_row_selected(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            return
        app = getattr(row, "app", None)
        if app is not None:
            self._show_details(app)
            log_event(
                self.logger,
                "application_selected",
                app_id=app.id,
                source=app.source_type.value,
            )

    def _refresh_app_list(self, query: str = "") -> None:
        self.app_list.remove_all()
        apps = self.search_service.search(query or "", self.all_apps)
        filtered = [app for app in apps if self._matches_filter(app)]
        self.current_apps = sort_applications(filtered)

        if not filtered:
            status = Adw.StatusPage(title="No applications found", description="The current scan did not match any installed application.")
            self.app_list.append(status)
            self._show_details(None)
            return

        for app in filtered:
            row = Gtk.ListBoxRow()
            row.add_css_class("app-row")
            row.set_selectable(True)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(12)
            box.set_margin_end(12)

            icon = Gtk.Image()
            set_application_icon(icon, app)
            icon.set_size_request(32, 32)
            box.append(icon)

            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            title = Gtk.Label(label=app.display_name or app.name)
            title.add_css_class("app-title")
            title.set_halign(Gtk.Align.START)
            title.set_xalign(0)
            subtitle = Gtk.Label(label=f"{app.source_type.value} • {app.version or 'unknown version'}")
            subtitle.set_halign(Gtk.Align.START)
            subtitle.set_xalign(0)
            subtitle.add_css_class("dim-label")
            status = Gtk.Label(label=self._status_text(app))
            status.set_halign(Gtk.Align.START)
            status.set_xalign(0)
            status.add_css_class("caption")
            text.append(title)
            text.append(subtitle)
            text.append(status)
            box.append(text)
            box.set_hexpand(True)
            row.set_child(box)
            row.app = app
            self.app_list.append(row)

        if filtered:
            first_row = self.app_list.get_row_at_index(0)
            if first_row is not None:
                self.app_list.select_row(first_row)

    def _launch_target(self, app: Application) -> str | None:
        target = app.executable_path or app.metadata.get("exec")
        return target if isinstance(target, str) and target.strip() else None

    def _can_launch(self, app: Application) -> bool:
        target = self._launch_target(app)
        return bool(target and self.launch_service.can_launch(target))

    def _launch_app(self, button: Gtk.Button, app: Application) -> None:
        target = self._launch_target(app)
        log_event(self.logger, "launch_requested", app_id=app.id, target=target)
        if not target:
            log_event(self.logger, "launch_completed", success=False, app_id=app.id, reason="no_target")
            return
        try:
            self.launch_service.launch(target)
            log_event(self.logger, "launch_completed", app_id=app.id, target=target)
        except Exception as error:
            log_event(
                self.logger,
                "launch_completed",
                success=False,
                app_id=app.id,
                target=target,
                error=repr(error),
                exc_info=True,
            )

    def _show_install_dialog(self, *args) -> None:
        log_event(self.logger, "install_dialog_opened")
        dialog = create_install_dialog(self, self.installation_service, self.logger)
        dialog.present()

    def _update_all(self, *args) -> None:
        log_event(self.logger, "update_all_requested")

        def do_update_all() -> None:
            try:
                self.update_service.update_all()
                log_event(self.logger, "update_all_completed")
            except Exception as error:
                log_event(
                    self.logger,
                    "update_all_completed",
                    success=False,
                    error=repr(error),
                    exc_info=True,
                )

        dialog = create_confirm_dialog(
            self,
            "Update all packages",
            "This will refresh and upgrade the supported package sources on this system.",
            "Update",
            do_update_all,
            self.logger,
        )
        dialog.present()

    def _update_app(self, button: Gtk.Button, app: Application) -> None:
        log_event(self.logger, "update_requested", app_id=app.id, source=app.source_type.value)

        def do_update() -> None:
            try:
                if app.source_type == SourceType.APT:
                    self.update_service.update_apt_package(app.package_name or app.name)
                elif app.source_type == SourceType.SNAP:
                    self.update_service.update_snap_package(app.package_name or app.name)
                elif app.source_type == SourceType.FLATPAK:
                    self.update_service.update_flatpak_package(app.application_id or app.package_name or app.name)
                log_event(self.logger, "update_completed", app_id=app.id)
            except Exception as error:
                log_event(self.logger, "update_completed", success=False, app_id=app.id, error=repr(error), exc_info=True)

        dialog = create_confirm_dialog(
            self,
            f"Update {app.display_name or app.name}",
            f"Start the update process for {app.display_name or app.name}?",
            "Update",
            do_update,
            self.logger,
        )
        dialog.present()

    def _remove_app(self, button: Gtk.Button, app: Application) -> None:
        if not app.has_capability("can_remove"):
            log_event(
                self.logger,
                "remove_requested",
                success=False,
                app_id=app.id,
                source=app.source_type.value,
                reason="unsupported_source",
            )
            return

        log_event(self.logger, "remove_requested", app_id=app.id, source=app.source_type.value)

        def do_remove() -> list[str]:
            removed_targets: list[str] = []
            if app.source_type == SourceType.APT:
                self.removal_service.remove_apt(app.package_name or app.name)
                removed_targets = [app.package_name or app.name]
            elif app.source_type == SourceType.SNAP:
                self.removal_service.remove_snap(app.package_name or app.name)
                removed_targets = [app.package_name or app.name]
            elif app.source_type == SourceType.FLATPAK:
                self.removal_service.remove_flatpak(app.application_id or app.package_name or app.name)
                removed_targets = [app.application_id or app.package_name or app.name]
            elif app.source_type == SourceType.APPIMAGE and app.executable_path:
                removed_targets = self.removal_service.remove_appimage(app.executable_path)
            elif app.source_type == SourceType.DESKTOP and app.desktop_file:
                removed_targets = self.removal_service.remove_desktop(app.desktop_file, app.metadata.get("exec"))
            else:
                raise ValueError(f"Removal is not supported for {app.source_type.value}")
            log_event(self.logger, "remove_completed", app_id=app.id, removed_targets=removed_targets)
            return removed_targets

        def refresh_after_remove() -> None:
            self.all_apps = list(self.inventory.discover())
            self._refresh_app_list(self.current_query)

        remove_label = self._remove_label(app)
        dialog = create_confirm_dialog(
            self,
            f"Remove {app.display_name or app.name}",
            f"This will {remove_label.lower()} for {app.display_name or app.name}. A progress window will show the operation status.",
            remove_label,
            lambda: create_progress_dialog(
                self,
                f"Removing {app.display_name or app.name}",
                do_remove,
                self.logger,
                refresh_after_remove,
            ),
            self.logger,
        )
        dialog.present()

    def _remove_label(self, app: Application) -> str:
        if app.source_type == SourceType.DESKTOP and not app.metadata.get("remove_target"):
            return "Remove launcher"
        return "Remove application"

    def _show_details(self, app: Application | None) -> None:
        for child in list(self.details_box):
            self.details_box.remove(child)

        if app is None:
            placeholder = Adw.StatusPage(title="Select an application", description="Choose an application from the list to inspect details and launch actions.")
            self.details_box.append(placeholder)
            return

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_halign(Gtk.Align.FILL)
        icon = Gtk.Image()
        set_application_icon(icon, app)
        icon.set_size_request(56, 56)
        header.append(icon)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label(label=app.display_name or app.name)
        title.add_css_class("detail-title")
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0)
        subtitle = Gtk.Label(label=f"{app.source_type.value} • {app.version or 'unknown version'}")
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_xalign(0)
        subtitle.add_css_class("dim-label")
        status = Gtk.Label(label=self._status_text(app))
        status.set_halign(Gtk.Align.START)
        status.set_xalign(0)
        status.add_css_class("caption")
        text.append(title)
        text.append(subtitle)
        text.append(status)
        header.append(text)
        self.details_box.append(header)

        description = Gtk.Label(label=app.description or "No description available")
        description.set_wrap(True)
        description.set_halign(Gtk.Align.START)
        description.set_xalign(0)
        self.details_box.append(description)

        meta = Gtk.Grid()
        meta.set_column_spacing(16)
        meta.set_row_spacing(8)

        fields = [
            ("Status", app.status.value if hasattr(app.status, "value") else str(app.status)),
            ("Source", app.source_type.value),
            ("Version", app.version or "unknown"),
            ("Package", app.package_name or app.name),
            ("Publisher", app.publisher or "system"),
            ("Executable", app.executable_path or "not available"),
        ]

        for index, (label_text, value_text) in enumerate(fields):
            label = Gtk.Label(label=f"{label_text}:")
            label.add_css_class("metadata-key")
            label.set_halign(Gtk.Align.START)
            label.set_xalign(0)
            value = Gtk.Label(label=str(value_text))
            value.set_halign(Gtk.Align.START)
            value.set_xalign(0)
            value.set_selectable(True)
            value.set_wrap(True)
            value.set_hexpand(True)
            meta.attach(label, 0, index, 1, 1)
            meta.attach(value, 1, index, 1, 1)
        self.details_box.append(meta)

        permissions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        permissions_title = Gtk.Label(label="Permissions")
        permissions_title.set_halign(Gtk.Align.START)
        permissions_title.set_xalign(0)
        permissions_box.append(permissions_title)

        if app.permissions:
            perms_grid = Gtk.Grid()
            perms_grid.set_row_spacing(6)
            perms_grid.set_column_spacing(12)
            for idx, permission in enumerate(app.permissions):
                perm_label = Gtk.Label(label=f"{permission.name}: {permission.state.label}")
                perm_label.set_halign(Gtk.Align.START)
                perm_label.set_xalign(0)
                perm_desc = Gtk.Label(label=permission.details or "System-level permission")
                perm_desc.set_halign(Gtk.Align.START)
                perm_desc.set_xalign(0)
                perm_desc.add_css_class("dim-label")
                perms_grid.attach(perm_label, 0, idx, 1, 1)
                perms_grid.attach(perm_desc, 1, idx, 1, 1)
            permissions_box.append(perms_grid)
        else:
            fallback = Gtk.Label(label="No explicit permission metadata is available.")
            fallback.set_halign(Gtk.Align.START)
            fallback.set_xalign(0)
            fallback.add_css_class("dim-label")
            permissions_box.append(fallback)
        self.details_box.append(permissions_box)

        metadata_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        metadata_title = Gtk.Label(label="System metadata")
        metadata_title.set_halign(Gtk.Align.START)
        metadata_title.set_xalign(0)
        metadata_box.append(metadata_title)

        metadata_grid = Gtk.Grid()
        metadata_grid.set_row_spacing(6)
        metadata_grid.set_column_spacing(12)
        metadata_items = [
            ("Architecture", app.architecture or "unknown"),
            ("Size", str(app.size) if app.size is not None else "unknown"),
            ("Install date", app.install_date.isoformat() if app.install_date else "unknown"),
            ("Desktop file", app.desktop_file or "not available"),
            ("Icon", app.icon or "default"),
        ]
        for idx, (key, value) in enumerate(metadata_items):
            key_label = Gtk.Label(label=f"{key}:")
            key_label.set_halign(Gtk.Align.START)
            key_label.set_xalign(0)
            value_label = Gtk.Label(label=str(value))
            value_label.set_halign(Gtk.Align.START)
            value_label.set_xalign(0)
            value_label.set_selectable(True)
            value_label.set_wrap(True)
            metadata_grid.attach(key_label, 0, idx, 1, 1)
            metadata_grid.attach(value_label, 1, idx, 1, 1)
        metadata_box.append(metadata_grid)
        self.details_box.append(metadata_box)

        capabilities = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cap_title = Gtk.Label(label="Capabilities")
        cap_title.set_halign(Gtk.Align.START)
        cap_title.set_xalign(0)
        capabilities.append(cap_title)

        flow = Gtk.FlowBox()
        flow.set_halign(Gtk.Align.START)
        flow.set_valign(Gtk.Align.START)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_column_spacing(8)
        flow.set_row_spacing(8)

        cap_names = sorted(app.capabilities) if app.capabilities else ["launch", "manage", "update"]
        for name in cap_names:
            pill = Gtk.Label(label=name.replace("_", " ").title())
            pill.add_css_class("pill")
            pill.set_margin_top(4)
            pill.set_margin_bottom(4)
            pill.set_margin_start(10)
            pill.set_margin_end(10)
            flow.append(pill)
        capabilities.append(flow)
        self.details_box.append(capabilities)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        launch_button = Gtk.Button(label="Launch")
        if self._can_launch(app):
            launch_button.connect("clicked", self._launch_app, app)
        else:
            launch_button.set_sensitive(False)
            launch_button.set_tooltip_text("No executable launch target is available")
        actions.append(launch_button)

        install_button = Gtk.Button(label="Install")
        install_button.connect("clicked", self._show_install_dialog)
        actions.append(install_button)

        remove_button = Gtk.Button(label=self._remove_label(app))
        remove_button.set_sensitive(app.has_capability("can_remove"))
        if remove_button.get_sensitive():
            remove_button.connect("clicked", self._remove_app, app)
        else:
            remove_button.set_tooltip_text("Removal is not supported for this application source")
        actions.append(remove_button)

        update_button = Gtk.Button(label="Update")
        update_button.connect("clicked", self._update_app, app)
        actions.append(update_button)

        self.details_box.append(actions)

    def on_about(self, action, parameter):
        log_event(self.logger, "about_opened")
        dialog = create_about_dialog(self)
        dialog.present()


def main() -> int:
    Adw.init()

    app = AppPilotApplication()
    return app.run(sys.argv)
