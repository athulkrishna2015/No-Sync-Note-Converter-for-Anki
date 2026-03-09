import copy
import re
from aqt import mw, dialogs
from aqt.qt import *
from aqt.utils import showInfo, tooltip
from anki.consts import MODEL_CLOZE
from anki.hooks import addHook
from aqt.gui_hooks import reviewer_will_show_context_menu

# Load Config
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

    if changed:
        save_config()


ensure_config_defaults()

def strip_cloze_tags(text):
    """
    Converts '{{c1::Answer::Hint}}' to 'Answer'.
    """
    start_pattern = re.compile(r"\{\{c\d+::")
    result = []
    cursor = 0

    while True:
        match = start_pattern.search(text, cursor)
        if not match:
            result.append(text[cursor:])
            break

        result.append(text[cursor:match.start()])
        i = match.end()
        depth = 0
        in_hint = False
        answer_chars = []
        closed = False

        while i < len(text):
            if text.startswith("::", i) and depth == 0 and not in_hint:
                in_hint = True
                i += 2
                continue

            if text.startswith("}}", i) and depth == 0:
                i += 2
                closed = True
                break

            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}" and depth > 0:
                depth -= 1

            if not in_hint:
                answer_chars.append(ch)
            i += 1

        if not closed:
            # Malformed cloze; preserve original trailing text as-is.
            result.append(text[match.start():])
            break

        result.append("".join(answer_chars))
        cursor = i

    return "".join(result)


def normalize_field_map(field_map):
    if not isinstance(field_map, dict):
        raise ValueError("Field mapping must be a dictionary.")

    normalized = {}
    for target_field, source_fields in field_map.items():
        if not isinstance(target_field, str):
            raise ValueError("Field mapping keys must be field names.")

        if source_fields is None:
            normalized[target_field] = []
        elif isinstance(source_fields, str):
            normalized[target_field] = [source_fields]
        elif isinstance(source_fields, (list, tuple)):
            cleaned_sources = []
            for source_field in source_fields:
                if not source_field:
                    continue
                if not isinstance(source_field, str):
                    raise ValueError(
                        f"Field mapping for '{target_field}' contains a non-text source field."
                    )
                cleaned_sources.append(source_field)
            normalized[target_field] = cleaned_sources
        else:
            raise ValueError(
                f"Field mapping for '{target_field}' must be a field name or list of field names."
            )

    return normalized


def validate_field_map(source_model, target_model, field_map, mapping_name):
    normalized = normalize_field_map(field_map)
    source_fields = {field["name"] for field in source_model["flds"]}
    target_fields = {field["name"] for field in target_model["flds"]}

    invalid_targets = sorted(
        target_field for target_field in normalized if target_field not in target_fields
    )
    invalid_sources = []
    for target_field, source_fields_list in normalized.items():
        for source_field in source_fields_list:
            if source_field not in source_fields:
                invalid_sources.append(f"{target_field} <- {source_field}")

    if invalid_targets or invalid_sources:
        problems = []
        if invalid_targets:
            problems.append(
                "unknown target fields: " + ", ".join(invalid_targets)
            )
        if invalid_sources:
            problems.append(
                "unknown source fields: " + ", ".join(sorted(invalid_sources))
            )
        raise ValueError(
            f"{mapping_name} is out of date for "
            f"{source_model['name']} -> {target_model['name']} ({'; '.join(problems)}). "
            "Please reopen the conversion dialog and update the mapping."
        )

    return normalized


def get_effective_field_map(source_model, target_model, override_mapping=None):
    if override_mapping is not None:
        return validate_field_map(
            source_model,
            target_model,
            override_mapping,
            "Selected field mapping",
        )

    map_key = f"{source_model['name']}->{target_model['name']}"
    mapping = config["mappings"].get(map_key)
    if not mapping:
        return None

    return validate_field_map(
        source_model,
        target_model,
        mapping.get("field_map", {}),
        f"Saved mapping '{map_key}'",
    )

def get_default_target_model_name(models, source_model_names=None):
    if not models:
        return None

    source_names = list(dict.fromkeys(name for name in (source_model_names or []) if name))
    source_set = set(source_names)
    preferred_targets = config["preferred_target_models"]

    remembered_targets = []
    for source_name in source_names:
        preferred_name = preferred_targets.get(source_name)
        if preferred_name in models and preferred_name not in source_set:
            remembered_targets.append(preferred_name)

    unique_targets = list(dict.fromkeys(remembered_targets))
    if len(unique_targets) == 1:
        return unique_targets[0]

    for model_name in models:
        if model_name not in source_set:
            return model_name

    return models[0]


def remember_conversion_pair(source_model_name, target_model_name, field_mapping):
    changed = False

    if source_model_name and target_model_name and source_model_name != target_model_name:
        preferred_targets = config["preferred_target_models"]
        if preferred_targets.get(source_model_name) != target_model_name:
            preferred_targets[source_model_name] = target_model_name
            changed = True

    map_key = f"{source_model_name}->{target_model_name}"
    mapping_entry = {
        "source_type": source_model_name,
        "target_type": target_model_name,
        "field_map": field_mapping,
    }
    if config["mappings"].get(map_key) != mapping_entry:
        config["mappings"][map_key] = mapping_entry
        changed = True

    if changed:
        save_config()


def get_quick_convert_presets(source_model_name=None):
    presets = []
    for preset in config["quick_convert_presets"]:
        target_model = mw.col.models.by_name(preset["target_type"])
        if not target_model:
            continue
        if source_model_name and preset["source_type"] != source_model_name:
            continue
        presets.append(preset)
    return sorted(presets, key=lambda preset: preset["name"].lower())


def get_quick_convert_preset(source_model_name, target_model_name, preset_name):
    for preset in config["quick_convert_presets"]:
        if (
            preset["name"] == preset_name
            and preset["source_type"] == source_model_name
            and preset["target_type"] == target_model_name
        ):
            return preset
    return None


def save_quick_convert_preset(name, source_model_name, target_model_name, field_mapping):
    preset_name = name.strip()
    if not preset_name:
        return None

    preset_entry = {
        "name": preset_name,
        "source_type": source_model_name,
        "target_type": target_model_name,
        "field_map": field_mapping,
    }

    for i, preset in enumerate(config["quick_convert_presets"]):
        if (
            preset["name"] == preset_name
            and preset["source_type"] == source_model_name
            and preset["target_type"] == target_model_name
        ):
            config["quick_convert_presets"][i] = preset_entry
            save_config()
            return "updated"

    config["quick_convert_presets"].append(preset_entry)
    save_config()
    return "created"


def format_quick_preset_label(preset):
    route = f"{preset['source_type']} -> {preset['target_type']}"
    preset_name = preset["name"].strip()
    normalized_name = " ".join(preset_name.lower().split())
    normalized_route = " ".join(route.lower().split())

    if normalized_route in normalized_name:
        return preset_name

    return f"{preset_name} ({route})"


def prompt_preset_name(parent, default_name):
    preset_name, ok = QInputDialog.getText(
        parent,
        "Preset Name",
        "Preset name:",
        QLineEdit.EchoMode.Normal,
        default_name,
    )
    if not ok:
        return None

    preset_name = preset_name.strip()
    if not preset_name:
        showInfo("Preset name cannot be empty.")
        return None

    return preset_name

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
                config["mappings"].get(map_key, {}).get("field_map", {})
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
            lambda _, tf=target_field, widget=row_widget: self.remove_source_selector(tf, widget)
        )

        row_layout.addWidget(combo, 1)
        row_layout.addWidget(remove_button)

        insert_index = row_state["layout"].count()
        if "add_button" in row_state:
            insert_index -= 1
        row_state["layout"].insertWidget(insert_index, row_widget)
        row_state["rows"].append({
            "widget": row_widget,
            "combo": combo,
            "remove_button": remove_button,
        })
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
        m = {}
        for target_field, row_state in self.mapping_rows.items():
            sources = []
            for row in row_state["rows"]:
                source_name = row["combo"].currentData()
                if source_name:
                    sources.append(source_name)
            m[target_field] = sources
        return m

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


class AddonConfigDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.working_toggle_strip_cloze = bool(config.get("toggle_strip_cloze", True))
        self.working_presets = copy.deepcopy(config.get("quick_convert_presets", []))
        self.working_mappings = copy.deepcopy(config.get("mappings", {}))

        self.setWindowTitle("No-Sync Note Converter Config")
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
        self.strip_cloze_checkbox = QCheckBox(
            "Strip cloze markup when converting from a Cloze note type to a non-Cloze note type"
        )
        self.strip_cloze_checkbox.setChecked(self.working_toggle_strip_cloze)
        general_layout.addWidget(self.strip_cloze_checkbox)

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

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
        config["toggle_strip_cloze"] = self.strip_cloze_checkbox.isChecked()
        config["quick_convert_presets"] = copy.deepcopy(self.working_presets)
        config["mappings"] = copy.deepcopy(self.working_mappings)
        save_config()
        super().accept()


def open_config_gui():
    dialog = AddonConfigDialog(mw)
    dialog.exec()
    return True


def group_note_ids_by_model(nids):
    notes_by_mid = {}
    for nid in nids:
        note = mw.col.get_note(nid)
        mid = note.mid
        if mid not in notes_by_mid:
            notes_by_mid[mid] = []
        notes_by_mid[mid].append(nid)
    return notes_by_mid


def finish_browser_conversion(browser, created_nids):
    if not created_nids:
        return

    mw.reset()

    query = f"nid:{','.join(map(str, created_nids))}"
    browser.search_for(query)

    try:
        browser.table.selectAll()
    except:
        pass

def core_convert_logic(nids, target_model, override_mapping=None):
    """
    Performs the actual Create New -> Delete Old logic.
    Returns a list of new Note IDs.
    """
    mw.progress.start()
    
    created_nids = []
    target_model_name = target_model["name"]
    target_is_cloze = target_model["type"] == MODEL_CLOZE

    try:
        def convert_notes():
            pending_nids = []
            mapping_cache = {}

            for nid in nids:
                old_note = mw.col.get_note(nid)
                old_model = old_note.note_type()
                if not old_model:
                    raise ValueError(f"Could not load the source note type for note {nid}.")

                old_model_id = old_model["id"]
                source_is_cloze = old_model["type"] == MODEL_CLOZE

                cache_key = (old_model_id, target_model["id"])
                if cache_key not in mapping_cache:
                    mapping_cache[cache_key] = get_effective_field_map(
                        old_model,
                        target_model,
                        override_mapping=override_mapping,
                    )
                field_map = mapping_cache[cache_key]

                new_note = mw.col.new_note(target_model)

                if field_map is not None:
                    for target_field, source_fields in field_map.items():
                        combined_content = []
                        for src in source_fields:
                            content = old_note[src]
                            if (
                                config["toggle_strip_cloze"]
                                and source_is_cloze
                                and not target_is_cloze
                            ):
                                content = strip_cloze_tags(content)
                            combined_content.append(content)

                        new_note[target_field] = "<br><br>".join(combined_content)
                else:
                    for field in old_note.keys():
                        if field in new_note:
                            content = old_note[field]
                            if (
                                config["toggle_strip_cloze"]
                                and source_is_cloze
                                and not target_is_cloze
                            ):
                                content = strip_cloze_tags(content)
                            new_note[field] = content

                old_cards = old_note.cards()
                deck_id = old_cards[0].did if old_cards else 1
                new_note.tags = old_note.tags

                mw.col.add_note(new_note, deck_id=deck_id)
                pending_nids.append(new_note.id)
                mw.col.remove_notes([nid])

            created_nids.extend(pending_nids)

        mw.col.db.transact(convert_notes)

    except Exception as e:
        showInfo(
            f"Error during conversion from note(s) to '{target_model_name}': {str(e)}\n\n"
            "No notes were converted."
        )
        return []
    finally:
        mw.progress.finish()
    
    return created_nids

# --- BROWSER HANDLER ---
def on_browser_convert(browser):
    nids = browser.selectedNotes()
    if not nids:
        tooltip("No notes selected.")
        return

    # Group nids by their model
    notes_by_mid = group_note_ids_by_model(nids)

    all_created_nids = []
    for mid, m_nids in notes_by_mid.items():
        old_model = mw.col.models.get(mid)
        if not old_model:
            continue

        target_model, mapping = show_conversion_dialog(browser, old_model)
        if not target_model:
            continue

        remember_conversion_pair(old_model["name"], target_model["name"], mapping)
        created_nids = core_convert_logic(m_nids, target_model, override_mapping=mapping)
        all_created_nids.extend(created_nids)
    
    if all_created_nids:
        finish_browser_conversion(browser, all_created_nids)
        tooltip(f"Converted {len(all_created_nids)} notes.")


def populate_browser_quick_convert_menu(browser, menu):
    menu.clear()

    nids = browser.selectedNotes()
    if not nids:
        action = menu.addAction("No notes selected")
        action.setEnabled(False)
        return

    notes_by_mid = group_note_ids_by_model(nids)
    presets_by_source = {}
    for mid in notes_by_mid:
        old_model = mw.col.models.get(mid)
        if not old_model:
            continue

        presets = get_quick_convert_presets(old_model["name"])
        if presets:
            presets_by_source[old_model["name"]] = presets

    if not presets_by_source:
        action = menu.addAction("No matching presets")
        action.setEnabled(False)
        return

    multiple_sources = len(presets_by_source) > 1
    for source_name in sorted(presets_by_source):
        target_menu = menu.addMenu(source_name) if multiple_sources else menu
        for preset in presets_by_source[source_name]:
            action = target_menu.addAction(format_quick_preset_label(preset))
            action.triggered.connect(
                lambda _, preset_source=preset["source_type"], preset_target=preset["target_type"], preset_name=preset["name"]:
                    on_browser_quick_convert(browser, preset_source, preset_target, preset_name)
            )


def on_browser_quick_convert(browser, source_model_name, target_model_name, preset_name):
    preset = get_quick_convert_preset(source_model_name, target_model_name, preset_name)
    if not preset:
        tooltip("Quick convert preset not found.")
        return

    nids = browser.selectedNotes()
    if not nids:
        tooltip("No notes selected.")
        return

    target_model = mw.col.models.by_name(preset["target_type"])
    if not target_model:
        showInfo(f"Preset target note type not found: {preset['target_type']}")
        return

    notes_by_mid = group_note_ids_by_model(nids)
    matching_nids = []
    skipped_count = 0
    for mid, grouped_nids in notes_by_mid.items():
        old_model = mw.col.models.get(mid)
        if old_model and old_model["name"] == source_model_name:
            matching_nids.extend(grouped_nids)
        else:
            skipped_count += len(grouped_nids)

    if not matching_nids:
        tooltip(f"Preset '{preset_name}' only works for {source_model_name} notes.")
        return

    remember_conversion_pair(
        source_model_name,
        target_model_name,
        preset["field_map"],
    )
    created_nids = core_convert_logic(
        matching_nids,
        target_model,
        override_mapping=preset["field_map"],
    )
    if created_nids:
        finish_browser_conversion(browser, created_nids)
        message = (
            f"Converted {len(created_nids)} notes with preset "
            f"'{preset_name}' ({source_model_name} -> {target_model_name})."
        )
        if skipped_count:
            message += f" Skipped {skipped_count} notes."
        tooltip(message)

def setup_browser_menu(browser):
    a = QAction("No-Sync Convert Note Type", browser)
    a.triggered.connect(lambda: on_browser_convert(browser))
    browser.form.menu_Notes.addSeparator()
    browser.form.menu_Notes.addAction(a)

    quick_menu = QMenu("No-Sync Quick Convert", browser.form.menu_Notes)
    quick_menu.aboutToShow.connect(lambda: populate_browser_quick_convert_menu(browser, quick_menu))
    browser.form.menu_Notes.addMenu(quick_menu)

# --- REVIEWER HANDLER ---
def on_reviewer_convert(reviewer):
    card = reviewer.card
    if not card:
        return

    old_note = card.note()
    old_model = old_note.note_type()

    # 1. Ask for Model and Mapping
    target_model, mapping = show_conversion_dialog(mw, old_model)
    if not target_model:
        return

    remember_conversion_pair(old_model["name"], target_model["name"], mapping)

    # 2. Convert
    created_nids = core_convert_logic([card.nid], target_model, override_mapping=mapping)

    # 3. Handle Reviewer Flow
    if created_nids:
        # Move reviewer to next card FIRST (since old one is gone)
        reviewer.nextCard()
        mw.reset()
        
        # Open Browser to the NEW card so user can add Clozes
        query = f"nid:{created_nids[0]}"
        dialogs.open("Browser", mw, search=[query])


def on_reviewer_quick_convert(reviewer, source_model_name, target_model_name, preset_name):
    preset = get_quick_convert_preset(source_model_name, target_model_name, preset_name)
    if not preset:
        tooltip("Quick convert preset not found.")
        return

    card = reviewer.card
    if not card:
        return

    old_note = card.note()
    old_model = old_note.note_type()
    if old_model["name"] != source_model_name:
        tooltip(f"Preset '{preset_name}' only works for {source_model_name} notes.")
        return

    target_model = mw.col.models.by_name(target_model_name)
    if not target_model:
        showInfo(f"Preset target note type not found: {target_model_name}")
        return

    remember_conversion_pair(
        source_model_name,
        target_model_name,
        preset["field_map"],
    )
    created_nids = core_convert_logic(
        [card.nid],
        target_model,
        override_mapping=preset["field_map"],
    )
    if created_nids:
        reviewer.nextCard()
        mw.reset()

        query = f"nid:{created_nids[0]}"
        dialogs.open("Browser", mw, search=[query])
        tooltip(f"Converted with preset '{preset_name}' ({source_model_name} -> {target_model_name}).")

def setup_reviewer_menu(reviewer, menu):
    a = menu.addAction("No-Sync Convert Note Type")
    a.triggered.connect(lambda: on_reviewer_convert(reviewer))

    quick_menu = menu.addMenu("No-Sync Quick Convert")
    card = reviewer.card
    if not card:
        action = quick_menu.addAction("No current card")
        action.setEnabled(False)
        return

    old_model = card.note().note_type()
    presets = get_quick_convert_presets(old_model["name"])
    if not presets:
        action = quick_menu.addAction("No presets for this note type")
        action.setEnabled(False)
        return

    for preset in presets:
        action = quick_menu.addAction(format_quick_preset_label(preset))
        action.triggered.connect(
            lambda _, preset_source=preset["source_type"], preset_target=preset["target_type"], preset_name=preset["name"]:
                on_reviewer_quick_convert(reviewer, preset_source, preset_target, preset_name)
        )

# --- HOOKS ---
addHook("browser.setupMenus", setup_browser_menu)
reviewer_will_show_context_menu.append(setup_reviewer_menu)
mw.addonManager.setConfigAction(__name__, open_config_gui)
mw.addonManager.setConfigUpdatedAction(__name__, reload_config)
