# AppPilot

AppPilot is a native Ubuntu application manager designed to discover, inspect, launch, update, and remove applications from the system using the operating system itself as the source of truth. It consolidates software from apt, Snap, Flatpak, AppImage, and desktop launchers into a single clean interface built with GTK 4 and Libadwaita.

## What AppPilot does

- Discovers installed and available applications from multiple package sources
- Shows a unified application catalog with source-aware metadata
- Launches applications from the system, respecting the real desktop environment setup
- Supports installation, update, and removal flows for supported package types
- Uses validation and safety checks before privileged operations are executed
- Provides a desktop-native UI focused on Ubuntu/Linux workflows

## Project structure

- `ubuntu_app_manager/app/` — GTK application bootstrap and main window
- `ubuntu_app_manager/domain/` — domain models, statuses, permissions, and error types
- `ubuntu_app_manager/providers/` — adapters for apt, Snap, Flatpak, AppImage, and desktop sources
- `ubuntu_app_manager/services/` — inventory, installation, update, removal, search, and launch logic
- `ubuntu_app_manager/security/` — validation and authorization helpers
- `ubuntu_app_manager/diagnostics/` — rotating structured runtime logging
- `ubuntu_app_manager/ui/` — dialogs and view widgets
- `ubuntu_app_manager/persistence/` — settings and persistence
- `tests/` — automated regression and validation tests

## Requirements

This project is intended for Ubuntu-based Linux systems and assumes a desktop environment with GTK support.

### Required system components

Before building and running the app, install the following:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip python3-dev \
  build-essential pkg-config \
  libgtk-4-dev libadwaita-1-dev \
  libglib2.0-dev libcairo2-dev \
  gobject-introspection gir1.2-gtk-4.0 gir1.2-adw-1.0
```

### Optional but commonly used runtime tools

Depending on your Ubuntu installation, these may be useful or already available:

```bash
sudo apt install -y apt flatpak snapd
```

> Flatpak and Snap support are handled by the app when the corresponding system tools are installed and available.

## Build and run

### 1. Clone the repository

```bash
git clone <repository-url>
cd AppPilot
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Upgrade packaging tools

```bash
python -m pip install --upgrade pip setuptools wheel
```

### 4. Install the project in editable mode

```bash
python -m pip install -e .
```

### 5. Run the application

```bash
appilot
```

## Development workflow

Run the test suite:

```bash
python -m pytest
```

If you want to run the app inside a virtual display for headless environments:

```bash
xvfb-run -a appilot
```

## Diagnostics

AppPilot writes a rotating diagnostic log to:

```text
~/.local/state/AppPilot/apppilot.log
```

The log records application startup, keyboard key names and modifiers, search queries and result counts, filters, selection changes, button and dialog responses, package actions, launch attempts, success status, and exception tracebacks. Log files are limited to 5 MB each with three rotated backups.

To inspect the most recent events:

```bash
tail -n 100 ~/.local/state/AppPilot/apppilot.log
```

## Security model

AppPilot treats the system inventory as the authoritative source. It does not assume local caches are trusted. System operations are validated before execution, and unsafe paths, invalid package names, or malicious Flatpak references are rejected before running any privileged command.

## Notes

- The project is designed for Ubuntu/Linux systems and expects system package managers to be available.
- The UI is implemented in GTK 4 and Libadwaita for a native desktop experience.
- The application is intentionally structured around real system providers instead of mock-only data.
