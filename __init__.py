import re
from aqt import mw, dialogs
from aqt.qt import *
from aqt.utils import showInfo, tooltip
from anki.hooks import addHook
from aqt.gui_hooks import reviewer_will_show_context_menu

# Load Config
config = mw.addonManager.getConfig(__name__)

def strip_cloze_tags(text):
    """
    Converts '{{c1::Answer::Hint}}' to 'Answer'.
    """
    pattern = r"\{\{c\d+::(.*?)(?::.*?)?\}\}"
    while re.search(pattern, text):
        text = re.sub(pattern, r"\1", text)
    return text

def get_target_model(parent_window):
    """
    Asks the user to select the target note type.
    """
    models = mw.col.models.all_names()
    target_model_name, ok = QInputDialog.getItem(
        parent_window, 
        "Select Target Note Type", 
        "Choose note type:", 
        models, 
        0, 
        False
    )
    if ok:
        return mw.col.models.by_name(target_model_name)
    return None

def core_convert_logic(nids, target_model):
    """
    Performs the actual Create New -> Delete Old logic.
    Returns a list of new Note IDs.
    """
    mw.checkpoint("No-Sync Conversion")
    mw.progress.start()
    
    created_nids = []
    target_model_name = target_model['name']

    try:
        for nid in nids:
            old_note = mw.col.get_note(nid)
            old_model_name = old_note.note_type()['name']
            
            # Create new note
            new_note = mw.col.new_note(target_model)
            
            # --- MAPPING LOGIC ---
            map_key = f"{old_model_name}->{target_model_name}"
            mapping = config['mappings'].get(map_key)
            
            if mapping:
                for target_field, source_fields in mapping['field_map'].items():
                    if target_field in new_note:
                        combined_content = []
                        for src in source_fields:
                            if src in old_note:
                                content = old_note[src]
                                # Strip Cloze if converting FROM Cloze TO Basic (and toggle is On)
                                if config['toggle_strip_cloze'] and "Cloze" in old_model_name and "Basic" in target_model_name:
                                    content = strip_cloze_tags(content)
                                combined_content.append(content)
                        
                        new_note[target_field] = "<br><br>".join(combined_content)
            else:
                # Fallback: Naive Name Matching
                for field in old_note.keys():
                    if field in new_note:
                         new_note[field] = old_note[field]

            # --- DECK & TAGS ---
            old_cards = old_note.cards()
            if old_cards:
                did = old_cards[0].did
                new_note.note_type()['did'] = did 
            
            new_note.tags = old_note.tags

            # --- SWAP ---
            # Add new note
            mw.col.add_note(new_note, deck_id=old_cards[0].did if old_cards else 1)
            created_nids.append(new_note.id)
            
            # Delete old note
            mw.col.remove_notes([nid])

    except Exception as e:
        showInfo(f"Error during conversion: {str(e)}")
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

    target_model = get_target_model(browser)
    if not target_model:
        return

    created_nids = core_convert_logic(nids, target_model)
    
    if created_nids:
        mw.reset()
        
        # 1. Search for the new notes to filter the view
        query = f"nid:{','.join(map(str, created_nids))}"
        browser.search_for(query)
        
        # 2. Force Selection so the Editor Sidebar populates
        # Use selectAll() (Qt Standard) which works on QTableView
        try:
            browser.table.selectAll()
        except:
            pass # Fail silently if UI is in weird state
            
        tooltip(f"Converted {len(created_nids)} notes.")

def setup_browser_menu(browser):
    a = QAction("No-Sync Convert Note Type", browser)
    a.triggered.connect(lambda: on_browser_convert(browser))
    browser.form.menu_Notes.addSeparator()
    browser.form.menu_Notes.addAction(a)

# --- REVIEWER HANDLER ---
def on_reviewer_convert(reviewer):
    card = reviewer.card
    if not card:
        return

    # 1. Ask for Model
    target_model = get_target_model(mw)
    if not target_model:
        return

    # 2. Convert
    created_nids = core_convert_logic([card.nid], target_model)

    # 3. Handle Reviewer Flow
    if created_nids:
        # Move reviewer to next card FIRST (since old one is gone)
        reviewer.nextCard()
        mw.reset()
        
        # Open Browser to the NEW card so user can add Clozes
        # FIX: Pass search as a LIST [query] to avoid unpacking chars
        query = f"nid:{created_nids[0]}"
        dialogs.open("Browser", mw, search=[query])

def setup_reviewer_menu(reviewer, menu):
    a = menu.addAction("No-Sync Convert Note Type")
    a.triggered.connect(lambda: on_reviewer_convert(reviewer))

# --- HOOKS ---
addHook("browser.setupMenus", setup_browser_menu)
reviewer_will_show_context_menu.append(setup_reviewer_menu)