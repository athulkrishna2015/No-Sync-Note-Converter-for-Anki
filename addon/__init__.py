from anki.hooks import addHook
from aqt import mw
from aqt.gui_hooks import (
    browser_will_show_context_menu,
    main_window_did_init,
    reviewer_will_show_context_menu,
)

from .browser_actions import setup_browser_context_menu, setup_browser_menu
from .config_dialog import open_config_gui, register_tools_config_action
from .reviewer_actions import setup_reviewer_menu
from .state import reload_config

addHook("browser.setupMenus", setup_browser_menu)
browser_will_show_context_menu.append(setup_browser_context_menu)
reviewer_will_show_context_menu.append(setup_reviewer_menu)
main_window_did_init.append(register_tools_config_action)
register_tools_config_action()
mw.addonManager.setConfigAction(__name__, open_config_gui)
mw.addonManager.setConfigUpdatedAction(__name__, reload_config)
