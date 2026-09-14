from __future__ import annotations

import threading

from gi.repository import Adw, Gtk
from gi.repository import GLib

from ubuntu_app_manager.diagnostics import get_logger, log_event


class SafeActionDialog(Adw.MessageDialog):
    def __init__(self, parent: Gtk.Window | None, title: str, body: str, primary_label: str = "Continue") -> None:
        super().__init__(transient_for=parent, modal=True)
        self.set_heading(title)
        self.set_body(body)
        self.add_response("cancel", "Cancel")
        self.add_response("confirm", primary_label)
        self.set_default_response("confirm")
        self.set_close_response("cancel")


def create_about_dialog(parent: Gtk.Window | None) -> Adw.AboutDialog:
    dialog = Adw.AboutDialog()
    dialog.set_application_name("AppPilot")
    dialog.set_version("0.1.0")
    dialog.set_comments("Ubuntu Application Manager")
    dialog.set_website("https://example.com/appilot")
    dialog.set_issue_url("https://example.com/appilot/issues")
    if parent is not None:
        dialog.set_transient_for(parent)
    return dialog


def create_install_dialog(parent: Gtk.Window | None, install_service, logger=None) -> Gtk.Dialog:
    logger = logger or get_logger()
    dialog = Gtk.Dialog(title="Install application", transient_for=parent, modal=True)
    dialog.set_default_size(420, 220)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)

    label = Gtk.Label(label="Choose installation source and enter the package reference.")
    label.set_halign(Gtk.Align.START)
    label.set_xalign(0)
    content.append(label)

    source_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    source_label = Gtk.Label(label="Source:")
    source_label.set_halign(Gtk.Align.START)
    source_combo = Gtk.ComboBoxText()
    source_combo.append_text("APT package")
    source_combo.append_text("Snap")
    source_combo.append_text("Flatpak")
    source_combo.append_text("Local .deb")
    source_combo.set_active(0)
    source_box.append(source_label)
    source_box.append(source_combo)
    content.append(source_box)

    entry = Gtk.Entry()
    entry.set_placeholder_text("firefox, snap name, flatpak ref, or /path/to/package.deb")
    entry.set_hexpand(True)
    content.append(entry)

    dialog.set_child(content)
    dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("_Install", Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.OK)

    def _on_response(dialog_obj: Gtk.Dialog, response: Gtk.ResponseType) -> None:
        log_event(logger, "install_dialog_response", response=str(response))
        if response != Gtk.ResponseType.OK:
            dialog_obj.destroy()
            return

        source = source_combo.get_active_text()
        value = entry.get_text().strip()
        if not value:
            log_event(logger, "install_completed", success=False, reason="empty_package_reference")
            dialog_obj.destroy()
            return

        try:
            if source == "APT package":
                install_service.install_apt(value)
            elif source == "Snap":
                install_service.install_snap(value)
            elif source == "Flatpak":
                install_service.install_flatpak(value)
            elif source == "Local .deb":
                install_service.install_deb(value)
            log_event(logger, "install_completed", source=source, package=value)
        except Exception as error:
            log_event(
                logger,
                "install_completed",
                success=False,
                source=source,
                package=value,
                error=repr(error),
                exc_info=True,
            )
        finally:
            dialog_obj.destroy()

    dialog.connect("response", _on_response)
    return dialog


def create_confirm_dialog(parent: Gtk.Window | None, title: str, body: str, confirm_label: str, action, logger=None) -> Adw.MessageDialog:
    logger = logger or get_logger()
    message = Adw.MessageDialog.new(parent, title, body)
    message.add_response("cancel", "Cancel")
    message.add_response("confirm", confirm_label)
    message.set_default_response("cancel")

    def _on_response(dialog: Adw.MessageDialog, response: str) -> None:
        log_event(logger, "confirmation_response", title=title, response=response)
        if response == "confirm":
            try:
                action()
                log_event(logger, "confirmation_action_completed", title=title)
            except Exception as error:
                log_event(
                    logger,
                    "confirmation_action_completed",
                    success=False,
                    title=title,
                    error=repr(error),
                    exc_info=True,
                )
        dialog.destroy()

    message.connect("response", _on_response)
    return message


def create_progress_dialog(parent: Gtk.Window | None, title: str, operation, logger=None, on_success=None) -> Gtk.Dialog:
    logger = logger or get_logger()
    dialog = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dialog.set_default_size(460, 170)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    content.set_margin_top(18)
    content.set_margin_bottom(18)
    content.set_margin_start(18)
    content.set_margin_end(18)

    status = Gtk.Label(label="Working... Please wait.")
    status.set_halign(Gtk.Align.START)
    status.set_xalign(0)
    progress = Gtk.ProgressBar()
    progress.set_show_text(True)
    progress.set_text("In progress")
    content.append(status)
    content.append(progress)
    dialog.set_child(content)
    dialog.set_deletable(False)
    dialog.present()

    pulse_source = GLib.timeout_add(80, lambda: progress.pulse() or True)

    def finish(success: bool, detail: str) -> bool:
        GLib.source_remove(pulse_source)
        if success and on_success is not None:
            on_success()
        progress.set_fraction(1.0 if success else 0.0)
        progress.set_text("Completed" if success else "Failed")
        status.set_text(detail)
        dialog.set_deletable(True)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        dialog.connect("response", lambda *_args: dialog.destroy())
        log_event(logger, "progress_dialog_completed", success=success, title=title, detail=detail)
        return False

    def run_operation() -> None:
        try:
            result = operation()
            detail = "Operation completed successfully."
            if result:
                detail = f"Removed {len(result)} item(s)."
            GLib.idle_add(finish, True, detail)
        except Exception as error:
            log_event(logger, "progress_dialog_error", success=False, title=title, error=repr(error), exc_info=True)
            GLib.idle_add(finish, False, f"Operation failed: {error}")

    threading.Thread(target=run_operation, name="apppilot-operation", daemon=True).start()
    return dialog
