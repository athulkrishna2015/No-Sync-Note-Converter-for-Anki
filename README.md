# [No-Sync Note Converter for Anki](https://github.com/athulkrishna2015/No-Sync-Note-Converter-for-Anki/)

**No-Sync Note Converter** is an Anki addon designed to change note types (e.g., Basic → Cloze) without triggering the "Full Sync Required" on AnkiWeb.

It bypasses the database schema change by performing a **"Create New → Delete Old"** operation. This preserves your media sync status—crucial for mobile users who want to avoid re-downloading their entire collection just because they changed a card template.

## Features

* **Zero-Sync Overhead:** Converts notes without triggering a full database upload.
* **Reviewer Integration:** Convert cards directly while reviewing. The addon will automatically skip to the next card and open a window to edit the new card (perfect for creating Clozes on the fly).
* **Smart Field Mapping:** Merges multiple fields (e.g., Front + Back) into a single destination field based on your config.
* **Cloze Stripping:** Option to automatically strip `{{c1::...}}` syntax when converting from Cloze to Basic.
* **Deck & Tag Preservation:** The new card stays in the exact same sub-deck and retains all tags.

## Installation

Install via AnkiWeb: [No-Sync Note Converter](https://ankiweb.net/shared/info/415704549)

5. Restart Anki.

## Configuration (`config.json`)

You can customize how fields are merged in `config.json`.

### Options

* `toggle_strip_cloze`: (`true`/`false`) If true, removes `{{c::}}` syntax when converting *from* a Cloze type *to* a Basic type.

### Mappings

Define rules for `SourceType -> TargetType`.

**Example:** Converting **Basic** (Front, Back) to **Cloze** (Text, Extra):

```json
"Basic->Cloze": {
    "source_type": "Basic",
    "target_type": "Cloze",
    "field_map": {
        "Text": ["Front", "Back"],   // Merges Front and Back into Text
        "Extra": ["Extra"]           // Moves Extra to Extra
    }
}

```

## Usage

### 1. In the Browser (Batch Mode)

1. Select the notes you want to convert.
2. Go to **Notes** > **No-Sync Convert Note Type**.
3. Select the **Target Note Type**.
4. The old notes are deleted, new ones created, and the editor sidebar will refresh to show the new notes.

### 2. In the Reviewer (Single Card Mode)

1. While reviewing a card, **Right-Click** (or click the **More** button).
2. Select **No-Sync Convert Note Type**.
3. Choose the Target Note Type.
4. **Action:** The current card is converted and deleted. Anki will immediately move you to the **Next Card**, and a separate **Browser Window** will open focused on the new card so you can edit it (e.g., to add Cloze deletions).

## ⚠️ Important Limitations

* **Review History Reset:** Because the addon creates a *fresh* note and deletes the old one, **review history (scheduling) for that specific card is lost.** The card becomes "New".
* **Full Sync vs. Media Sync:** This addon prevents a "Full Database Sync," but if you change media filenames or add images, a media sync will still occur (which is normal and fast).

## License

MIT License. Free to use and modify.
