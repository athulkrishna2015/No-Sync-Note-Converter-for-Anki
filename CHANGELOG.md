# Changelog

All notable changes to **No-Sync Note Converter** are documented here. This file is updated from full git history (`git log --all`) and GitHub releases (`gh release list`).

## [Unreleased]
* Cleanup: remove duplicate `doc/` folder, keep canonical `docs/` (`b669cf5`).

## 2.0.0 — 2026-09-02 ([release](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/releases/tag/v2.0.0))
**Tag:** `v2.0.0` · **Commits:** `5803cdc`, `033c84c`, `5678ba1`

* **Config UI refactor:** each tab now lives in its own module (`addon/config_tabs/general.py`, `presets.py`, `mappings.py`, `log.py`, `tab_support.py` + `widgets.py`) — `5803cdc`.
* **Support tab:** new `tab_support.py` mixin with "I have supported this addon (Hide automatic update welcome)" checkbox (`meta.supporter_opt_out`); if unchecked, Support tab auto-opens on addon update (deferred via `main_window_did_init` + `QTimer.singleShot(1500)` to avoid blocking startup) — `033c84c`.
* **Live logs:** `LogTab` now tails `debug.log` live (polling + `QFileSystemWatcher`, interval control, auto-refresh only when visible) and shows cleared-on-startup session logs — `033c84c`.
* **Logger:** `addon/logger.py` with rotation (2 MiB, 3 backups), `clear_log_on_startup()` called on Anki start, `clear_log()` for manual clear — `5803cdc`/`033c84c`.
* **Build:** `make_ankiaddon.py` now gitignore-aware, respects `.gitignore`, excludes `*.log`/`meta.json`, clean via `--clean`; fixed `ADDON_NAME` to `No_Sync_Note_Converter`; `bump.py` supports `major/minor/patch` and `path` alias — `033c84c`/`5678ba1`.
* **Docs:** moved `CHANGELOG` from `README` to `CHANGELOG.md`, moved `DEVELOPMENT.md` to `docs/development.md`, added `docs/architecture.md` + `docs/configuration.md` with full module map, variables, defaults and JSON schemas; `README` now links to `docs/` — `033c84c`.

## 1.7.0 — 2026-04-02 ([release](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/releases/tag/v1.7.0))
**Tag:** `v1.7.0` · **Commit:** `7dc9e19`

* Added a **Use source deck as target deck** button in the main conversion dialog to quickly reset the destination to "Same as original".
* Updated conversion logic so that when "Same as original" is selected, each newly created card is placed in the exact subdeck/deck of its corresponding original card, instead of grouping them all into a single deck.

## 1.6.1 — 2026-04-01 ([release](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/releases/tag/v1.6.1))
**Tag:** `v1.6.1` · **Commit:** `9ce76fa`

* Fix crash: `AttributeError: 'Browser' object has no attribute 'onSearch'` on Anki 25.04+ where `onSearch` was renamed to `search`. Also handle `browser.search()` fallback.

## 1.6.0 — 2026-03-31 ([release](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/releases/tag/v1.6.0))
**Tag:** `v1.6.0` · **Commits:** `f7d33c3`, `5366ca8`

* **Preserve review history** toggle (enabled by default) — copies selected source card's scheduling state onto new card.
* **Use history from** picker — when source note has multiple cards, dropdown shows `Card 1`, `Card 2` + template name; choice remembered per source note type (`review_history_source_card_ord_by_model`).
* **Remembered card choice** reused for browser quick-convert; reviewer quick-convert defaults to current card's `ord`.
* **Unified multi-source dialog** — browser batch with mixed source note types now uses one shared `ConversionDialog` with source switcher (`allow_source_selection`).
* **Reviewer improvements** — `initial_review_history_card_ord_by_model` set to `card.ord`.
* Restored single-step undo (`add_custom_undo_entry` + `merge_undo_entries`).

## 1.5.1 — 2026-03-27 ([release](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/releases/tag/v1.5.1))
**Tag:** `v1.5.1` · **Commit:** `9c40b7e` (`ko-fi`)

* Added Ko-fi support widget/button and Support tab QR codes (UPI/BTC/ETH).

## 1.5.0 — 2026-03-24 ([release](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/releases/tag/v1.5.0))
**Tag:** `v1.5.0` · **Commit:** `a5a77f0`

* **Project standardization:** moved addon source to `addon/` directory.
* **Browser integration:** added conversion actions to `Notes` menu + right-click context menu; added `No-Sync Quick Convert` submenu.
* **New conversion options:** `Open notes after`, `Delete original`, `Strip clozes` checkboxes + `Target Deck` selector (default "Same as original"); all settings persisted via `state.config`.
* **Documentation:** updated `README.md`, `DEVELOPMENT.md`; modernized `bump.py` + `make_ankiaddon.py` with semantic versioning.

## 1.4.1 — 2026-03-10 ([release](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/releases/tag/NSNC-V1.4.1.ankiaddon))
**Tag:** `NSNC-V1.4.1.ankiaddon` · **Commits:** `7bf8a82`, `a220527`

* Added single-step undo (`add_custom_undo_entry`).
* Added `Tools → No-Sync Note Converter Config` action.
* Refactored addon into smaller modules (`state.py`, `mapping.py`, `operations.py`, etc.).

## 1.3.0 — 2026-03-09 ([release](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/releases/tag/NSNC-V1.3.0.ankiaddon))
**Tag:** `NSNC-V1.3.0.ankiaddon` · **Commit:** `b6350ca`

* Fixed conversion rollback — failed runs no longer leave partially converted notes (`db.transact` rollback).
* Fixed deck preservation — no longer mutates target note type's default deck.
* Fixed cloze stripping detection to use `type == MODEL_CLOZE` instead of name matching.
* Added validation for saved mappings/quick presets — stale field references now raise explicit error.
* Added GUI config editor behind Add-ons `Config` button.
* Updated config editor to allow source/target change inside preset/mapping edit window.

## 1.2 — 2026-02-21 ([release](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/releases/tag/1.2))
**Tag:** `1.2` · **Commits:** `5709daa`, `950a82c`

* Field mapping GUI + fix field loss issues (`950a82c`).
* Fix `AttributeError` for `QDialogButtonBox` in Qt6 (`5709daa`).

## 1.1 — 2026-01-29 ([release](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/releases/tag/1.1))
**Tag:** `1.1` · **Commits:** `c0ad95c`, `d80202d`

* Initial upload of No-Sync Note Converter (`c0ad95c`).
* Revised `README` for new Reviewer features and link update (`d80202d`).

---

## Git History Summary

```
c0ad95c Add files via upload
d80202d Revise README for new Reviewer features and link update          → 1.1
950a82c Add field mapping GUI and fix field loss issues
5709daa Fix AttributeError for QDialogButtonBox in Qt6                     → 1.2
b6350ca Add files via upload                                               → NSNC-V1.3.0
a220527 Update README.md
7bf8a82 Add files via upload                                               → NSNC-V1.4.1
a5a77f0 Standardize project structure and release v1.5.0                  → v1.5.0
9c40b7e ko-fi                                                              → v1.5.1
f7d33c3 Release v1.6.0: Review history preservation...                     → v1.6.0
5366ca8 Update README.md
9ce76fa chore: release v1.6.1                                              → v1.6.1
7dc9e19 Release v1.7.0                                                     → v1.7.0
5803cdc refactor: split config UI tabs into separate modules...
033c84c feat: live logs, non-blocking update check, docs restructure...   → v2.0.0 (via 5678ba1)
5678ba1 Release v2.0.0                                                      → v2.0.0
b669cf5 cleanup: remove duplicate doc/ folder, keep canonical docs/       → Unreleased
```

GitHub releases: 10 releases (1.1, 1.2, NSNC-V1.3.0, NSNC-V1.4.1, v1.5.0, v1.5.1, v1.6.0, v1.6.1, v1.7.0, v2.0.0). `CHANGELOG.md` now mirrors all.
