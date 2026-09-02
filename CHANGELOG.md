# Changelog

All notable changes to **No-Sync Note Converter** are documented here.

## 2.0.0 — 02-09-2026
* **Config UI refactor:** each tab now lives in its own module (`addon/config_tabs/general.py`, `presets.py`, `mappings.py`, `log.py`, `tab_support.py` + `widgets.py`).
* **Support tab:** new `tab_support.py` mixin with "I have supported this addon (Hide automatic update welcome)" checkbox (`meta.supporter_opt_out`); if unchecked, Support tab auto-opens on addon update (deferred via `main_window_did_init` + `QTimer.singleShot` to avoid blocking startup).
* **Live logs:** `LogTab` now tails `debug.log` live (polling + `QFileSystemWatcher`, interval control, auto-refresh only when visible) and shows cleared-on-startup session logs.
* **Logger:** `addon/logger.py` with rotation (2 MiB, 3 backups), `clear_log_on_startup()` called on Anki start, `clear_log()` for manual clear.
* **Build:** `make_ankiaddon.py` now gitignore-aware, respects `.gitignore`, excludes `*.log`/`meta.json`, clean via `--clean`; fixed `ADDON_NAME` to `No_Sync_Note_Converter`; `bump.py` supports `major/minor/patch`.
* **Docs:** moved `CHANGELOG` from `README` to `CHANGELOG.md`, moved `DEVELOPMENT.md` to `docs/development.md` (mirrored in `doc/`), added `docs/architecture.md` + `docs/configuration.md` with full module map, variables, defaults and JSON schemas; `README` now links to `docs/`.

## 02-04-2026
* Added a **Use source deck as target deck** button in the main conversion dialog to quickly reset the destination to "Same as original".
* Updated the conversion logic so that when "Same as original" is selected, each newly created card is placed in the exact subdeck/deck of its corresponding original card, instead of grouping them all into a single deck.

## 01-04-2026
* Fixed a crash in newer Anki versions where the Browser `onSearch` method was renamed to `search`.
* Updated browser batch conversion so mixed source note types can be configured from one shared conversion dialog instead of opening a separate dialog for each source type.
* Fixed reviewer conversions so multi-card notes default review-history preservation to the currently reviewed card.
* Restored single-step undo for conversions.

## 31-03-2026
* Added a **Preserve review history** toggle to the main conversion dialog, enabled by default.
* Added a **Use history from** picker that appears when the source note has multiple current cards and shows card numbers in the dropdown, plus the template name when available.
* Preserved the selected source card's scheduling on the merged card.
* Remembered the selected history-source card per source note type and reused it for browser quick-convert actions.

## 24-03-2026
* **Enhanced Browser Integration:** Added conversion actions directly to the browser's right-click context menu.
* **New Conversion Options:** Added checkboxes to control whether to open notes in the browser after conversion, delete original notes, and strip clozes.
* **Deck Selection:** Added the ability to choose a target deck for converted notes (defaults to the original deck).
* **Setting Persistence:** All conversion options are now remembered for the next use.
* **Project Standardization:** Renamed internal package components and updated build scripts for consistency as "No-Sync Note Converter."

## 10-03-2026
* Added single-step undo for note conversion, so one **Edit -> Undo** restores the previous notes/cards.
* Added a direct **Tools -> No-Sync Note Converter Config** action.
* Refactored the addon into smaller modules to make the codebase easier to maintain.

## 09-03-2026
* Fixed conversion rollback so failed runs do not leave partially converted notes behind.
* Fixed deck preservation so conversions no longer mutate the target note type's default deck.
* Fixed cloze stripping detection to use the real note type kind instead of matching names like `"Cloze"` or `"Basic"`.
* Added validation for saved mappings and quick presets so stale field references are blocked with an explicit error instead of silently dropping content.
* Added a GUI config editor behind the Add-ons **Config** button for managing presets and mappings with the existing conversion dialog.
* Updated the config editor so source note type can be changed inside the preset/mapping edit window without a separate source picker.

## 22-02-2026
* Fixed Cloze-to-Basic cloze stripping so MathJax/LaTeX content with nested braces is preserved correctly (prevents broken formulas like `\mathbf{E}` / `\frac{...}{...}` after conversion).
