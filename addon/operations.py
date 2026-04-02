from anki.consts import MODEL_CLOZE
from aqt import mw
from aqt.utils import showInfo

from . import state
from .mapping import get_effective_field_map, strip_cloze_tags


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


def _get_card_by_ord(cards, ord_value):
    try:
        ord_value = int(ord_value)
    except (TypeError, ValueError):
        return None

    for card in cards:
        if int(card.ord) == ord_value:
            return card
    return None


def _copy_card_scheduling(source_card, target_card):
    for attr in (
        "type",
        "queue",
        "due",
        "ivl",
        "factor",
        "reps",
        "lapses",
        "left",
        "odue",
        "odid",
        "flags",
        "custom_data",
        "memory_state",
        "desired_retention",
        "decay",
        "last_review_time",
    ):
        setattr(target_card, attr, getattr(source_card, attr))


def _get_preferred_review_history_ord(settings, source_model_name):
    preferred_ord = settings.get("review_history_source_card_ord")
    if preferred_ord is not None:
        return preferred_ord

    saved_ords = settings.get("review_history_source_card_ord_by_model", {})
    if isinstance(saved_ords, dict):
        return saved_ords.get(source_model_name, 0)

    return 0


def _preserve_review_history(old_cards, new_note, preferred_source_ord, delete_original):
    try:
        if not old_cards or not new_note.id:
            return

        source_card = _get_card_by_ord(old_cards, preferred_source_ord) or old_cards[0]
        target_cards = new_note.cards()
        if not target_cards:
            return

        target_card = _get_card_by_ord(target_cards, source_card.ord) or target_cards[0]
        _copy_card_scheduling(source_card, target_card)
        mw.col.update_card(target_card)
    except Exception:
        # Review-history transfer is best-effort and should not abort conversion.
        return


def core_convert_logic(nids, target_model, override_mapping=None, override_settings=None):
    """
    Performs the actual Create New -> Delete Old logic.
    Returns a list of new Note IDs.
    """
    if not nids:
        return []

    settings = state.config.copy()
    if override_settings:
        settings.update(override_settings)

    mw.progress.start()

    created_nids = []
    target_model_name = target_model["name"]
    target_is_cloze = target_model["type"] == MODEL_CLOZE
    undo_entry = None

    try:
        undo_entry = mw.col.add_custom_undo_entry("Convert Note Type")

        def convert_notes():
            pending_nids = []
            mapping_cache = {}

            for nid in nids:
                old_note = mw.col.get_note(nid)
                old_model = old_note.note_type()
                if not old_model:
                    raise ValueError(
                        f"Could not load the source note type for note {nid}."
                    )

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

                strip_cloze = settings.get("toggle_strip_cloze", True)

                if field_map is not None:
                    for target_field, source_fields in field_map.items():
                        combined_content = []
                        for src in source_fields:
                            content = old_note[src]
                            if strip_cloze and source_is_cloze and not target_is_cloze:
                                content = strip_cloze_tags(content)
                            combined_content.append(content)

                        new_note[target_field] = "<br><br>".join(combined_content)
                else:
                    for field in old_note.keys():
                        if field in new_note:
                            content = old_note[field]
                            if strip_cloze and source_is_cloze and not target_is_cloze:
                                content = strip_cloze_tags(content)
                            new_note[field] = content

                old_cards = old_note.cards()
                deck_id = settings.get("target_deck_id")
                if not deck_id:
                    deck_id = old_cards[0].did if old_cards else 1
                new_note.tags = old_note.tags

                mw.col.add_note(new_note, deck_id=deck_id)
                pending_nids.append(new_note.id)

                if not settings.get("target_deck_id") and old_cards:
                    for target_card in new_note.cards():
                        source_card = _get_card_by_ord(old_cards, target_card.ord) or old_cards[0]
                        if source_card.did != target_card.did:
                            target_card.did = source_card.did
                            mw.col.update_card(target_card)

                if settings.get("preserve_review_history", True):
                    _preserve_review_history(
                        old_cards,
                        new_note,
                        _get_preferred_review_history_ord(
                            settings,
                            old_model["name"],
                        ),
                        settings.get("delete_original", True),
                    )

                if settings.get("delete_original", True):
                    mw.col.remove_notes([nid])

            created_nids.extend(pending_nids)

        mw.col.db.transact(convert_notes)
        mw.col.merge_undo_entries(undo_entry)

    except Exception as e:
        showInfo(
            f"Error during conversion from note(s) to '{target_model_name}': {str(e)}\n\n"
            "No notes were converted."
        )
        return []
    finally:
        mw.progress.finish()

    return created_nids
