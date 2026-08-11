import os
import json
import glob
import hashlib


def get_md5_7(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:7]


def generate_geyser_mappings():
    print("[MAPPINGS] Starting Geyser mappings generation...")

    # Search for all model item JSON files across all namespaces
    search_dirs = [
        "pack/assets/**/models/item/*.json",
        "pack/assets/**/models/items/*.json",
        "assets/**/models/item/*.json",
        "assets/**/models/items/*.json",
        "staging/assets/**/models/item/*.json",
    ]
    model_files = []
    for sdir in search_dirs:
        model_files.extend(glob.glob(sdir, recursive=True))
    model_files = list(set(model_files))

    print(f"[MAPPINGS] Found {len(model_files)} item model file(s) to inspect.")

    # Load sprites.json if present
    sprites_map = {}
    sprite_paths = ["sprites.json", "pack/sprites.json", "staging/sprites.json"]
    for sp in sprite_paths:
        if os.path.isfile(sp):
            try:
                with open(sp, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
                if isinstance(sdata, dict):
                    for item_k, sprite_entries in sdata.items():
                        clean_item = item_k.replace("minecraft:", "")
                        if isinstance(sprite_entries, list):
                            for se in sprite_entries:
                                cmd = se.get("custom_model_data")
                                dmg = se.get("damage_predicate")
                                unb = se.get("unbreakable", False)
                                sprite_tex = se.get("sprite")
                                pkey = f"{clean_item}_c{cmd}_d{dmg}_u{unb}"
                                sprites_map[pkey] = sprite_tex
            except Exception as e:
                print(f"[MAPPINGS] Warning reading {sp}: {e}")

    items_map = {}
    config_entries = {}
    total_custom_items = 0

    for mfile in model_files:
        try:
            norm_path = mfile.replace("\\", "/")
            base_filename = os.path.splitext(os.path.basename(norm_path))[0]
            item_name = base_filename

            with open(mfile, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                continue

            overrides = data.get("overrides", [])
            if not isinstance(overrides, list):
                continue

            for idx, override in enumerate(overrides):
                if not isinstance(override, dict):
                    continue

                predicate = override.get("predicate", {})
                model_ref = override.get("model", "")
                if not model_ref:
                    continue

                cmd = predicate.get("custom_model_data")
                dmg = predicate.get("damage")
                damaged = predicate.get("damaged")

                # If no custom predicate is set, skip default model
                if cmd is None and dmg is None and damaged is None:
                    continue

                unbreakable = True if damaged == 0 else None
                damage_val = int(dmg) if dmg is not None else None
                cmd_val = int(cmd) if cmd is not None else None

                # Build predicate hash key
                pred_str = f"{item_name}_c{cmd_val}_d{damage_val}_u{unbreakable}"
                entry_hash = get_md5_7(pred_str)
                path_hash = f"gmdl_{entry_hash}"

                # Determine icon
                custom_sprite = sprites_map.get(pred_str)
                if custom_sprite:
                    icon_name = custom_sprite
                else:
                    icon_name = path_hash

                mapping_entry = {
                    "name": path_hash,
                    "allow_offhand": True,
                    "icon": icon_name
                }
                if cmd_val is not None:
                    mapping_entry["custom_model_data"] = cmd_val
                if damage_val is not None:
                    mapping_entry["damage_predicate"] = damage_val
                if unbreakable is not None:
                    mapping_entry["unbreakable"] = unbreakable

                full_item_key = f"minecraft:{item_name}"
                if full_item_key not in items_map:
                    items_map[full_item_key] = []

                # Avoid duplicates
                if not any(e["name"] == path_hash for e in items_map[full_item_key]):
                    items_map[full_item_key].append(mapping_entry)
                    total_custom_items += 1

                # Record config entry for 3D/2D models
                namespace = model_ref.split(":")[0] if ":" in model_ref else "minecraft"
                model_subpath = model_ref.split(":")[-1]
                config_entries[path_hash] = {
                    "item": item_name,
                    "geyserID": path_hash,
                    "path_hash": path_hash,
                    "geometry": f"geo_{entry_hash}",
                    "namespace": namespace,
                    "model_path": os.path.dirname(model_subpath),
                    "model_name": os.path.basename(model_subpath),
                    "nbt": {
                        "CustomModelData": cmd_val,
                        "Damage": damage_val,
                        "Unbreakable": unbreakable
                    }
                }

        except Exception as e:
            print(f"[MAPPINGS] Error parsing model file {mfile}: {e}")

    result = {
        "format_version": "1",
        "items": items_map
    }

    # Write to target directories
    out_paths = [
        "staging/target/geyser_mappings.json",
        "target/geyser_mappings.json",
        "staging/target/unpackaged/geyser_mappings.json"
    ]
    for outp in out_paths:
        try:
            os.makedirs(os.path.dirname(outp), exist_ok=True)
            with open(outp, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"[MAPPINGS] Successfully wrote mappings to {outp} ({len(items_map)} items, {total_custom_items} custom predicates)")
        except Exception as e:
            print(f"[MAPPINGS] Warning writing to {outp}: {e}")

    # Write config.json fallback if needed
    for cfg_path in ["staging/config.json", "config.json"]:
        if not os.path.isfile(cfg_path) or os.path.getsize(cfg_path) < 10:
            try:
                os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(config_entries, f, indent=2)
            except Exception:
                pass


if __name__ == "__main__" or True:
    generate_geyser_mappings()
