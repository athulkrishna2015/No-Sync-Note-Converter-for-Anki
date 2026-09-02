from aqt import mw
from aqt.qt import *

from .. import state


class GeneralTab(QWidget):
    def __init__(self, parent=None, working_toggle_strip_cloze=True):
        super().__init__(parent)
        self._working_toggle_strip_cloze = working_toggle_strip_cloze
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.open_after_checkbox = QCheckBox("Open notes in browser/editor after conversion")
        self.open_after_checkbox.setChecked(state.config.get("open_notes_after", True))
        layout.addWidget(self.open_after_checkbox)

        self.delete_original_checkbox = QCheckBox("Delete original notes after conversion")
        self.delete_original_checkbox.setChecked(state.config.get("delete_original", True))
        layout.addWidget(self.delete_original_checkbox)

        self.preserve_review_history_checkbox = QCheckBox(
            "Preserve review history on the merged card by default"
        )
        self.preserve_review_history_checkbox.setChecked(
            state.config.get("preserve_review_history", True)
        )
        layout.addWidget(self.preserve_review_history_checkbox)

        self.strip_cloze_checkbox = QCheckBox(
            "Strip cloze markup when converting from a Cloze note type to a non-Cloze note type"
        )
        self.strip_cloze_checkbox.setChecked(self._working_toggle_strip_cloze)
        layout.addWidget(self.strip_cloze_checkbox)

        layout.addSpacing(10)
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
        layout.addLayout(deck_row)

        general_hint = QLabel(
            "Use the tabs below to manage quick presets and saved field mappings with the same GUI used during conversion."
        )
        general_hint.setWordWrap(True)
        layout.addWidget(general_hint)
        layout.addStretch()
