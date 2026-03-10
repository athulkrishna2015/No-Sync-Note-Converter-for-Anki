from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, tooltip

from . import state
from .mapping import (
    get_default_target_model_name,
    normalize_field_map,
    prompt_preset_name,
    remember_conversion_pair,
    save_quick_convert_preset,
)


class ConversionDialog(QDialog):
    def __init__(
        self,
        parent,
        old_model,
        initial_source_model_name=None,
        initial_target_model_name=None,
        initial_mapping=None,
        *,
        allow_source_selection=False,
        show_save_preset_button=True,
        window_title="Convert Note Type",
        title_html=None,
    ):
        super().__init__(parent)
        self.allow_source_selection = allow_source_selection
        self.available_model_names = mw.col.models.all_names()
        if not self.available_model_names:
            raise ValueError("No note types are available.")

        self.initial_source_model_name = initial_source_model_name
        if old_model is not None:
            self.initial_source_model_name = old_model["name"]
        if self.initial_source_model_name not in self.available_model_names:
            self.initial_source_model_name = self.available_model_names[0]

        self.old_model = None
        self.old_fields = []
        self.active_source_name = None
        self.active_target_name = None
        self.mapping_rows = {}
        self.temp_mappings = {}
        self.initial_target_model_name = initial_target_model_name
        self.has_initial_mapping = initial_mapping is not None
        self.initial_mapping = normalize_field_map(initial_mapping or {})
        self.initial_mapping_pair = (
            self.initial_source_model_name,
            self.initial_target_model_name,
        )
        self.show_save_preset_button = show_save_preset_button
        self.title_html_template = title_html or "Convert <b>{source}</b> notes"

        self.setWindowTitle(window_title)
        self.setMinimumWidth(560)
        self.setup_ui()

        self.set_source_model(self.initial_source_model_name)
        if self.allow_source_selection:
            self.source_combo.blockSignals(True)
            self.source_combo.setCurrentIndex(
                self.source_combo.findData(self.initial_source_model_name)
            )
            self.source_combo.blockSignals(False)

        models = self.available_model_names
        default_target_name = initial_target_model_name or get_default_target_model_name(
            models, [self.old_model["name"]]
        )
        self.target_combo.blockSignals(True)
        if default_target_name in models:
            self.target_combo.setCurrentIndex(models.index(default_target_name))
        self.target_combo.blockSignals(False)
        self.active_source_name = self.old_model["name"]
        self.active_target_name = self.target_combo.currentData()
        self.build_mapping_rows(self.get_saved_mapping(self.active_target_name))

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.title_label = QLabel()
        layout.addWidget(self.title_label)

        if self.allow_source_selection:
            source_row = QHBoxLayout()
            source_row.addWidget(QLabel("Source note type"))

            self.source_combo = QComboBox()
            for model_name in self.available_model_names:
                self.source_combo.addItem(model_name, model_name)
            self.source_combo.currentTextChanged.connect(self.on_source_changed)
            source_row.addWidget(self.source_combo, 1)
            layout.addLayout(source_row)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Target note type"))

        self.target_combo = QComboBox()
        for model_name in self.available_model_names:
            self.target_combo.addItem(model_name, model_name)
        self.target_combo.currentTextChanged.connect(self.on_target_changed)
        target_row.addWidget(self.target_combo, 1)
        layout.addLayout(target_row)

        self.mapping_label = QLabel()
        layout.addWidget(self.mapping_label)

        hint = QLabel(
            "Use dropdowns to choose source fields for each target field. "
            "If you add multiple source fields, their contents are merged top-to-bottom."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.scroll_layout = QGridLayout(scroll_content)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        if self.show_save_preset_button:
            save_preset_button = buttons.addButton(
                "Save Quick Preset",
                QDialogButtonBox.ButtonRole.ActionRole,
            )
            save_preset_button.clicked.connect(self.save_quick_preset)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_pair_key(self, source_model_name=None, target_model_name=None):
        source_name = source_model_name or (
            self.old_model["name"] if self.old_model is not None else None
        )
        target_name = target_model_name
        if target_name is None and hasattr(self, "target_combo"):
            target_name = self.target_combo.currentData()

        if not source_name or not target_name:
            return None
        return (source_name, target_name)

    def remember_current_mapping(self):
        pair_key = self.get_pair_key(self.active_source_name, self.active_target_name)
        if pair_key is None or not self.mapping_rows:
            return
        self.temp_mappings[pair_key] = self.get_mapping()

    def render_title_html(self):
        try:
            return self.title_html_template.format(source=self.old_model["name"])
        except (IndexError, KeyError, ValueError):
            return self.title_html_template

    def set_source_model(self, source_model_name):
        source_model = mw.col.models.by_name(source_model_name)
        if not source_model:
            raise ValueError(f"Source note type not found: {source_model_name}")

        self.old_model = source_model
        self.old_fields = [field["name"] for field in self.old_model["flds"]]
        self.title_label.setText(self.render_title_html())

    def get_saved_mapping(self, target_model_name):
        pair_key = self.get_pair_key(target_model_name=target_model_name)
        if pair_key is None:
            return {}

        if pair_key in self.temp_mappings:
            return self.temp_mappings[pair_key]

        if self.has_initial_mapping and pair_key == self.initial_mapping_pair:
            return self.initial_mapping

        source_model_name, target_model_name = pair_key
        map_key = f"{source_model_name}->{target_model_name}"
        try:
            return normalize_field_map(
                state.config["mappings"].get(map_key, {}).get("field_map", {})
            )
        except ValueError:
            return {}

    def get_default_sources(self, target_field, saved_mapping):
        if target_field in saved_mapping:
            return [src for src in saved_mapping[target_field] if src in self.old_fields]

        if target_field in self.old_fields:
            return [target_field]

        if target_field == "Front" and "Text" in self.old_fields:
            return ["Text"]

        if target_field == "Back":
            if "Extra" in self.old_fields:
                return ["Extra"]
            if "Back Extra" in self.old_fields:
                return ["Back Extra"]

        return []

    def build_mapping_rows(self, saved_mapping):
        self.clear_mapping_rows()

        target_model = self.get_target_model()
        if not target_model:
            return

        self.mapping_label.setText(
            f"Mapping from <b>{self.old_model['name']}</b> to <b>{target_model['name']}</b>"
        )

        target_fields = [f["name"] for f in target_model["flds"]]
        for row, target_field in enumerate(target_fields):
            self.scroll_layout.addWidget(QLabel(target_field), row, 0)

            field_widget = QWidget()
            field_layout = QVBoxLayout(field_widget)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(4)

            self.mapping_rows[target_field] = {
                "layout": field_layout,
                "rows": [],
            }

            default_sources = self.get_default_sources(target_field, saved_mapping)
            if not default_sources:
                default_sources = [None]

            for source_name in default_sources:
                self.add_source_selector(target_field, source_name)

            add_button = QPushButton("Add source field")
            add_button.clicked.connect(
                lambda _, tf=target_field: self.add_source_selector(tf, None)
            )
            field_layout.addWidget(add_button, alignment=Qt.AlignmentFlag.AlignLeft)
            self.mapping_rows[target_field]["add_button"] = add_button

            self.scroll_layout.addWidget(field_widget, row, 1)
            self.update_remove_buttons(target_field)

        self.scroll_layout.setColumnStretch(1, 1)

    def clear_mapping_rows(self):
        self.mapping_rows = {}
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def add_source_selector(self, target_field, selected_source):
        row_state = self.mapping_rows[target_field]
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)

        combo = QComboBox()
        combo.addItem("(None)", None)
        for source_name in self.old_fields:
            combo.addItem(source_name, source_name)

        if selected_source:
            idx = combo.findData(selected_source)
            if idx != -1:
                combo.setCurrentIndex(idx)

        remove_button = QToolButton()
        remove_button.setText("Remove")
        remove_button.clicked.connect(
            lambda _, tf=target_field, widget=row_widget: self.remove_source_selector(
                tf, widget
            )
        )

        row_layout.addWidget(combo, 1)
        row_layout.addWidget(remove_button)

        insert_index = row_state["layout"].count()
        if "add_button" in row_state:
            insert_index -= 1
        row_state["layout"].insertWidget(insert_index, row_widget)
        row_state["rows"].append(
            {
                "widget": row_widget,
                "combo": combo,
                "remove_button": remove_button,
            }
        )
        self.update_remove_buttons(target_field)

    def remove_source_selector(self, target_field, row_widget):
        row_state = self.mapping_rows[target_field]
        if len(row_state["rows"]) <= 1:
            row_state["rows"][0]["combo"].setCurrentIndex(0)
            return

        for i, row in enumerate(row_state["rows"]):
            if row["widget"] is row_widget:
                removed = row_state["rows"].pop(i)
                removed["widget"].deleteLater()
                break

        self.update_remove_buttons(target_field)

    def update_remove_buttons(self, target_field):
        row_state = self.mapping_rows[target_field]
        can_remove = len(row_state["rows"]) > 1
        for row in row_state["rows"]:
            row["remove_button"].setEnabled(can_remove)

    def on_source_changed(self, source_model_name):
        self.remember_current_mapping()
        try:
            self.set_source_model(source_model_name)
        except ValueError as exc:
            showInfo(str(exc))
            return

        self.active_source_name = self.old_model["name"]
        self.active_target_name = self.target_combo.currentData()
        self.build_mapping_rows(self.get_saved_mapping(self.active_target_name))

    def on_target_changed(self, target_model_name):
        self.remember_current_mapping()
        self.active_source_name = self.old_model["name"] if self.old_model else None
        self.active_target_name = target_model_name
        self.build_mapping_rows(self.get_saved_mapping(target_model_name))

    def get_source_model(self):
        return self.old_model

    def get_target_model(self):
        target_model_name = self.target_combo.currentData()
        return mw.col.models.by_name(target_model_name) if target_model_name else None

    def get_mapping(self):
        mapping = {}
        for target_field, row_state in self.mapping_rows.items():
            sources = []
            for row in row_state["rows"]:
                source_name = row["combo"].currentData()
                if source_name:
                    sources.append(source_name)
            mapping[target_field] = sources
        return mapping

    def save_quick_preset(self):
        source_model = self.get_source_model()
        target_model = self.get_target_model()
        if not source_model or not target_model:
            showInfo("Please choose a target note type before saving a preset.")
            return

        preset_name = prompt_preset_name(
            self,
            f"{source_model['name']} -> {target_model['name']}",
        )
        if not preset_name:
            return

        mapping = self.get_mapping()
        remember_conversion_pair(source_model["name"], target_model["name"], mapping)
        result = save_quick_convert_preset(
            preset_name,
            source_model["name"],
            target_model["name"],
            mapping,
        )
        if result == "created":
            tooltip(f"Saved quick preset: {preset_name}")
        elif result == "updated":
            tooltip(f"Updated quick preset: {preset_name}")


def show_conversion_dialog(parent, old_model):
    dialog = ConversionDialog(
        parent,
        old_model,
        initial_target_model_name=get_default_target_model_name(
            mw.col.models.all_names(), [old_model["name"]]
        ),
    )
    if not dialog.exec():
        return None, None

    return dialog.get_target_model(), dialog.get_mapping()
