# [No-Sync Note Converter for Anki](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/)

**No-Sync Note Converter** is an Anki addon designed to change note types (e.g., Basic → Cloze) without triggering the "Full Sync Required" on AnkiWeb.

It bypasses the database schema change by performing a **"Create New → Delete Old"** operation. This preserves your media sync status—crucial for mobile users who want to avoid re-downloading their entire collection just because they changed a card template.

## Features

* **Zero-Sync Overhead:** Converts notes without triggering a full database upload.
* **Field Mapping GUI:** A new interactive dialog allows you to map fields between note types on the fly. No more lost data in "Extra" fields!
* **Reviewer Integration:** Convert cards directly while reviewing. The addon will automatically skip to the next card and open a window to edit the new card (perfect for creating Clozes on the fly).
* **Smart Field Mapping:** Automatically suggests logical mappings (e.g., "Text" -> "Front", "Extra" -> "Back") while allowing full manual control.
* **Cloze Stripping:** Option to automatically strip `{{c1::...}}` syntax when converting from Cloze to Basic.
* **Deck & Tag Preservation:** The new card stays in the exact same sub-deck and retains all tags.

## Installation

Install via AnkiWeb: [No-Sync Note Converter](https://ankiweb.net/shared/info/415704549)

## Usage

### 1. In the Browser (Batch Mode)

1. Select the notes you want to convert.
2. Go to **Notes** > **No-Sync Convert Note Type**.
3. Select the **Target Note Type**.
4. **Field Mapping Dialog:** A dialog will appear for each unique note type selected. Choose which source fields map to which target fields.
5. The old notes are deleted, new ones created, and the editor sidebar will refresh to show the new notes.

### 2. In the Reviewer (Single Card Mode)

1. While reviewing a card, **Right-Click** (or click the **More** button).
2. Select **No-Sync Convert Note Type**.
3. Choose the Target Note Type.
4. **Field Mapping Dialog:** Map the fields for the current note.
5. **Action:** The current card is converted and deleted. Anki will immediately move you to the **Next Card**, and a separate **Browser Window** will open focused on the new card so you can edit it (e.g., to add Cloze deletions).

## Configuration (`config.json`)

You can customize the default behavior in `config.json`.

### Options

* `toggle_strip_cloze`: (`true`/`false`) If true, removes `{{c::}}` syntax when converting *from* a Cloze type *to* a Basic type.

### Mappings (Advanced)

While the GUI handles most cases, you can still define permanent rules for `SourceType -> TargetType` in `config.json`. These will be used as the default selections in the mapping dialog.

**Example:**

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

## ⚠️ Important Limitations

* **Review History Reset:** Because the addon creates a *fresh* note and deletes the old one, **review history (scheduling) for that specific card is lost.** The card becomes "New".
* **Full Sync vs. Media Sync:** This addon prevents a "Full Database Sync," but if you change media filenames or add images, a media sync will still occur (which is normal and fast).

## License

MIT License. Free to use and modify.
