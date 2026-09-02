# No-Sync Note Converter - Developer Notes

This repository contains the source for the **No-Sync Note Converter** Anki add-on.

## Project Structure

- `addon/`: Add-on package contents.
  - `__init__.py`: Entry point. Injects the browser/reviewer menu actions and binds the configuration GUI.
  - `browser_actions.py`: Handles browser-related actions like adding menus and context actions.
  - `config_dialog.py`: Provides the visual configuration UI and the Support tab for donations.
  - `config.json`: Default properties.
  - `conversion_dialog.py`: PyQt dialog housing the main interface for field mapping and target model selection.
  - `manifest.json`: Anki add-on manifest file.
  - `mapping.py`: Logic for field mapping validation, presets, and cloze stripping.
  - `operations.py`: Core logic for note conversion (create new, delete old) and undo handling.
  - `reviewer_actions.py`: Handles reviewer context-menu actions.
  - `state.py`: Manages global configuration state and constants.
  - `Support/`: Directory containing QR codes displayed in the Support tab.
- `bump.py`: Version helpers (`validate_version`, `sync_version`) and configurable semantic bumping (`major`/`minor`/`patch`, default `patch`).
- `make_ankiaddon.py`: Creates `.ankiaddon`; auto-bumps patch only when no explicit version is provided.

## Features Wired Into Anki

- **Browser & Reviewer Actions:** Adds conversion actions to the browser's Note menu, browser's right-click context menu, and reviewer's context menu.
- **Add-on Configuration Manager:** Replaces the default JSON editor with a tailored `QDialog` interface.
- **Note Addition API:** Native use of `mw.col.new_note()` and `mw.col.add_note()` to ensure stable compatibility with the Anki DB.

## Versioning Scheme

Version format is strictly:

```text
major.minor.patch
```

Behavior:

- `bump.py` validates semantic version format and syncs:
  - `manifest.json` keys: `version`, `human_version`
  - `addon/VERSION`
- `bump.py` can read current version and increment:
  - `patch`: `x.y.z` -> `x.y.(z+1)` (default)
  - `minor`: `x.y.z` -> `x.(y+1).0`
  - `major`: `x.y.z` -> `(x+1).0.0`
- `make_ankiaddon.py` behavior:
  - Without args: auto-bumps patch via `bump.py`, then packages.
  - With `<major.minor.patch>` arg: writes that version via `bump.py` sync helpers, then packages without bumping.

## Common Commands

Bump patch version:

```shell
python bump.py
```

Build `.ankiaddon` locally:

```shell
python make_ankiaddon.py
```

Build `.ankiaddon` with explicit version (no auto-bump):

```shell
python make_ankiaddon.py 1.5.0
```

Output naming format:

```text
No_Sync_Note_Converter_v<major.minor.patch>_<YYYYMMDDHHMM>.ankiaddon
```

## Local Testing With Symlink

Linux:

```shell
ln -s "$(pwd)/addon" ~/.local/share/Anki2/addons21/no_sync_converter_dev
```

Windows (PowerShell as admin):

```powershell
New-Item -ItemType SymbolicLink -Path "$env:APPDATA\Anki2\addons21\no_sync_converter_dev" -Target "$pwd\addon"
```
