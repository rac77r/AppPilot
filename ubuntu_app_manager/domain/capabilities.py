from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capability:
    name: str
    label: str


CAPABILITIES = {
    "can_install": Capability("can_install", "Install"),
    "can_update": Capability("can_update", "Update"),
    "can_remove": Capability("can_remove", "Remove"),
    "can_launch": Capability("can_launch", "Launch"),
    "can_open_location": Capability("can_open_location", "Open Location"),
    "can_view_details": Capability("can_view_details", "Details"),
    "can_make_executable": Capability("can_make_executable", "Make Executable"),
    "can_change_permissions": Capability("can_change_permissions", "Permissions"),
}


def default_capabilities() -> set[str]:
    return {
        "can_launch",
        "can_view_details",
        "can_open_location",
    }
