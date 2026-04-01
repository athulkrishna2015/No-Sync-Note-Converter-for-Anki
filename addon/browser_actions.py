from aqt import mw
from aqt.qt import QAction, QMenu
from aqt.utils import showInfo, tooltip

from . import state
from .conversion_dialog import (
    show_conversion_dialog,
    show_multi_source_conversion_dialog,
)
from .mapping import (
    format_quick_preset_label,
    get_quick_convert_preset,
    get_quick_convert_presets,
    remember_conversion_pair,
)
from .operations import (
    core_convert_logic,
    finish_browser_conversion,
    group_note_ids_by_model,
)


def _get_sample_note_ids_by_model(notes_by_mid):
    sample_note_ids_by_model = {}
    for mid, model_nids in notes_by_mid.items():
        old_model = mw.col.models.get(mid)
        if not old_model or not model_nids:
            continue

        best_nid = model_nids[0]
        best_card_count = -1
        for nid in model_nids:
            try:
                note = mw.col.get_note(nid)
                card_count = len(note.cards())
            except Exception:
                card_count = -1

            if card_count > best_card_count:
                best_nid = nid
                best_card_count = card_count

        sample_note_ids_by_model[old_model["name"]] = best_nid

    return sample_note_ids_by_model


def on_browser_convert(browser):
    nids = browser.selectedNotes()
    if not nids:
        tooltip("No notes selected.")
        return

    notes_by_mid = group_note_ids_by_model(nids)
    model_names_by_mid = {}
    for mid, model_nids in notes_by_mid.items():
        old_model = mw.col.models.get(mid)
        if not old_model:
            continue
        model_names_by_mid[mid] = old_model["name"]
    sample_note_ids_by_model = _get_sample_note_ids_by_model(notes_by_mid)

    all_created_nids = []
    open_after = False
    if len(model_names_by_mid) > 1:
        conversion_plans, settings = show_multi_source_conversion_dialog(
            browser,
            list(model_names_by_mid.values()),
            sample_note_ids_by_model,
        )
        if not conversion_plans:
            return

        if settings.get("open_notes_after"):
            open_after = True

        for mid, model_nids in notes_by_mid.items():
            source_model_name = model_names_by_mid.get(mid)
            conversion_plan = conversion_plans.get(source_model_name)
            if not conversion_plan:
                continue

            remember_conversion_pair(
                source_model_name,
                conversion_plan["target_model"]["name"],
                conversion_plan["mapping"],
            )
            created_nids = core_convert_logic(
                model_nids,
                conversion_plan["target_model"],
                override_mapping=conversion_plan["mapping"],
                override_settings=settings,
            )
            all_created_nids.extend(created_nids)
    else:
        for mid, model_nids in notes_by_mid.items():
            old_model = mw.col.models.get(mid)
            if not old_model:
                continue

            target_model, mapping, settings = show_conversion_dialog(
                browser,
                old_model,
                sample_note_ids_by_model={
                    old_model["name"]: sample_note_ids_by_model.get(old_model["name"])
                },
            )
            if not target_model:
                continue

            if settings.get("open_notes_after"):
                open_after = True

            remember_conversion_pair(old_model["name"], target_model["name"], mapping)
            created_nids = core_convert_logic(
                model_nids,
                target_model,
                override_mapping=mapping,
                override_settings=settings,
            )
            all_created_nids.extend(created_nids)

    if all_created_nids:
        if open_after:
            finish_browser_conversion(browser, all_created_nids)
        else:
            mw.reset()
            if hasattr(browser, "search"):
                browser.search()
            else:
                browser.onSearch(reset=False)
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
                lambda _,
                preset_source=preset["source_type"],
                preset_target=preset["target_type"],
                preset_name=preset["name"]: on_browser_quick_convert(
                    browser, preset_source, preset_target, preset_name
                )
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
        if state.config.get("open_notes_after", True):
            finish_browser_conversion(browser, created_nids)
        else:
            mw.reset()
            if hasattr(browser, "search"):
                browser.search()
            else:
                browser.onSearch(reset=False)
        
        message = (
            f"Converted {len(created_nids)} notes with preset "
            f"'{preset_name}' ({source_model_name} -> {target_model_name})."
        )
        if skipped_count:
            message += f" Skipped {skipped_count} notes."
        tooltip(message)


def setup_browser_menu(browser):
    action = QAction("No-Sync Convert Note Type", browser)
    action.triggered.connect(lambda: on_browser_convert(browser))
    browser.form.menu_Notes.addSeparator()
    browser.form.menu_Notes.addAction(action)

    quick_menu = QMenu("No-Sync Quick Convert", browser.form.menu_Notes)
    quick_menu.aboutToShow.connect(
        lambda: populate_browser_quick_convert_menu(browser, quick_menu)
    )
    browser.form.menu_Notes.addMenu(quick_menu)


def setup_browser_context_menu(browser, menu):
    menu.addSeparator()
    action = menu.addAction("No-Sync Convert Note Type")
    action.triggered.connect(lambda: on_browser_convert(browser))

    quick_menu = menu.addMenu("No-Sync Quick Convert")
    # Populate the quick menu immediately for the context menu
    populate_browser_quick_convert_menu(browser, quick_menu)
