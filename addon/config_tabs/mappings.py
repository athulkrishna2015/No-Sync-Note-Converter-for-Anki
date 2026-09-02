from aqt.qt import *
from aqt.utils import tooltip

from .. import logger


class MappingsTab(QWidget):
    def __init__(self, parent_dialog):
        super().__init__(parent_dialog)
        self._dialog = parent_dialog
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Saved field mappings"))
        self.mapping_list = QListWidget()
        layout.addWidget(self.mapping_list, 1)

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
        layout.addLayout(mapping_buttons)

    def refresh(self):
        self.mapping_list.clear()
        for map_key, mapping_entry in sorted(self._dialog.working_mappings.items()):
            label = f"{mapping_entry['source_type']} -> {mapping_entry['target_type']}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, map_key)
            self.mapping_list.addItem(item)

    def selected_mapping_key(self):
        item = self.mapping_list.currentItem()
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def add_mapping(self):
        source_name, target_model, mapping = self._dialog.edit_mapping_dialog(
            None,
            window_title="Create Saved Mapping",
            title_html="Create saved mapping for <b>{source}</b>",
        )
        if not target_model:
            return

        map_key = f"{source_name}->{target_model['name']}"
        self._dialog.working_mappings[map_key] = {
            "source_type": source_name,
            "target_type": target_model["name"],
            "field_map": mapping,
        }
        logger.info("Mapping added: %s", map_key)
        self.refresh()

    def edit_mapping(self):
        map_key = self.selected_mapping_key()
        if not map_key:
            tooltip("Select a mapping to edit.", parent=self)
            return

        mapping_entry = self._dialog.working_mappings[map_key]
        source_name, target_model, mapping = self._dialog.edit_mapping_dialog(
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
            del self._dialog.working_mappings[map_key]
        self._dialog.working_mappings[new_map_key] = {
            "source_type": source_name,
            "target_type": target_model["name"],
            "field_map": mapping,
        }
        logger.info("Mapping edited: %s -> %s", map_key, new_map_key)
        self.refresh()

    def delete_mapping(self):
        map_key = self.selected_mapping_key()
        if not map_key:
            tooltip("Select a mapping to delete.", parent=self)
            return

        mapping_entry = self._dialog.working_mappings[map_key]
        result = QMessageBox.question(
            self,
            "Delete Saved Mapping",
            f"Delete mapping '{mapping_entry['source_type']} -> {mapping_entry['target_type']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        logger.info("Mapping deleted: %s", map_key)
        del self._dialog.working_mappings[map_key]
        self.refresh()
