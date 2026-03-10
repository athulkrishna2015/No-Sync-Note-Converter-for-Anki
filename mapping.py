import re

from aqt import mw
from aqt.qt import QInputDialog, QLineEdit
from aqt.utils import showInfo

from . import state


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
            problems.append("unknown target fields: " + ", ".join(invalid_targets))
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
    mapping = state.config["mappings"].get(map_key)
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

    source_names = list(
        dict.fromkeys(name for name in (source_model_names or []) if name)
    )
    source_set = set(source_names)
    preferred_targets = state.config["preferred_target_models"]

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
        preferred_targets = state.config["preferred_target_models"]
        if preferred_targets.get(source_model_name) != target_model_name:
            preferred_targets[source_model_name] = target_model_name
            changed = True

    map_key = f"{source_model_name}->{target_model_name}"
    mapping_entry = {
        "source_type": source_model_name,
        "target_type": target_model_name,
        "field_map": field_mapping,
    }
    if state.config["mappings"].get(map_key) != mapping_entry:
        state.config["mappings"][map_key] = mapping_entry
        changed = True

    if changed:
        state.save_config()


def get_quick_convert_presets(source_model_name=None):
    presets = []
    for preset in state.config["quick_convert_presets"]:
        target_model = mw.col.models.by_name(preset["target_type"])
        if not target_model:
            continue
        if source_model_name and preset["source_type"] != source_model_name:
            continue
        presets.append(preset)
    return sorted(presets, key=lambda preset: preset["name"].lower())


def get_quick_convert_preset(source_model_name, target_model_name, preset_name):
    for preset in state.config["quick_convert_presets"]:
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

    for i, preset in enumerate(state.config["quick_convert_presets"]):
        if (
            preset["name"] == preset_name
            and preset["source_type"] == source_model_name
            and preset["target_type"] == target_model_name
        ):
            state.config["quick_convert_presets"][i] = preset_entry
            state.save_config()
            return "updated"

    state.config["quick_convert_presets"].append(preset_entry)
    state.save_config()
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
