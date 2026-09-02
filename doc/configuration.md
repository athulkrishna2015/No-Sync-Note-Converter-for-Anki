# Configuration

## Files

| Path | Purpose | Shipped | Runtime |
|------|---------|---------|---------|
| `addon/config.json` | Default config shipped in package | Yes | Copied to Anki meta on first install |
| `addon/manifest.json` | Anki manifest (`name`, `package`, `version`, `human_version`) | Yes | Read for update detection |
| `addon/VERSION` | Single-line version `1.7.0` | Yes | Primary source for `_get_current_version()` |
| `addon/debug.log` | Session log (cleared on Anki start) | No (created) | `addon/logger.py` 2 MiB rotation, 3 backups (`debug.log.1`..`.3`) |
| `meta.json` (Anki managed, not in repo) | Holds `config` + `supporter_opt_out`, `last_seen_version` | No | `mw.addonManager.addonMeta(ADDON_PACKAGE)` |

`.gitignore` ignores `meta.json`, `*.log`, `debug.log*`, `*.ankiaddon`, `__pycache__`. `make_ankiaddon.py` also excludes those via `load_gitignore_patterns()` plus explicit `meta.json`, `*.log`, `.log.*`.

## `addon/config.json` Keys & Defaults

Shipped defaults (`state.ensure_config_defaults()` supplements missing keys):

```json
{
  "toggle_strip_cloze": true,
  "preserve_review_history": true,
  "review_history_source_card_ord_by_model": {},
  "preferred_target_models": {},
  "quick_convert_presets": [],
  "mappings": {
    "Basic->Cloze": {
      "source_type": "Basic",
      "target_type": "Cloze",
      "field_map": { "Text": ["Front", "Back"], "Extra": ["Extra"] }
    },
    "Cloze->Basic": {
      "source_type": "Cloze",
      "target_type": "Basic",
      "field_map": { "Front": ["Text"], "Back": ["Extra"] }
    }
  }
}
```

### Full Key Reference (all keys after `ensure_config_defaults()`)

| JSON Key | Type | Default | Description |
|----------|------|---------|-------------|
| `toggle_strip_cloze` | `bool` | `true` | Strip `{{c1::...::hint}}` → answer when converting Cloze → non-Cloze. Used in `operations.core_convert_logic()` via `mapping.strip_cloze_tags()` (brace-depth aware, preserves LaTeX). Checkbox in GeneralTab and conversion dialog Options. |
| `preserve_review_history` | `bool` | `true` | Default for `ConversionDialog.preserve_review_history_cb`. When true, `_preserve_review_history()` copies scheduling. Persisted via dialog `accept()` and config tab. |
| `review_history_source_card_ord_by_model` | `object<string,int>` | `{}` | Remembered card choice per source note type, value is zero-based ord (`0=Card1`). Populated from dialog `review_history_source_combo.currentData()` and saved via `state.config["review_history_source_card_ord_by_model"]`. Used by `operations._get_preferred_review_history_ord()` and `browser_actions` quick-convert. |
| `preferred_target_models` | `object<string,string>` | `{}` | Last target per source (`"Basic": "Cloze"`). Updated by `mapping.remember_conversion_pair()`. Drives `get_default_target_model_name()` and conversion dialog `target_combo` default. |
| `quick_convert_presets` | `list<preset>` | `[]` | Named presets. Each `{name, source_type, target_type, field_map}`. Managed via Config → Quick Presets tab and conversion dialog Save Quick Preset. Filtered by `get_quick_convert_presets(source)` for menu. |
| `mappings` | `object<string,entry>` | `{"Basic->Cloze":{...},"Cloze->Basic":{...}}` | Permanent `Source->Target` entries, key is `f"{source}->{target}"`, value `{source_type, target_type, field_map}`. Used by `get_effective_field_map()` as fallback; validated via `validate_field_map()`. |
| `open_notes_after` | `bool` | `true` | Added by `ensure_config_defaults()` if missing. When true, `finish_browser_conversion()` or `dialogs.open("Browser")` opens new notes. Checkbox in both dialogs. |
| `delete_original` | `bool` | `true` | When true, `mw.col.remove_notes([nid])` after creation (zero-sync). Checkbox in both dialogs. |
| `target_deck_id` | `int|null` | `null` | `null` = "Same as original" per-card `did`. Else fixed deck id. Populated from `deck_combo.currentData()`. |
| `mappings` (see above) |  |  |  |
| `preferred_target_models` |  |  |  |

### Preset Entry Schema

```json
{
  "name": "Basic -> Cloze (Merged front+back)",
  "source_type": "Basic",
  "target_type": "Cloze",
  "field_map": {
    "Text": ["Front", "Back"],
    "Back": ["Back Extra"],
    "Back Extra": []
  }
}
```

* `name` – display, unique together with `(source_type,target_type)`. `format_quick_preset_label()` hides route if already in name.
* `field_map` – `target_field → [source_fields]` ordered; joined with `"<br><br>"` in `operations`.

### Mapping Entry Schema

```json
"Source->Target": {
  "source_type": "Cloze",
  "target_type": "Basic",
  "field_map": { "Front": ["Text"], "Back": ["Extra"] }
}
```

* Normalized by `normalize_field_map()` (string→[string], filters empty).
* Validated against `source_model["flds"]` and `target_model["flds"]` – raises with `unknown target/source fields`.

## `addon/meta.json` (Anki runtime, not shipped)

Managed by `mw.addonManager.addonMeta(ADDON_PACKAGE)` where `ADDON_PACKAGE` from `addon/config_tabs/widgets.py` (`addonFromModule(__name__)`).

| Meta Key | Type | Default | Writer |
|----------|------|---------|--------|
| `config` | object | see above | `state.save_config()` via `writeConfig` |
| `supporter_opt_out` | `bool` | `false` | `config_tabs/tab_support.py:SupportTabMixin.on_supporter_check_toggled()` checkbox "I have supported this addon (Hide automatic update welcome)" |
| `last_seen_version` | `string` | `""` (first run) | `__init__._maybe_show_support_on_update()` stores current `VERSION` after each start; used to detect update |
| `last_version` | alias | – | Read as fallback for `last_seen_version` |

## `addon/state.py` Variables & Constants

```python
ADDON_NAME = "No-Sync Note Converter"
TOOLS_MENU_OBJECT = "no_sync_note_converter_tools_menu"
TOOLS_CONFIG_ACTION_OBJECT = "no_sync_note_converter_config_action"
SUPPORT_QR_WIDTH = 460
SUPPORT_ITEMS = [
  {"label":"UPI","value":"athulkrishnasv2015-2@okhdfcbank","image":"UPI.jpg"},
  {"label":"BTC","value":"bc1q...","image":"BTC.jpg"},
  {"label":"ETH","value":"0x...","image":"ETH.jpg"},
]
SUPPORT_DIR = Path(__file__).parent / "Support"
config = mw.addonManager.getConfig(__name__) or {}
```

* `save_config()` → `writeConfig(__name__, config)`
* `reload_config(new)` → deepcopy + `ensure_config_defaults()`
* `ensure_config_defaults()` – idempotently adds missing keys, normalizes `quick_convert_presets` (drops entries missing name/source/target/field_map), normalizes `review_history_source_card_ord_by_model` (int ≥0), sets `target_deck_id=None` if absent, calls `save_config()` if changed.

## `addon/logger.py` Variables

```python
LOG_FILE = Path(__file__).parent / "debug.log"
LOG_MAX_BYTES = 2*1024*1024
LOG_BACKUP_COUNT = 3
_logger = singleton
```

* `info/debug/warning/error(msg, *args, exc_info)` auto-`_rotate_if_needed()`
* `clear_log()` flushes handlers, `write_text("")`, logs "Log cleared by user"
* `clear_log_on_startup()` silent truncate (called in `__init__.py` on Anki start)

## Conversion Dialog `get_settings()` Return

```python
{
  "open_notes_after": bool,
  "delete_original": bool,
  "preserve_review_history": bool,
  "review_history_source_card_ord": int|None,  # None for multi-source
  "review_history_source_card_ord_by_model": {model: ord},
  "toggle_strip_cloze": bool,
  "target_deck_id": int|None
}
```

Passed as `override_settings` to `core_convert_logic()`.

## Environment & Build

* `bump.py` `VERSION_RE = r"^\d+\.\d+(?:\.\d+)?$"`, `sync_version()` writes both `manifest.json` (`version`, `human_version`) and `VERSION`; `increment_version(part)` for `major` (`x.0`), `minor` (`x.y`), `patch` (`x.y.z+1`).
* `make_ankiaddon.py` `ADDON_NAME="No_Sync_Note_Converter"`, `ADDON_DIR="addon"`, `load_gitignore_patterns()`, `is_ignored()`, artifact `No_Sync_Note_Converter_v<ver>_<timestamp>.ankiaddon`, `--clean` flag.
