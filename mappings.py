"""
mappings.py - Python fallback Geyser mappings generator.
Replicates the original converter.sh jq pipeline for generating geyser_mappings.json
from Java Edition item model overrides. Supports ItemsAdder, Oraxen, and Nexo namespaces.

This is called from manager.py as a fallback/supplement when converter.sh either:
1. Takes the early exit branch (no item models in minecraft namespace)
2. Generates an empty/invalid config.json
3. Fails to produce geyser_mappings.json

The generated file matches the exact Geyser format:
{
  "format_version": "1",
  "items": {
    "minecraft:<item>": [
      {
        "name": "gmdl_<N>",
        "allow_offhand": true,
        "icon": "<icon_name>",
        "custom_model_data": <N>,
        ...
      }
    ]
  }
}
"""
import os
import json
import glob
import math


def generate_geyser_mappings(pack_dir="pack"):
    """
    Scans pack_dir/assets/*/models/item/*.json for Java item model overrides
    and generates geyser_mappings.json in the same format as converter.sh.
    """
    print("[MAPPINGS] Starting Geyser mappings generation (Python fallback)...")

    # Find all item model JSON files across ALL namespaces
    # Original: ./assets/minecraft/models/item/*.json
    # Extended: ./assets/*/models/item/*.json (for oraxen, nexo, itemsadder, etc.)
    search_patterns = [
        os.path.join(pack_dir, "assets", "*", "models", "item", "*.json"),
        os.path.join(pack_dir, "assets", "*", "models", "items", "*.json"),
        # Also check staging directory (when run from converter.sh working dir)
        os.path.join("assets", "*", "models", "item", "*.json"),
        os.path.join("assets", "*", "models", "items", "*.json"),
        os.path.join("staging", "assets", "*", "models", "item", "*.json"),
        os.path.join("staging", "assets", "*", "models", "items", "*.json"),
    ]

    model_files = []
    for pattern in search_patterns:
        model_files.extend(glob.glob(pattern))
    # Deduplicate
    model_files = list(set(os.path.normpath(f) for f in model_files))

    print(f"[MAPPINGS] Found {len(model_files)} item model file(s) to inspect.")

    if not model_files:
        print("[MAPPINGS] No item model files found, skipping mappings generation.")
        return

    # Load item_texture.json for bedrock icon lookups (if downloaded by converter.sh)
    bedrock_icons = {}
    icon_paths = [
        "scratch_files/item_texture.json",
        "staging/scratch_files/item_texture.json",
    ]
    for ip in icon_paths:
        if os.path.isfile(ip):
            try:
                with open(ip, "r", encoding="utf-8") as f:
                    bedrock_icons = json.load(f)
                print(f"[MAPPINGS] Loaded bedrock icon texture map from {ip}")
                break
            except Exception:
                pass

    # Load item_mappings.json for max_damage lookups
    max_damage_map = {}
    mapping_paths = [
        "scratch_files/item_mappings.json",
        "staging/scratch_files/item_mappings.json",
    ]
    for mp in mapping_paths:
        if os.path.isfile(mp):
            try:
                with open(mp, "r", encoding="utf-8") as f:
                    item_mappings = json.load(f)
                for java_id, props in item_mappings.items():
                    if isinstance(props, dict) and "max_damage" in props:
                        short_name = java_id.split(":")[-1] if ":" in java_id else java_id
                        max_damage_map[short_name] = props["max_damage"]
                print(f"[MAPPINGS] Loaded max_damage map from {mp}")
                break
            except Exception:
                pass

    # Collect all override entries, mimicking the original jq pipeline:
    # [inputs | {(input_filename | sub(...; .itemname)): .overrides?[]?}]
    all_entries = []
    global_idx = 0

    for mfile in sorted(model_files):
        try:
            item_name = os.path.splitext(os.path.basename(mfile))[0]

            with open(mfile, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                continue

            overrides = data.get("overrides", [])
            if not isinstance(overrides, list):
                continue

            for override in overrides:
                if not isinstance(override, dict):
                    continue

                predicate = override.get("predicate", {})
                model_ref = override.get("model", "")
                if not model_ref:
                    continue

                cmd = predicate.get("custom_model_data")
                dmg_raw = predicate.get("damage")
                damaged = predicate.get("damaged")

                # Skip entries with no predicates (vanilla model)
                if cmd is None and dmg_raw is None and damaged is None:
                    continue

                # Calculate actual damage value (same as original jq: damage * maxdur | ceil)
                damage_val = None
                if dmg_raw is not None:
                    max_dur = max_damage_map.get(item_name, 1)
                    damage_val = math.ceil(float(dmg_raw) * max_dur)

                # Unbreakable flag (same as original: damaged == 0 -> true)
                unbreakable = True if damaged == 0 else None

                cmd_val = int(cmd) if cmd is not None else None

                # Resolve model namespace and path
                if ":" in model_ref:
                    namespace = model_ref.split(":")[0]
                    model_subpath = model_ref.split(":", 1)[1]
                else:
                    namespace = "minecraft"
                    model_subpath = model_ref

                model_path_parts = model_subpath.split("/")
                model_dir = "/".join(model_path_parts[:-1]) if len(model_path_parts) > 1 else ""
                model_name = model_path_parts[-1]

                # Resolve bedrock icon
                icon_info = bedrock_icons.get(item_name, {"icon": "camera", "frame": 0})
                if not isinstance(icon_info, dict):
                    icon_info = {"icon": "camera", "frame": 0}

                # Build path for the model json file
                json_path = f"./assets/{namespace}/models/{model_subpath}.json"

                # Assign sequential geyserID (same as original: gmdl_1, gmdl_2, ...)
                global_idx += 1
                geyser_id = f"gmdl_{global_idx}"

                entry = {
                    "item": item_name,
                    "bedrock_icon": icon_info,
                    "nbt": {},
                    "path": json_path,
                    "namespace": namespace,
                    "model_path": model_dir,
                    "model_name": model_name,
                    "generated": False,
                    "geyserID": geyser_id,
                    "path_hash": geyser_id,
                }

                if damage_val is not None:
                    entry["nbt"]["Damage"] = damage_val
                if unbreakable is not None:
                    entry["nbt"]["Unbreakable"] = unbreakable
                if cmd_val is not None:
                    entry["nbt"]["CustomModelData"] = cmd_val

                all_entries.append(entry)

        except Exception as e:
            print(f"[MAPPINGS] Error parsing model file {mfile}: {e}")

    print(f"[MAPPINGS] Found {len(all_entries)} custom item overrides total.")

    if not all_entries:
        print("[MAPPINGS] No custom overrides found, writing minimal mappings.")
        result = {"format_version": "1", "items": {}}
    else:
        # Group entries by item name (same as original jq: group_by(.key) | add)
        items_map = {}
        for entry in all_entries:
            item_key = f"minecraft:{entry['item']}"
            if item_key not in items_map:
                items_map[item_key] = []

            mapping_entry = {
                "name": entry["path_hash"],
                "allow_offhand": True,
                "icon": entry["path_hash"] if entry["generated"] else entry["bedrock_icon"].get("icon", "camera"),
            }

            if not entry["generated"] and "frame" in entry["bedrock_icon"]:
                mapping_entry["frame"] = entry["bedrock_icon"]["frame"]

            nbt = entry.get("nbt", {})
            if "CustomModelData" in nbt:
                mapping_entry["custom_model_data"] = nbt["CustomModelData"]
            if "Damage" in nbt:
                mapping_entry["damage_predicate"] = nbt["Damage"]
            if "Unbreakable" in nbt:
                mapping_entry["unbreakable"] = nbt["Unbreakable"]

            items_map[item_key].append(mapping_entry)

        result = {
            "format_version": "1",
            "items": items_map,
        }

    # Write to target directories
    out_paths = [
        "staging/target/geyser_mappings.json",
        "target/geyser_mappings.json",
        "staging/target/unpackaged/geyser_mappings.json",
    ]
    for outp in out_paths:
        try:
            os.makedirs(os.path.dirname(outp), exist_ok=True)
            # Only write if file doesn't exist or is empty/invalid
            should_write = True
            if os.path.isfile(outp) and os.path.getsize(outp) > 50:
                try:
                    with open(outp, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                    # If existing file has items already, don't overwrite
                    if isinstance(existing, dict) and existing.get("items") and len(existing["items"]) > 0:
                        print(f"[MAPPINGS] {outp} already has {len(existing['items'])} items, skipping overwrite.")
                        should_write = False
                except Exception:
                    pass

            if should_write:
                with open(outp, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2)
                item_count = len(result.get("items", {}))
                entry_count = sum(len(v) for v in result.get("items", {}).values())
                print(f"[MAPPINGS] Wrote {outp} ({item_count} items, {entry_count} overrides)")
        except Exception as e:
            print(f"[MAPPINGS] Warning writing to {outp}: {e}")

    # Also write config.json if it doesn't exist (for converter.sh to consume)
    config_path = "staging/config.json" if os.path.isdir("staging") else "config.json"
    if not os.path.isfile(config_path) or os.path.getsize(config_path) < 10:
        try:
            config_obj = {}
            for entry in all_entries:
                config_obj[entry["geyserID"]] = entry
            os.makedirs(os.path.dirname(config_path) if os.path.dirname(config_path) else ".", exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_obj, f, indent=2)
            print(f"[MAPPINGS] Wrote config.json fallback: {config_path} ({len(config_obj)} entries)")
        except Exception as e:
            print(f"[MAPPINGS] Warning writing config: {e}")


if __name__ == "__main__":
    generate_geyser_mappings()
