import copy
from pathlib import Path

from aqt import mw

ADDON_NAME = "No-Sync Note Converter"
TOOLS_MENU_OBJECT = "no_sync_note_converter_tools_menu"
TOOLS_CONFIG_ACTION_OBJECT = "no_sync_note_converter_config_action"
SUPPORT_QR_WIDTH = 460
SUPPORT_ITEMS = [
    {
        "label": "UPI",
        "value": "athulkrishnasv2015-2@okhdfcbank",
        "image": "UPI.jpg",
    },
    {
        "label": "BTC",
        "value": "bc1qrrek3m7sr33qujjrktj949wav6mehdsk057cfx",
        "image": "BTC.jpg",
    },
    {
        "label": "ETH",
        "value": "0xce6899e4903EcB08bE5Be65E44549fadC3F45D27",
        "image": "ETH.jpg",
    },
]
SUPPORT_DIR = Path(__file__).resolve().parent / "Support"

config = mw.addonManager.getConfig(__name__) or {}


def save_config():
    mw.addonManager.writeConfig(__name__, config)


def reload_config(new_config=None):
    global config
    config = copy.deepcopy(new_config or mw.addonManager.getConfig(__name__) or {})
    ensure_config_defaults()


def ensure_config_defaults():
    changed = False

    if not isinstance(config.get("mappings"), dict):
        config["mappings"] = {}
        changed = True

    if not isinstance(config.get("preferred_target_models"), dict):
        config["preferred_target_models"] = {}
        changed = True

    presets = config.get("quick_convert_presets")
    normalized_presets = []
    if isinstance(presets, list):
        for preset in presets:
            if not isinstance(preset, dict):
                continue
            name = str(preset.get("name", "")).strip()
            source_type = str(preset.get("source_type", "")).strip()
            target_type = str(preset.get("target_type", "")).strip()
            field_map = preset.get("field_map")
            if name and source_type and target_type and isinstance(field_map, dict):
                normalized_presets.append(
                    {
                        "name": name,
                        "source_type": source_type,
                        "target_type": target_type,
                        "field_map": field_map,
                    }
                )
    if presets != normalized_presets:
        config["quick_convert_presets"] = normalized_presets
        changed = True

    if "toggle_strip_cloze" not in config:
        config["toggle_strip_cloze"] = True
        changed = True

    if "open_notes_after" not in config:
        config["open_notes_after"] = True
        changed = True

    if "delete_original" not in config:
        config["delete_original"] = True
        changed = True

    if "target_deck_id" not in config:
        config["target_deck_id"] = None  # None means "same as original"
        changed = True

    if changed:
        save_config()


ensure_config_defaults()
