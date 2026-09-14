from __future__ import annotations

from gi.repository import Adw, Gtk

from ubuntu_app_manager.app.application import set_application_icon

from ubuntu_app_manager.app.config import APP_NAME, APP_SUBTITLE
from ubuntu_app_manager.services.inventory import InventoryService


class AppPilotMainWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app)
        self.set_title(APP_NAME)
        self.set_default_size(1200, 760)
        self.inventory = InventoryService()
        self._build_ui()

    def _build_ui(self) -> None:
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=APP_NAME, subtitle=APP_SUBTITLE))

        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Search applications")
        search_entry.set_hexpand(True)

        install_button = Gtk.Button(label="+ Install")
        install_button.add_css_class("suggested-action")

        toolbar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar_box.append(search_entry)
        toolbar_box.append(install_button)

        header.pack_start(toolbar_box)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sidebar.set_size_request(220, -1)
        for label in ["All", "Installed", "Updates", "Sources", "APT", "Snap", "Flatpak", "AppImage", "Unknown", "Settings"]:
            button = Gtk.Button(label=label)
            button.set_halign(Gtk.Align.FILL)
            sidebar.append(button)

        app_list = Gtk.ListBox()
        app_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._populate_applications(app_list)

        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        split.set_margin_top(12)
        split.set_margin_bottom(12)
        split.set_margin_start(12)
        split.set_margin_end(12)
        split.append(sidebar)
        split.append(app_list)

        content = Adw.ToolbarView()
        content.add_top_bar(header)
        content.set_content(split)
        self.set_content(content)

    def _populate_applications(self, app_list: Gtk.ListBox) -> None:
        apps = self.inventory.discover()
        if not apps:
            status = Adw.StatusPage(title="No applications detected", description="The system scan finished without any known application entries.")
            app_list.append(status)
            return

        for app in apps:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            box.set_margin_start(12)
            box.set_margin_end(12)
            box.set_margin_top(8)
            box.set_margin_bottom(8)

            icon = Gtk.Image()
            set_application_icon(icon, app)
            icon.set_size_request(32, 32)
            box.append(icon)

            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            heading = Gtk.Label(label=app.display_name or app.name)
            heading.set_halign(Gtk.Align.START)
            heading.set_xalign(0)
            sub = Gtk.Label(label=f"{app.source_type.value} • {app.version or 'unknown version'}")
            sub.set_halign(Gtk.Align.START)
            sub.set_xalign(0)
            sub.add_css_class("dim-label")
            text.append(heading)
            text.append(sub)
            box.append(text)

            action = Gtk.Button(label="Launch")
            action.set_halign(Gtk.Align.END)
            box.append(action)

            row.set_child(box)
            app_list.append(row)
