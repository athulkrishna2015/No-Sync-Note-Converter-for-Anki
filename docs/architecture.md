# Architecture

## Overview

No-Sync Note Converter avoids a full AnkiWeb sync by using **Create New → Delete Old** rather than mutating the note-type schema. Every conversion is wrapped in a single DB transaction + single custom undo entry, so `Edit → Undo` is atomic.

```
User selects notes (Browser) or card (Reviewer)
        → conversion_dialog.py (field mapping + options)
        → browser_actions.py / reviewer_actions.py (remember pair, delegate)
        → operations.core_convert_logic() (new_note, add_note, preserve scheduling/tags/decks, delete old, merge undo)
        → state.save_config() + logger
```

## Module Map

| Module | File | Responsibility |
|--------|------|---------------|
| Entrypoint | `addon/__init__.py` | Hook registration, log clear on start, update detection for Support tab, `setConfigAction` |
| State | `addon/state.py` | `ADDON_NAME`, `TOOLS_MENU_OBJECT`, `SUPPORT_ITEMS`, `SUPPORT_DIR`, `config` dict, `ensure_config_defaults()`, `save_config()`/`reload_config()` |
| Logger | `addon/logger.py` | `LOG_FILE=addon/debug.log` (2 MiB rotation, 3 backups), `debug/info/warning/error()`, `read_log_text()`, `clear_log()`, `clear_log_on_startup()`, `_rotate_if_needed()` |
| Mapping | `addon/mapping.py` | `strip_cloze_tags()` (brace-depth aware), `normalize_field_map()`, `validate_field_map()`, `get_effective_field_map()`, preset helpers `save_quick_convert_preset()`, `get_quick_convert_presets()` |
| Operations | `addon/operations.py` | `core_convert_logic()`, `group_note_ids_by_model()`, `finish_browser_conversion()`, `_preserve_review_history()`, `_copy_card_scheduling()` |
| Conversion UI | `addon/conversion_dialog.py` | `ConversionDialog` (source/target combo, deck combo, options, dynamic field rows, review-history picker), `show_conversion_dialog()`, `show_multi_source_conversion_dialog()` |
| Config UI | `addon/config_dialog.py` | `AddonConfigDialog(QDialog, SupportTabMixin)` orchestrates `QTabWidget` tabs, `edit_mapping_dialog()`, `open_config_gui(initial_tab)` |
| Config Tabs | `addon/config_tabs/*.py` | `GeneralTab`, `PresetsTab`, `MappingsTab`, `LogTab`, `SupportTabMixin` (`tab_support.py`) + `widgets.py` (`ADDON_PACKAGE`) |
| Browser | `addon/browser_actions.py` | `on_browser_convert()` (single vs multi-source), `on_browser_quick_convert()`, `populate_browser_quick_convert_menu()`, `setup_browser_menu/context` |
| Reviewer | `addon/reviewer_actions.py` | `on_reviewer_convert()`, `on_reviewer_quick_convert()`, `setup_reviewer_menu()` |

## Key Data Flows

### Browser batch (single source type)
`selectedNotes() → group_note_ids_by_model() → show_conversion_dialog() → remember_conversion_pair() → core_convert_logic() → finish_browser_conversion()`

### Browser batch (multi-source)
`selectedNotes() → notes_by_mid → show_multi_source_conversion_dialog() → conversion_plans: {source_name: {target_model, mapping}} per source → loop core_convert_logic per mid → merge all_created_nids → browser.search()`

### Reviewer single
`reviewer.card → note_type() → show_conversion_dialog(initial_review_history_card_ord_by_model={model: card.ord}) → core_convert_logic([nid], ..., override_settings={"review_history_source_card_ord": card.ord}) → reviewer.nextCard() → Browser(open)`

### Quick Convert
`preset stored in state.config["quick_convert_presets"] → browser/reviewer quick menu filtered by source_type → core_convert_logic(override_mapping=preset.field_map)` (reviewer injects current card ord)

## Conversion Dialog State (`conversion_dialog.py`)

* `available_model_names`, `available_source_model_names`, `old_model`, `old_fields`, `active_source_name/target_name`, `temp_mappings`, `target_model_names_by_source`, `sample_note_ids_by_model`, `review_history_card_ords`
* `build_mapping_rows()` creates per-target-field `QComboBox` rows + `Add source field` / `Remove`
* `get_default_sources()` heuristics: `Text→Front`, `Extra/Back Extra→Back`
* `remember_conversion_pair()` + `preferred_target_models` persists default target per source
* `review_history` UI: `preserve_review_history_cb` toggles row visibility; `build_review_history_card_choices()` uses sample note's `cards()` or `tmpls`

## Operations Detail (`operations.py`)

* `mw.col.add_custom_undo_entry("Convert Note Type")` + `db.transact(convert_notes)` + `merge_undo_entries`
* Per `nid`: `get_effective_field_map()` (validate or fallback to field-name match), `new_note[target]= "<br><br>".join(sources)` with optional `strip_cloze_tags` when `source_is_cloze and not target_is_cloze`
* Deck handling: `deck_id = settings.target_deck_id or old_cards[0].did`; if `target_deck_id is None`, each new card's `did` is patched to source card's `did` per `ord`
* Tags: `new_note.tags = old_note.tags`
* Scheduling: `_preserve_review_history()` picks `source_card = card_by_ord(preferred) or cards[0]`, `target_card = card_by_ord(source.ord) or cards[0]`, `_copy_card_scheduling()` copies `type,queue,due,ivl,factor,reps,lapses,left,odue,odid,flags,custom_data,memory_state,desired_retention,decay,last_review_time`, `update_card()`
* Delete old: `mw.col.remove_notes([nid])` if `delete_original`

## Config Dialog Tabs

* `GeneralTab(QWidget)` (`general.py`): `open_after_checkbox`, `delete_original_checkbox`, `preserve_review_history_checkbox`, `strip_cloze_checkbox`, `deck_combo` ("Same as original" + `decks.all_names_and_ids()`).
* `PresetsTab(QWidget)` (`presets.py`): `preset_list`, `upsert_preset()` (dedup by `(name,source,target)`), `add/edit/delete` via `parent.edit_mapping_dialog()`.
* `MappingsTab(QWidget)` (`mappings.py`): similar for `working_mappings` dict keyed `"{source}->{target}"`.
* `LogTab(QWidget)` (`log.py`): `QPlainTextEdit` + Refresh/Clear/Copy/Reveal; reads `logger.read_log_text()`, truncates last 500 kB.
* `SupportTabMixin` (`tab_support.py`): `_create_support_tab()` builds instruction, `supporter_check` (meta `supporter_opt_out`), scroll QR list, `AnkiWebView` Ko-fi widget; `load_supporter_state()` / `on_supporter_check_toggled()` read/write `mw.addonManager.addonMeta(ADDON_PACKAGE)`.
* `widgets.py`: `ADDON_PACKAGE = addonFromModule(__name__) or __name__.split('.')[0]`.

`AddonConfigDialog` stores `working_toggle_strip_cloze`, `working_presets`, `working_mappings` as deep copies; `accept()` writes back to `state.config` + `save_config()`.

## State & Constants (`state.py`)

* `ADDON_NAME = "No-Sync Note Converter"`
* `TOOLS_MENU_OBJECT`, `TOOLS_CONFIG_ACTION_OBJECT`
* `SUPPORT_QR_WIDTH=460`, `SUPPORT_ITEMS=[UPI,BTC,ETH]`, `SUPPORT_DIR=addon/Support`
* `config = getConfig(__name__) or {}` + `ensure_config_defaults()` called at import.

## Logger (`logger.py`)

* `LOG_FILE = Path(__file__).parent / "debug.log"`
* `_get_logger()` lazy singleton `logging.getLogger("no_sync_note_converter")` + `FileHandler(LOG_FILE)` + formatter `%Y-%m-%d %H:%M:%S [LEVEL] msg`
* `_rotate_if_needed()` when `>2 MiB`: `debug.log → debug.log.1 → .2 → .3`
* Session: `__init__.py` calls `clear_log_on_startup()` on import, truncates file while keeping handler, then logs `Addon loaded ... log cleared on Anki start`.

## Hooks (`__init__.py`)

```python
addHook("browser.setupMenus", setup_browser_menu)
browser_will_show_context_menu.append(setup_browser_context_menu)
reviewer_will_show_context_menu.append(setup_reviewer_menu)
main_window_did_init.append(register_tools_config_action)
main_window_did_init.append(_maybe_show_support_on_update)
mw.addonManager.setConfigAction(__name__, open_config_gui)
mw.addonManager.setConfigUpdatedAction(__name__, reload_config)
```

* `_maybe_show_support_on_update` compares `VERSION`/`manifest.json` vs `meta["last_seen_version"]`; if changed and `not supporter_opt_out`, `QTimer.singleShot(1200, open_config_gui(support))`.

## Build Tools

* `bump.py`: `validate_version`, `sync_version(manifest.json + VERSION)`, `increment_version(major/minor/patch)`, CLI `python bump.py [major|minor|patch]`.
* `make_ankiaddon.py`: `ADDON_NAME="No_Sync_Note_Converter"`, `load_gitignore_patterns()`, `is_ignored()`, excludes `meta.json`, `*.log`, `.log.*`, `__pycache__`, packages `addon/` → `No_Sync_Note_Converter_vX.Y.Z_YYYYMMDDHHMM.ankiaddon`; `--clean` removes old packages.

## Support Assets

`addon/Support/UPI.jpg`, `BTC.jpg`, `ETH.jpg` rendered in both config Support tab and `conversion_dialog`? Actually only config.

## Version / Manifest

* `addon/VERSION` single line `1.7.0`
* `addon/manifest.json` `{name, package, version, human_version}`
* `addon/config.json` shipped defaults (see configuration.md)

## Error Handling

* `validate_field_map` raises `ValueError` with stale field list → `core_convert_logic` catches and `showInfo("... No notes were converted.")`, returns `[]`, progress finishes, undo not merged.
* `_preserve_review_history` is best-effort (`except: return` / log warning).
* `edit_mapping_dialog` catches `ValueError` for missing source model.

