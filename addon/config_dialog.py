import copy

from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

from . import logger, state
from .config_tabs.general import GeneralTab
from .config_tabs.log import LogTab
from .config_tabs.mappings import MappingsTab
from .config_tabs.presets import PresetsTab
from .config_tabs.tab_support import SupportTabMixin
from .conversion_dialog import ConversionDialog


class AddonConfigDialog(QDialog, SupportTabMixin):
    def __init__(self, parent, initial_tab=None):
        super().__init__(parent)
        self.working_toggle_strip_cloze = bool(
            state.config.get("toggle_strip_cloze", True)
        )
        self.working_presets = copy.deepcopy(
            state.config.get("quick_convert_presets", [])
        )
        self.working_mappings = copy.deepcopy(state.config.get("mappings", {}))
        self._initial_tab = initial_tab

        self.setWindowTitle(f"{state.ADDON_NAME} Config")
        self.setMinimumWidth(780)
        self.setMinimumHeight(560)
        self.setup_ui()
        logger.info("Config dialog opened (initial_tab=%s)", initial_tab)

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.general_tab = GeneralTab(
            self, working_toggle_strip_cloze=self.working_toggle_strip_cloze
        )
        self.tabs.addTab(self.general_tab, "General")

        self.presets_tab = PresetsTab(self)
        self.tabs.addTab(self.presets_tab, "Quick Presets")

        self.mappings_tab = MappingsTab(self)
        self.tabs.addTab(self.mappings_tab, "Mappings")

        # Support tab via mixin (creates self.support_tab and self.supporter_check)
        self._create_support_tab()
        self.tabs.addTab(self.support_tab, "Support")

        self.log_tab = LogTab(self)
        self.tabs.addTab(self.log_tab, "Logs")

        # Handle initial tab selection
        if self._initial_tab == "support":
            self.tabs.setCurrentWidget(self.support_tab)
        elif self._initial_tab == "logs":
            self.tabs.setCurrentWidget(self.log_tab)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # Shared helper used by PresetsTab / MappingsTab
    def edit_mapping_dialog(
        self,
        source_model_name,
        *,
        initial_target_model_name=None,
        initial_mapping=None,
        window_title,
        title_html,
    ):
        try:
            dialog = ConversionDialog(
                self,
                mw.col.models.by_name(source_model_name) if source_model_name else None,
                initial_source_model_name=source_model_name,
                initial_target_model_name=initial_target_model_name,
                initial_mapping=initial_mapping,
                allow_source_selection=True,
                show_save_preset_button=False,
                window_title=window_title,
                title_html=title_html,
            )
        except ValueError as exc:
            logger.error(f"edit_mapping_dialog failed: {exc}", exc_info=True)
            showInfo(str(exc))
            return None, None, None
        if not dialog.exec():
            logger.debug("edit_mapping_dialog cancelled: %s", window_title)
            return None, None, None

        source_model = dialog.get_source_model()
        if not source_model:
            return None, None, None
        logger.debug(
            "edit_mapping_dialog success: %s -> %s",
            source_model["name"],
            dialog.get_target_model()["name"] if dialog.get_target_model() else "?",
        )
        return source_model["name"], dialog.get_target_model(), dialog.get_mapping()

    # Backward-compatible delegations (in case external code calls them)
    def refresh_preset_list(self):
        if hasattr(self, "presets_tab"):
            self.presets_tab.refresh()

    def refresh_mapping_list(self):
        if hasattr(self, "mappings_tab"):
            self.mappings_tab.refresh()

    def selected_preset_index(self):
        return self.presets_tab.selected_preset_index() if hasattr(self, "presets_tab") else None

    def selected_mapping_key(self):
        return self.mappings_tab.selected_mapping_key() if hasattr(self, "mappings_tab") else None

    def accept(self):
        state.config["open_notes_after"] = self.general_tab.open_after_checkbox.isChecked()
        state.config["delete_original"] = self.general_tab.delete_original_checkbox.isChecked()
        state.config["preserve_review_history"] = (
            self.general_tab.preserve_review_history_checkbox.isChecked()
        )
        state.config["toggle_strip_cloze"] = self.general_tab.strip_cloze_checkbox.isChecked()
        state.config["target_deck_id"] = self.general_tab.deck_combo.currentData()
        state.config["quick_convert_presets"] = copy.deepcopy(self.working_presets)
        state.config["mappings"] = copy.deepcopy(self.working_mappings)
        state.save_config()
        logger.info(
            "Config saved: open_after=%s delete_original=%s preserve_history=%s strip_cloze=%s deck=%s presets=%d mappings=%d",
            state.config["open_notes_after"],
            state.config["delete_original"],
            state.config["preserve_review_history"],
            state.config["toggle_strip_cloze"],
            state.config["target_deck_id"],
            len(self.working_presets),
            len(self.working_mappings),
        )
        super().accept()


def open_config_gui(*_args, initial_tab=None, **_kwargs):
    # Allow initial_tab via kwargs or via mw.addonManager dialog trigger (Anki calls with no args)
    # Support both open_config_gui(initial_tab="support") and plain call
    logger.info("open_config_gui triggered (initial_tab=%s)", initial_tab)
    dialog = AddonConfigDialog(mw, initial_tab=initial_tab)
    dialog.exec()
    return True


def register_tools_config_action(*_args):
    if not hasattr(mw, "form") or not hasattr(mw.form, "menuTools"):
        return

    tools_menu = mw.form.menuTools
    action_label = f"{state.ADDON_NAME} Config"

    for action in list(tools_menu.actions()):
        menu = action.menu()
        if menu and (
            menu.objectName() == state.TOOLS_MENU_OBJECT
            or menu.title() == state.ADDON_NAME
        ):
            tools_menu.removeAction(action)
            menu.deleteLater()
            continue
        if (
            action.objectName() == state.TOOLS_CONFIG_ACTION_OBJECT
            or action.text() == action_label
        ):
            tools_menu.removeAction(action)
            action.deleteLater()

    config_action = QAction(action_label, tools_menu)
    config_action.setObjectName(state.TOOLS_CONFIG_ACTION_OBJECT)
    config_action.triggered.connect(open_config_gui)
    tools_menu.addAction(config_action)
    logger.debug("Tools menu config action registered")
