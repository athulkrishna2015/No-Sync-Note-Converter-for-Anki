from aqt.qt import *
from aqt.utils import tooltip

from .. import logger
from ..mapping import format_quick_preset_label, prompt_preset_name


class PresetsTab(QWidget):
    def __init__(self, parent_dialog):
        super().__init__(parent_dialog)
        self._dialog = parent_dialog
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Quick convert presets"))
        self.preset_list = QListWidget()
        layout.addWidget(self.preset_list, 1)

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
        layout.addLayout(preset_buttons)

    def refresh(self):
        self.preset_list.clear()
        sorted_presets = sorted(
            enumerate(self._dialog.working_presets),
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

    def selected_preset_index(self):
        item = self.preset_list.currentItem()
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def upsert_preset(self, preset_entry, replace_index=None):
        identity = (
            preset_entry["name"],
            preset_entry["source_type"],
            preset_entry["target_type"],
        )
        updated_presets = []
        replaced = False

        for index, existing in enumerate(self._dialog.working_presets):
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

        self._dialog.working_presets = updated_presets

    def add_preset(self):
        source_name, target_model, mapping = self._dialog.edit_mapping_dialog(
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
        logger.info("Preset added: %s (%s -> %s)", preset_name, source_name, target_model["name"])
        self.refresh()

    def edit_preset(self):
        preset_index = self.selected_preset_index()
        if preset_index is None:
            tooltip("Select a preset to edit.", parent=self)
            return

        preset = self._dialog.working_presets[preset_index]
        source_name, target_model, mapping = self._dialog.edit_mapping_dialog(
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
        logger.info(
            "Preset edited: %s (%s -> %s) index=%s",
            preset_name,
            source_name,
            target_model["name"],
            preset_index,
        )
        self.refresh()

    def delete_preset(self):
        preset_index = self.selected_preset_index()
        if preset_index is None:
            tooltip("Select a preset to delete.", parent=self)
            return

        preset = self._dialog.working_presets[preset_index]
        result = QMessageBox.question(
            self,
            "Delete Quick Preset",
            f"Delete preset '{preset['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        logger.info("Preset deleted: %s index=%s", preset["name"], preset_index)
        del self._dialog.working_presets[preset_index]
        self.refresh()
