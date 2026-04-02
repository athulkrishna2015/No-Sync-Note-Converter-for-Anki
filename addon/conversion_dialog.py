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
        available_source_model_names=None,
        sample_note_ids_by_model=None,
        initial_review_history_card_ord_by_model=None,
        show_save_preset_button=True,
        window_title="Convert Note Type",
        title_html=None,
    ):
        super().__init__(parent)
        self.allow_source_selection = allow_source_selection
        self.available_model_names = mw.col.models.all_names()
        if not self.available_model_names:
            raise ValueError("No note types are available.")

        requested_source_model_names = (
            available_source_model_names or self.available_model_names
        )
        self.available_source_model_names = [
            model_name
            for model_name in requested_source_model_names
            if model_name in self.available_model_names
        ]
        if not self.available_source_model_names:
            self.available_source_model_names = list(self.available_model_names)

        self.initial_source_model_name = initial_source_model_name
        if old_model is not None:
            self.initial_source_model_name = old_model["name"]
        if self.initial_source_model_name not in self.available_source_model_names:
            self.initial_source_model_name = self.available_source_model_names[0]

        self.old_model = None
        self.old_fields = []
        self.active_source_name = None
        self.active_target_name = None
        self.mapping_rows = {}
        self.temp_mappings = {}
        self.target_model_names_by_source = {}
        self.sample_note_ids_by_model = dict(sample_note_ids_by_model or {})
        self.review_history_card_ords = self.load_review_history_card_ords()
        self.initial_review_history_card_ords = self.normalize_review_history_card_ords(
            initial_review_history_card_ord_by_model
        )
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

        if self.initial_target_model_name:
            self.target_model_names_by_source[self.initial_source_model_name] = (
                self.initial_target_model_name
            )

        # Initialize deck combo with current decks
        self.deck_combo.addItem("Same as original", None)
        for deck in sorted(mw.col.decks.all_names_and_ids(), key=lambda x: x.name):
            self.deck_combo.addItem(deck.name, deck.id)

        # Load saved settings
        self.open_after_cb.setChecked(state.config.get("open_notes_after", True))
        self.delete_original_cb.setChecked(state.config.get("delete_original", True))
        self.preserve_review_history_cb.setChecked(
            state.config.get("preserve_review_history", True)
        )
        self.strip_cloze_cb.setChecked(state.config.get("toggle_strip_cloze", True))

        target_deck_id = state.config.get("target_deck_id")
        if target_deck_id:
            idx = self.deck_combo.findData(target_deck_id)
            if idx != -1:
                self.deck_combo.setCurrentIndex(idx)

        self.set_source_model(self.initial_source_model_name)
        if self.allow_source_selection:
            self.source_combo.blockSignals(True)
            self.source_combo.setCurrentIndex(
                self.source_combo.findData(self.initial_source_model_name)
            )
            self.source_combo.blockSignals(False)

        self.set_target_for_source(self.old_model["name"])
        self.active_source_name = self.old_model["name"]
        self.active_target_name = self.target_combo.currentData()
        self.target_model_names_by_source[self.active_source_name] = (
            self.active_target_name
        )
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
            for model_name in self.available_source_model_names:
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

        deck_row = QHBoxLayout()
        deck_row.addWidget(QLabel("Target deck"))
        self.deck_combo = QComboBox()
        deck_row.addWidget(self.deck_combo, 1)
        
        self.use_source_deck_btn = QPushButton("Use source deck as target deck")
        self.use_source_deck_btn.clicked.connect(lambda: self.deck_combo.setCurrentIndex(0))
        self.use_source_deck_btn.setToolTip("Set target deck back to 'Same as original'")
        deck_row.addWidget(self.use_source_deck_btn)
        
        layout.addLayout(deck_row)

        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        options_group.setLayout(options_layout)

        self.open_after_cb = QCheckBox("Open notes in browser/editor after conversion")
        options_layout.addWidget(self.open_after_cb)

        self.delete_original_cb = QCheckBox("Delete original notes after conversion")
        options_layout.addWidget(self.delete_original_cb)

        self.preserve_review_history_cb = QCheckBox(
            "Preserve review history on the merged card"
        )
        self.preserve_review_history_cb.toggled.connect(
            self.update_review_history_controls
        )
        options_layout.addWidget(self.preserve_review_history_cb)

        self.review_history_row = QWidget()
        review_history_row = QHBoxLayout(self.review_history_row)
        review_history_row.setContentsMargins(0, 0, 0, 0)
        self.review_history_source_label = QLabel("Use history from")
        review_history_row.addWidget(self.review_history_source_label)
        self.review_history_source_combo = QComboBox()
        review_history_row.addWidget(self.review_history_source_combo, 1)
        options_layout.addWidget(self.review_history_row)

        self.strip_cloze_cb = QCheckBox("Remove clozes in non-cloze fields")
        options_layout.addWidget(self.strip_cloze_cb)

        layout.addWidget(options_group)

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

    def normalize_review_history_card_ords(self, saved):
        if not isinstance(saved, dict):
            return {}

        normalized = {}
        for model_name, ord_value in saved.items():
            if not isinstance(model_name, str):
                continue
            try:
                ord_value = int(ord_value)
            except (TypeError, ValueError):
                continue
            if ord_value >= 0:
                normalized[model_name] = ord_value
        return normalized

    def load_review_history_card_ords(self):
        return self.normalize_review_history_card_ords(
            state.config.get("review_history_source_card_ord_by_model")
        )

    def set_source_model(self, source_model_name):
        source_model = mw.col.models.by_name(source_model_name)
        if not source_model:
            raise ValueError(f"Source note type not found: {source_model_name}")

        self.old_model = source_model
        self.old_fields = [field["name"] for field in self.old_model["flds"]]
        self.title_label.setText(self.render_title_html())
        self.populate_review_history_cards()

    def get_sample_note(self, source_model_name=None):
        source_name = source_model_name or (
            self.old_model["name"] if self.old_model is not None else None
        )
        if not source_name:
            return None

        note_id = self.sample_note_ids_by_model.get(source_name)
        if note_id is None:
            return None

        try:
            note = mw.col.get_note(note_id)
        except Exception:
            return None

        note_model = note.note_type()
        if not note_model or note_model["name"] != source_name:
            return None

        return note

    def remember_current_review_history_card(self):
        if self.old_model is None:
            return

        selected_ord = self.review_history_source_combo.currentData()
        if selected_ord is None:
            return

        self.review_history_card_ords[self.old_model["name"]] = int(selected_ord)

    def get_saved_review_history_card_ord(self):
        if self.old_model is None:
            return 0

        source_name = self.old_model["name"]
        ord_value = self.review_history_card_ords.get(
            source_name,
            self.initial_review_history_card_ords.get(source_name, 0),
        )
        return ord_value if isinstance(ord_value, int) and ord_value >= 0 else 0

    def build_review_history_card_choices(self):
        note = self.get_sample_note()
        if note is not None:
            cards = sorted(note.cards(), key=lambda card: int(card.ord))
            if cards:
                choices = []
                for card in cards:
                    label = f"Card {int(card.ord) + 1}"
                    template_name = str(card.template().get("name", "")).strip()
                    if template_name:
                        label = f"{label}: {template_name}"
                    choices.append((label, int(card.ord)))
                return choices

        templates = self.old_model.get("tmpls", []) if self.old_model else []
        if not templates:
            templates = [{"name": ""}]

        choices = []
        for ord_value, template in enumerate(templates):
            template_name = str(template.get("name", "")).strip()
            label = f"Card {ord_value + 1}"
            if template_name:
                label = f"{label}: {template_name}"
            choices.append((label, ord_value))
        return choices

    def populate_review_history_cards(self):
        self.review_history_source_combo.clear()

        for label, ord_value in self.build_review_history_card_choices():
            self.review_history_source_combo.addItem(label, ord_value)

        selected_ord = self.get_saved_review_history_card_ord()
        selected_index = self.review_history_source_combo.findData(selected_ord)
        if selected_index == -1:
            selected_index = 0
        self.review_history_source_combo.setCurrentIndex(selected_index)
        self.update_review_history_controls()

    def update_review_history_controls(self):
        is_enabled = (
            self.preserve_review_history_cb.isChecked()
            and self.review_history_source_combo.count() > 1
        )
        self.review_history_row.setVisible(is_enabled)
        self.review_history_source_label.setEnabled(is_enabled)
        self.review_history_source_combo.setEnabled(is_enabled)

    def remember_current_target_selection(self):
        if not self.active_source_name:
            return

        target_model_name = self.target_combo.currentData()
        if target_model_name:
            self.target_model_names_by_source[self.active_source_name] = target_model_name

    def get_selected_target_model_name(self, source_model_name):
        selected_target_name = self.target_model_names_by_source.get(source_model_name)
        if selected_target_name in self.available_model_names:
            return selected_target_name

        preferred_target_name = state.config["preferred_target_models"].get(
            source_model_name
        )
        if preferred_target_name in self.available_model_names:
            return preferred_target_name

        return get_default_target_model_name(
            self.available_model_names,
            [source_model_name],
        )

    def set_target_for_source(self, source_model_name):
        target_model_name = self.get_selected_target_model_name(source_model_name)
        if not target_model_name:
            return

        self.target_combo.blockSignals(True)
        target_index = self.target_combo.findData(target_model_name)
        if target_index != -1:
            self.target_combo.setCurrentIndex(target_index)
        self.target_combo.blockSignals(False)

    def get_saved_mapping_for_pair(self, source_model_name, target_model_name):
        pair_key = self.get_pair_key(source_model_name, target_model_name)
        if pair_key is None:
            return {}

        if pair_key in self.temp_mappings:
            return self.temp_mappings[pair_key]

        if self.has_initial_mapping and pair_key == self.initial_mapping_pair:
            return self.initial_mapping

        map_key = f"{source_model_name}->{target_model_name}"
        try:
            return normalize_field_map(
                state.config["mappings"].get(map_key, {}).get("field_map", {})
            )
        except ValueError:
            return {}

    def get_saved_mapping(self, target_model_name):
        source_model_name = self.old_model["name"] if self.old_model is not None else None
        return self.get_saved_mapping_for_pair(source_model_name, target_model_name)

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
        self.remember_current_review_history_card()
        self.remember_current_target_selection()
        try:
            self.set_source_model(source_model_name)
        except ValueError as exc:
            showInfo(str(exc))
            return

        self.set_target_for_source(source_model_name)
        self.active_source_name = self.old_model["name"]
        self.active_target_name = self.target_combo.currentData()
        self.build_mapping_rows(self.get_saved_mapping(self.active_target_name))

    def on_target_changed(self, target_model_name):
        self.remember_current_mapping()
        self.active_source_name = self.old_model["name"] if self.old_model else None
        self.active_target_name = target_model_name
        if self.active_source_name and target_model_name:
            self.target_model_names_by_source[self.active_source_name] = target_model_name
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

    def accept(self):
        self.remember_current_mapping()
        self.remember_current_review_history_card()
        self.remember_current_target_selection()

        # Save settings for next time
        state.config["open_notes_after"] = self.open_after_cb.isChecked()
        state.config["delete_original"] = self.delete_original_cb.isChecked()
        state.config["preserve_review_history"] = (
            self.preserve_review_history_cb.isChecked()
        )
        state.config["toggle_strip_cloze"] = self.strip_cloze_cb.isChecked()
        state.config["target_deck_id"] = self.deck_combo.currentData()
        state.config["review_history_source_card_ord_by_model"] = dict(
            sorted(self.review_history_card_ords.items())
        )
        state.save_config()
        super().accept()

    def get_settings(self):
        review_history_source_card_ord = self.review_history_source_combo.currentData()
        if self.allow_source_selection:
            review_history_source_card_ord = None

        return {
            "open_notes_after": self.open_after_cb.isChecked(),
            "delete_original": self.delete_original_cb.isChecked(),
            "preserve_review_history": self.preserve_review_history_cb.isChecked(),
            "review_history_source_card_ord": review_history_source_card_ord,
            "review_history_source_card_ord_by_model": dict(
                sorted(self.review_history_card_ords.items())
            ),
            "toggle_strip_cloze": self.strip_cloze_cb.isChecked(),
            "target_deck_id": self.deck_combo.currentData(),
        }

    def get_conversion_plans(self):
        self.remember_current_mapping()
        self.remember_current_target_selection()

        source_model_names = (
            self.available_source_model_names
            if self.allow_source_selection
            else [self.old_model["name"]]
        )
        conversion_plans = {}
        for source_model_name in source_model_names:
            target_model_name = self.get_selected_target_model_name(source_model_name)
            if not target_model_name:
                continue

            target_model = mw.col.models.by_name(target_model_name)
            if not target_model:
                continue

            conversion_plans[source_model_name] = {
                "target_model": target_model,
                "mapping": self.get_saved_mapping_for_pair(
                    source_model_name,
                    target_model_name,
                ),
            }

        return conversion_plans

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


def show_conversion_dialog(
    parent,
    old_model,
    *,
    sample_note_ids_by_model=None,
    initial_review_history_card_ord_by_model=None,
):
    dialog = ConversionDialog(
        parent,
        old_model,
        initial_target_model_name=get_default_target_model_name(
            mw.col.models.all_names(), [old_model["name"]]
        ),
        sample_note_ids_by_model=sample_note_ids_by_model,
        initial_review_history_card_ord_by_model=initial_review_history_card_ord_by_model,
    )
    if not dialog.exec():
        return None, None, None

    return dialog.get_target_model(), dialog.get_mapping(), dialog.get_settings()


def show_multi_source_conversion_dialog(parent, source_model_names, sample_note_ids_by_model):
    source_model_names = list(dict.fromkeys(source_model_names))
    if not source_model_names:
        return None, None

    dialog = ConversionDialog(
        parent,
        None,
        initial_source_model_name=source_model_names[0],
        allow_source_selection=True,
        available_source_model_names=source_model_names,
        sample_note_ids_by_model=sample_note_ids_by_model,
        window_title="Convert Notes",
        title_html="Convert <b>{source}</b> notes",
    )
    if not dialog.exec():
        return None, None

    return dialog.get_conversion_plans(), dialog.get_settings()
