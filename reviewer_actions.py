from aqt import dialogs, mw
from aqt.utils import showInfo, tooltip

from .conversion_dialog import show_conversion_dialog
from .mapping import (
    format_quick_preset_label,
    get_quick_convert_preset,
    get_quick_convert_presets,
    remember_conversion_pair,
)
from .operations import core_convert_logic


def on_reviewer_convert(reviewer):
    card = reviewer.card
    if not card:
        return

    old_note = card.note()
    old_model = old_note.note_type()

    target_model, mapping = show_conversion_dialog(mw, old_model)
    if not target_model:
        return

    remember_conversion_pair(old_model["name"], target_model["name"], mapping)

    created_nids = core_convert_logic([card.nid], target_model, override_mapping=mapping)

    if created_nids:
        reviewer.nextCard()
        mw.reset()

        query = f"nid:{created_nids[0]}"
        dialogs.open("Browser", mw, search=[query])


def on_reviewer_quick_convert(
    reviewer, source_model_name, target_model_name, preset_name
):
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
        tooltip(
            f"Converted with preset '{preset_name}' ({source_model_name} -> {target_model_name})."
        )


def setup_reviewer_menu(reviewer, menu):
    action = menu.addAction("No-Sync Convert Note Type")
    action.triggered.connect(lambda: on_reviewer_convert(reviewer))

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
            lambda _,
            preset_source=preset["source_type"],
            preset_target=preset["target_type"],
            preset_name=preset["name"]: on_reviewer_quick_convert(
                reviewer, preset_source, preset_target, preset_name
            )
        )
