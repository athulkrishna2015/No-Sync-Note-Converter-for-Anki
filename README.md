# [No-Sync Note Converter for Anki](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/)

**No-Sync Note Converter** is an Anki addon designed to change note types (e.g., Basic → Cloze) without triggering the "Full Sync Required" on AnkiWeb.

It bypasses the database schema change by performing a **"Create New → Delete Old"** operation. This preserves your media sync status—crucial for mobile users who want to avoid re-downloading their entire collection just because they changed a card template.

## Features

* **Zero-Sync Overhead:** Converts notes without triggering a full database upload.
* **Unified Conversion Dialog:** Target note type selection and field mapping now happen in one window, with dropdown-based field mapping and ordered multi-field merges.
* **Quick Convert Presets:** Save named source-to-target conversion presets from the dialog and reuse them from one-click quick convert menus that only appear for matching source note types.
* **Single-Step Undo:** Each conversion is merged into one Anki undo action, so **Edit -> Undo** restores the previous note/card state in a single step.
* **GUI Config Editor:** Open the config UI from **Tools -> No-Sync Note Converter Config** or the Add-ons **Config** button to edit general settings, quick presets, and saved mappings without hand-editing JSON.
* **Reviewer Integration:** Convert cards directly while reviewing. The addon will automatically skip to the next card and open a window to edit the new card (perfect for creating Clozes on the fly).
* **Smart Field Mapping:** Automatically suggests logical mappings (e.g., "Text" -> "Front", "Extra" -> "Back") while allowing full manual control.
* **Cloze Stripping:** Option to automatically strip `{{c1::...}}` syntax when converting from a Cloze note type to any non-Cloze note type.
* **Deck & Tag Preservation:** The new card stays in the exact same sub-deck and retains all tags.
* **Safe Failure Handling:** Conversions are validated before they run, and failed conversions are rolled back instead of leaving partially converted notes behind.

## Installation

Install via AnkiWeb: [No-Sync Note Converter](https://ankiweb.net/shared/info/415704549)

## Usage

### 1. In the Browser (Batch Mode)

1. Select the notes you want to convert.
2. Go to **Notes** > **No-Sync Convert Note Type**.
3. **Conversion Dialog:** A dialog will appear for each unique source note type selected. Choose the target note type at the top, then map fields with dropdown selectors below. You can add multiple source fields to one target field, and they will be merged in order.
4. The old notes are deleted, new ones created, and the browser refreshes to show the new notes.
5. If needed, use **Edit -> Undo** once to restore the original notes/cards.

<img width="863" height="722" alt="Screenshot_20260309_185829" src="https://github.com/user-attachments/assets/cf0c8df3-3738-42a9-bdca-edca7c3b6f33" />


### Quick Presets

1. Open the conversion dialog for a source note type.
2. Configure the target note type and field mapping.
3. Click **Save Quick Preset** and give the preset a custom name.
4. The preset will use the current note type as its fixed source note type.
5. Reuse it later from **Notes** > **No-Sync Quick Convert** in the browser, or from **No-Sync Quick Convert** in the reviewer context menu. Only presets that match the current source note type are shown.

Preset customization:
The preset name, target note type, and field mapping are customizable. The source note type is fixed automatically from the note type you created the preset from.

### Config GUI

1. Open **Tools** > **No-Sync Note Converter Config**.
2. Alternatively, open **Tools** > **Add-ons**, select **No-Sync Note Converter**, and click **Config**.
3. Use the GUI tabs to edit the strip-cloze option, quick presets, and saved mappings.
4. Add/Edit actions reuse the same conversion dialog UI, so field mapping stays consistent with normal conversion.
5. In the config editor, source note type and target note type can both be changed directly inside the edit window. There is no separate source-selection popup.

### 2. In the Reviewer (Single Card Mode)

1. While reviewing a card, **Right-Click** (or click the **More** button).
2. Select **No-Sync Convert Note Type**.
3. **Conversion Dialog:** Choose the target note type and map the fields in the same window. You can add multiple source fields to one target field, and they will be merged in order.
4. **Action:** The current card is converted and deleted. Anki will immediately move you to the **Next Card**, and a separate **Browser Window** will open focused on the new card so you can edit it (e.g., to add Cloze deletions).
5. If you want to revert it, use **Edit -> Undo** once.

## Configuration (`config.json`)

You can customize the default behavior in `config.json`.

### Options

* `toggle_strip_cloze`: (`true`/`false`) If true, removes `{{c::}}` syntax when converting *from* a Cloze note type *to* a non-Cloze note type.

### Mappings (Advanced)

While the GUI handles most cases, you can still define permanent rules for `SourceType -> TargetType` in `config.json`. These will be used as the default selections in the conversion dialog.

**Mapping Example:**

```json
"Cloze->Basic": {
    "source_type": "Cloze",
    "target_type": "Basic",
    "field_map": {
        "Front": ["Text"],
        "Back": ["Extra"]
    }
}
```

### Quick Convert Presets (Advanced)

Quick presets are stored in `quick_convert_presets` as named conversion rules that can be applied without reopening the dialog.
Each preset has a fixed `source_type`, so a Cloze preset will not be shown for Basic notes, and a Basic preset will not be shown for Cloze notes.

The shipped `config.json` provides defaults, but once you edit settings in Anki, the live addon config is stored by Anki in addon metadata.

**Preset Example:**

```json
"quick_convert_presets": [
    {
        "name": "Basic to Cloze",
        "source_type": "Basic",
        "target_type": "Cloze",
        "field_map": {
            "Text": ["Front", "Back"],
            "Extra": ["Extra"]
        }
    }
]
```

## Project Layout

The addon is now split into smaller modules for easier maintenance:

* `__init__.py`: addon entrypoint and hook registration.
* `state.py`: shared config state, defaults, and constants.
* `mapping.py`: mapping validation, preset helpers, and cloze stripping.
* `conversion_dialog.py`: main conversion dialog UI.
* `config_dialog.py`: addon config window, support tab, and Tools menu registration.
* `operations.py`: note conversion logic and custom undo handling.
* `browser_actions.py`: Browser menu actions and quick-convert integration.
* `reviewer_actions.py`: Reviewer context-menu actions.

## ⚠️ Important Limitations

* **Review History Reset:** Because the addon creates a *fresh* note and deletes the old one, **review history (scheduling) for that specific card is lost.** The card becomes "New".
* **Full Sync vs. Media Sync:** This addon prevents a "Full Database Sync," but if you change media filenames or add images, a media sync will still occur (which is normal and fast).
* **Stale Presets/Mappings:** If source or target fields are renamed later, the addon will block the conversion and ask you to reopen the conversion dialog and update the mapping.

## Changelog

### 10-03-2026

* Added single-step undo for note conversion, so one **Edit -> Undo** restores the previous notes/cards.
* Added a direct **Tools -> No-Sync Note Converter Config** action.
* Refactored the addon into smaller modules to make the codebase easier to maintain.

### 09-03-2026

* Fixed conversion rollback so failed runs do not leave partially converted notes behind.
* Fixed deck preservation so conversions no longer mutate the target note type's default deck.
* Fixed cloze stripping detection to use the real note type kind instead of matching names like `"Cloze"` or `"Basic"`.
* Added validation for saved mappings and quick presets so stale field references are blocked with an explicit error instead of silently dropping content.
* Added a GUI config editor behind the Add-ons **Config** button for managing presets and mappings with the existing conversion dialog.
* Updated the config editor so source note type can be changed inside the preset/mapping edit window without a separate source picker.

### 22-02-2026

* Fixed Cloze-to-Basic cloze stripping so MathJax/LaTeX content with nested braces is preserved correctly (prevents broken formulas like `\mathbf{E}` / `\frac{...}{...}` after conversion).

## License

MIT License. Free to use and modify.
