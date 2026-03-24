import copy

from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, tooltip

from . import state
from .conversion_dialog import ConversionDialog
from .mapping import format_quick_preset_label, prompt_preset_name


class AddonConfigDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.working_toggle_strip_cloze = bool(
            state.config.get("toggle_strip_cloze", True)
        )
        self.working_presets = copy.deepcopy(
            state.config.get("quick_convert_presets", [])
        )
        self.working_mappings = copy.deepcopy(state.config.get("mappings", {}))

        self.setWindowTitle(f"{state.ADDON_NAME} Config")
        self.setMinimumWidth(780)
        self.setMinimumHeight(560)
        self.setup_ui()
        self.refresh_preset_list()
        self.refresh_mapping_list()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        self.open_after_checkbox = QCheckBox("Open notes in browser/editor after conversion")
        self.open_after_checkbox.setChecked(state.config.get("open_notes_after", True))
        general_layout.addWidget(self.open_after_checkbox)

        self.delete_original_checkbox = QCheckBox("Delete original notes after conversion")
        self.delete_original_checkbox.setChecked(state.config.get("delete_original", True))
        general_layout.addWidget(self.delete_original_checkbox)

        self.strip_cloze_checkbox = QCheckBox(
            "Strip cloze markup when converting from a Cloze note type to a non-Cloze note type"
        )
        self.strip_cloze_checkbox.setChecked(self.working_toggle_strip_cloze)
        general_layout.addWidget(self.strip_cloze_checkbox)

        general_layout.addSpacing(10)
        deck_row = QHBoxLayout()
        deck_row.addWidget(QLabel("Default target deck:"))
        self.deck_combo = QComboBox()
        self.deck_combo.addItem("Same as original", None)
        for deck in sorted(mw.col.decks.all_names_and_ids(), key=lambda x: x.name):
            self.deck_combo.addItem(deck.name, deck.id)
        
        target_deck_id = state.config.get("target_deck_id")
        if target_deck_id:
            idx = self.deck_combo.findData(target_deck_id)
            if idx != -1:
                self.deck_combo.setCurrentIndex(idx)
        deck_row.addWidget(self.deck_combo, 1)
        general_layout.addLayout(deck_row)

        general_hint = QLabel(
            "Use the tabs below to manage quick presets and saved field mappings with the same GUI used during conversion."
        )
        general_hint.setWordWrap(True)
        general_layout.addWidget(general_hint)
        general_layout.addStretch()
        tabs.addTab(general_tab, "General")

        presets_tab = QWidget()
        presets_layout = QVBoxLayout(presets_tab)
        presets_layout.addWidget(QLabel("Quick convert presets"))
        self.preset_list = QListWidget()
        presets_layout.addWidget(self.preset_list, 1)

        preset_buttons = QHBoxLayout()
        add_preset = QPushButton("Add")
        add_preset.clicked.connect(self.add_preset)
        preset_buttons.addWidget(add_preset)
        edit_preset = QPushButton("Edit")
        edit_preset.clicked.connect(self.edit_preset)
        preset_buttons.addWidget(edit_preset)
        delete_preset = QPushButton("Delete")
        delete_preset.clicked.connect(self.delete_preset)
        preset_buttons.addWidget(delete_preset)
        preset_buttons.addStretch()
        presets_layout.addLayout(preset_buttons)
        tabs.addTab(presets_tab, "Quick Presets")

        mappings_tab = QWidget()
        mappings_layout = QVBoxLayout(mappings_tab)
        mappings_layout.addWidget(QLabel("Saved field mappings"))
        self.mapping_list = QListWidget()
        mappings_layout.addWidget(self.mapping_list, 1)

        mapping_buttons = QHBoxLayout()
        add_mapping = QPushButton("Add")
        add_mapping.clicked.connect(self.add_mapping)
        mapping_buttons.addWidget(add_mapping)
        edit_mapping = QPushButton("Edit")
        edit_mapping.clicked.connect(self.edit_mapping)
        mapping_buttons.addWidget(edit_mapping)
        delete_mapping = QPushButton("Delete")
        delete_mapping.clicked.connect(self.delete_mapping)
        mapping_buttons.addWidget(delete_mapping)
        mapping_buttons.addStretch()
        mappings_layout.addLayout(mapping_buttons)
        tabs.addTab(mappings_tab, "Mappings")

        support_tab = QWidget()
        support_layout = QVBoxLayout(support_tab)

        support_hint = QLabel(
            "Support the addon with the payment methods below."
        )
        support_hint.setWordWrap(True)
        support_layout.addWidget(support_hint)

        support_scroll = QScrollArea()
        support_scroll.setWidgetResizable(True)
        support_content = QWidget()
        support_content_layout = QVBoxLayout(support_content)
        support_content_layout.setSpacing(16)

        for item in state.SUPPORT_ITEMS:
            support_content_layout.addWidget(self.create_support_item(item))

        support_content_layout.addStretch()
        support_scroll.setWidget(support_content)
        support_layout.addWidget(support_scroll, 1)
        tabs.addTab(support_tab, "Support")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def create_support_item(self, item):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(frame)
        layout.setSpacing(10)

        title = QLabel(item["label"])
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 1)
        title.setFont(title_font)
        layout.addWidget(title)

        value_row = QHBoxLayout()
        value_field = QLineEdit(item["value"])
        value_field.setReadOnly(True)
        value_field.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        value_field.setCursorPosition(0)
        value_row.addWidget(value_field, 1)

        copy_button = QPushButton(f"Copy {item['label']}")
        copy_button.clicked.connect(
            lambda _, label=item["label"], value=item["value"]: self.copy_support_value(
                label, value
            )
        )
        value_row.addWidget(copy_button)
        layout.addLayout(value_row)

        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(state.SUPPORT_DIR / item["image"]))
        if pixmap.isNull():
            qr_label.setText("QR code image not found.")
        else:
            scaled = pixmap.scaledToWidth(
                min(state.SUPPORT_QR_WIDTH, pixmap.width()),
                Qt.TransformationMode.SmoothTransformation,
            )
            qr_label.setPixmap(scaled)
            qr_label.setMinimumSize(scaled.size())

        qr_row = QHBoxLayout()
        qr_row.addStretch()
        qr_row.addWidget(qr_label)
        qr_row.addStretch()
        layout.addLayout(qr_row)

        return frame

    def copy_support_value(self, label, value):
        QApplication.clipboard().setText(value)
        tooltip(f"{label} ID copied.", parent=self)

    def refresh_preset_list(self):
        self.preset_list.clear()
        sorted_presets = sorted(
            enumerate(self.working_presets),
            key=lambda item: (
                item[1]["source_type"].lower(),
                item[1]["name"].lower(),
                item[1]["target_type"].lower(),
            ),
        )
        for index, preset in sorted_presets:
            item = QListWidgetItem(format_quick_preset_label(preset))
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.preset_list.addItem(item)

    def refresh_mapping_list(self):
        self.mapping_list.clear()
        for map_key, mapping_entry in sorted(self.working_mappings.items()):
            label = f"{mapping_entry['source_type']} -> {mapping_entry['target_type']}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, map_key)
            self.mapping_list.addItem(item)

    def selected_preset_index(self):
        item = self.preset_list.currentItem()
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def selected_mapping_key(self):
        item = self.mapping_list.currentItem()
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

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
            showInfo(str(exc))
            return None, None, None
        if not dialog.exec():
            return None, None, None

        source_model = dialog.get_source_model()
        if not source_model:
            return None, None, None
        return source_model["name"], dialog.get_target_model(), dialog.get_mapping()

    def upsert_preset(self, preset_entry, replace_index=None):
        identity = (
            preset_entry["name"],
            preset_entry["source_type"],
            preset_entry["target_type"],
        )
        updated_presets = []
        replaced = False

        for index, existing in enumerate(self.working_presets):
            existing_identity = (
                existing["name"],
                existing["source_type"],
                existing["target_type"],
            )
            if replace_index is not None and index == replace_index:
                if not replaced:
                    updated_presets.append(preset_entry)
                    replaced = True
                continue
            if existing_identity == identity:
                if not replaced:
                    updated_presets.append(preset_entry)
                    replaced = True
                continue
            updated_presets.append(existing)

        if not replaced:
            updated_presets.append(preset_entry)

        self.working_presets = updated_presets

    def add_preset(self):
        source_name, target_model, mapping = self.edit_mapping_dialog(
            None,
            window_title="Create Quick Preset",
            title_html="Create quick preset for <b>{source}</b>",
        )
        if not target_model:
            return

        preset_name = prompt_preset_name(
            self,
            f"{source_name} -> {target_model['name']}",
        )
        if not preset_name:
            return

        self.upsert_preset(
            {
                "name": preset_name,
                "source_type": source_name,
                "target_type": target_model["name"],
                "field_map": mapping,
            }
        )
        self.refresh_preset_list()

    def edit_preset(self):
        preset_index = self.selected_preset_index()
        if preset_index is None:
            tooltip("Select a preset to edit.", parent=self)
            return

        preset = self.working_presets[preset_index]
        source_name, target_model, mapping = self.edit_mapping_dialog(
            preset["source_type"],
            initial_target_model_name=preset["target_type"],
            initial_mapping=preset["field_map"],
            window_title="Edit Quick Preset",
            title_html="Edit quick preset for <b>{source}</b>",
        )
        if not target_model:
            return

        preset_name = prompt_preset_name(self, preset["name"])
        if not preset_name:
            return

        self.upsert_preset(
            {
                "name": preset_name,
                "source_type": source_name,
                "target_type": target_model["name"],
                "field_map": mapping,
            },
            replace_index=preset_index,
        )
        self.refresh_preset_list()

    def delete_preset(self):
        preset_index = self.selected_preset_index()
        if preset_index is None:
            tooltip("Select a preset to delete.", parent=self)
            return

        preset = self.working_presets[preset_index]
        result = QMessageBox.question(
            self,
            "Delete Quick Preset",
            f"Delete preset '{preset['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        del self.working_presets[preset_index]
        self.refresh_preset_list()

    def add_mapping(self):
        source_name, target_model, mapping = self.edit_mapping_dialog(
            None,
            window_title="Create Saved Mapping",
            title_html="Create saved mapping for <b>{source}</b>",
        )
        if not target_model:
            return

        map_key = f"{source_name}->{target_model['name']}"
        self.working_mappings[map_key] = {
            "source_type": source_name,
            "target_type": target_model["name"],
            "field_map": mapping,
        }
        self.refresh_mapping_list()

    def edit_mapping(self):
        map_key = self.selected_mapping_key()
        if not map_key:
            tooltip("Select a mapping to edit.", parent=self)
            return

        mapping_entry = self.working_mappings[map_key]
        source_name, target_model, mapping = self.edit_mapping_dialog(
            mapping_entry["source_type"],
            initial_target_model_name=mapping_entry["target_type"],
            initial_mapping=mapping_entry["field_map"],
            window_title="Edit Saved Mapping",
            title_html="Edit saved mapping for <b>{source}</b>",
        )
        if not target_model:
            return

        new_map_key = f"{source_name}->{target_model['name']}"
        if new_map_key != map_key:
            del self.working_mappings[map_key]
        self.working_mappings[new_map_key] = {
            "source_type": source_name,
            "target_type": target_model["name"],
            "field_map": mapping,
        }
        self.refresh_mapping_list()

    def delete_mapping(self):
        map_key = self.selected_mapping_key()
        if not map_key:
            tooltip("Select a mapping to delete.", parent=self)
            return

        mapping_entry = self.working_mappings[map_key]
        result = QMessageBox.question(
            self,
            "Delete Saved Mapping",
            f"Delete mapping '{mapping_entry['source_type']} -> {mapping_entry['target_type']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        del self.working_mappings[map_key]
        self.refresh_mapping_list()

    def accept(self):
        state.config["open_notes_after"] = self.open_after_checkbox.isChecked()
        state.config["delete_original"] = self.delete_original_checkbox.isChecked()
        state.config["toggle_strip_cloze"] = self.strip_cloze_checkbox.isChecked()
        state.config["target_deck_id"] = self.deck_combo.currentData()
        state.config["quick_convert_presets"] = copy.deepcopy(self.working_presets)
        state.config["mappings"] = copy.deepcopy(self.working_mappings)
        state.save_config()
        super().accept()


def open_config_gui(*_args, **_kwargs):
    dialog = AddonConfigDialog(mw)
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
