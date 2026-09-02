from pathlib import Path
import json

from anki.hooks import addHook
from aqt import mw
from aqt.gui_hooks import (
    browser_will_show_context_menu,
    main_window_did_init,
    reviewer_will_show_context_menu,
)

from . import logger
from .browser_actions import setup_browser_context_menu, setup_browser_menu
from .config_dialog import open_config_gui, register_tools_config_action
from .reviewer_actions import setup_reviewer_menu
from .state import reload_config

# Clear log file on Anki start (fresh log per session as requested)
try:
    logger.clear_log_on_startup()
except Exception:
    pass

logger.info("Addon loaded: No-Sync Note Converter - session start, log cleared on Anki start")


def _get_current_version() -> str:
    try:
        version_file = Path(__file__).resolve().parent / "VERSION"
        if version_file.exists():
            v = version_file.read_text(encoding="utf-8").strip()
            if v:
                return v
    except Exception as e:
        logger.debug(f"Failed to read VERSION file: {e}")

    try:
        manifest_path = Path(__file__).resolve().parent / "manifest.json"
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for key in ("human_version", "version"):
                v = str(data.get(key, "")).strip()
                if v:
                    return v
    except Exception as e:
        logger.debug(f"Failed to read manifest version: {e}")
    return ""


def _maybe_show_support_on_update(*_args, **_kwargs):
    """Lightweight update check - file reads only; UI is deferred to avoid blocking startup."""
    try:
        from .config_tabs.widgets import ADDON_PACKAGE

        current = _get_current_version()
        if not current:
            logger.debug("Update check: could not determine current version")
            return

        try:
            meta = mw.addonManager.addonMeta(ADDON_PACKAGE)
        except Exception as e:
            logger.debug(f"Update check: failed to get addonMeta: {e}")
            return

        last_seen = str(meta.get("last_seen_version") or meta.get("last_version") or "").strip()
        if not last_seen:
            # First run: store current without showing
            meta["last_seen_version"] = current
            try:
                mw.addonManager.writeAddonMeta(ADDON_PACKAGE, meta)
                logger.info(f"First run: storing version {current} without showing support tab")
            except Exception as e:
                logger.debug(f"Failed to store first version: {e}")
            return

        if last_seen == current:
            logger.debug(f"Update check: version unchanged ({current})")
            return

        # Version changed -> update
        supporter_opt_out = bool(meta.get("supporter_opt_out", False))
        logger.info(f"Addon update detected: {last_seen} -> {current} (supporter_opt_out={supporter_opt_out})")

        # Always update stored version before possibly showing UI
        meta["last_seen_version"] = current
        try:
            mw.addonManager.writeAddonMeta(ADDON_PACKAGE, meta)
        except Exception as e:
            logger.debug(f"Failed to update stored version: {e}")

        if supporter_opt_out:
            logger.info("Update notice suppressed (I have supported this addon checked)")
            return

        # Defer UI opening until event loop is idle - must not block Anki startup
        try:
            from aqt.qt import QTimer

            def _open():
                try:
                    logger.info("Opening config UI on Support tab due to addon update")
                    open_config_gui(initial_tab="support")
                except Exception as e:
                    logger.error(f"Failed to open support tab on update: {e}", exc_info=True)

            # 1.5s delay lets Anki finish startup painting before showing dialog
            QTimer.singleShot(1500, _open)
        except Exception as e:
            logger.error(f"Failed to schedule support tab open: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"_maybe_show_support_on_update failed: {e}", exc_info=True)


def _on_main_window_init(*args, **kwargs):
    """Wrapper that defers update check to avoid blocking main_window_did_init."""
    try:
        register_tools_config_action(*args, **kwargs)
        # Defer heavy-ish check (file IO + meta) to next event loop tick
        from aqt.qt import QTimer

        QTimer.singleShot(300, _maybe_show_support_on_update)
    except Exception as e:
        logger.debug(f"_on_main_window_init failed: {e}")
        try:
            register_tools_config_action(*args, **kwargs)
        except Exception:
            pass


addHook("browser.setupMenus", setup_browser_menu)
browser_will_show_context_menu.append(setup_browser_context_menu)
reviewer_will_show_context_menu.append(setup_reviewer_menu)
main_window_did_init.append(_on_main_window_init)
# Also register immediately for cases where main_window_did_init has already fired (e.g., reload)
try:
    register_tools_config_action()
except Exception:
    pass
mw.addonManager.setConfigAction(__name__, open_config_gui)
mw.addonManager.setConfigUpdatedAction(__name__, reload_config)
