# -*- coding: utf-8 -*-
from aqt import mw

try:
    ADDON_PACKAGE = mw.addonManager.addonFromModule(__name__)
except Exception:
    ADDON_PACKAGE = None

if not ADDON_PACKAGE:
    # Fallback: derive top-level package from __name__ (addon.config_tabs.widgets -> addon)
    ADDON_PACKAGE = __name__.split(".")[0]
