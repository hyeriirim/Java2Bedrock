import os
import json
import shutil
import glob
from jproperties import Properties

ARMOR_SLOTS = {
    "helmet": {"layer": 1, "geo": "geometry.player.armor.helmet", "types": ["helmet", "cap"]},
    "chestplate": {"layer": 1, "geo": "geometry.player.armor.chestplate", "types": ["chestplate", "tunic"]},
    "leggings": {"layer": 2, "geo": "geometry.player.armor.leggings", "types": ["leggings", "pants"]},
    "boots": {"layer": 1, "geo": "geometry.player.armor.boots", "types": ["boots"]}
}

ALL_ARMOR_ITEMS = [
    "leather_helmet", "leather_chestplate", "leather_leggings", "leather_boots",
    "diamond_helmet", "diamond_chestplate", "diamond_leggings", "diamond_boots",
    "iron_helmet", "iron_chestplate", "iron_leggings", "iron_boots",
    "golden_helmet", "golden_chestplate", "golden_leggings", "golden_boots",
    "chainmail_helmet", "chainmail_chestplate", "chainmail_leggings", "chainmail_boots",
    "netherite_helmet", "netherite_chestplate", "netherite_leggings", "netherite_boots",
    "turtle_helmet"
]


def write_armor_attachable(file_path, gmdl, layer_texture, slot_type):
    geo = ARMOR_SLOTS.get(slot_type, {}).get("geo", f"geometry.player.armor.{slot_type}")
    ajson = {
        "format_version": "1.10.0",
        "minecraft:attachable": {
            "description": {
                "identifier": f"geyser_custom:{gmdl}.player",
                "item": {f"geyser_custom:{gmdl}": "query.owner_identifier == 'minecraft:player'"},
                "materials": {
                    "default": "armor_leather",
                    "enchanted": "armor_leather_enchanted"
                },
                "textures": {
                    "default": f"textures/armor_layer/{layer_texture}",
                    "enchanted": "textures/misc/enchanted_item_glint"
                },
                "geometry": {
                    "default": geo
                },
                "scripts": {
                    "parent_setup": "variable.helmet_layer_visible = 0.0;"
                },
                "render_controllers": ["controller.render.armor"]
            }
        }
    }
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(ajson, f, indent=2)


def find_texture_in_pack(texture_name):
    clean = texture_name.replace("\\", "/").replace(".png", "")
    base = os.path.basename(clean)

    candidates = [
        f"pack/assets/minecraft/optifine/cit/ia_generated_armors/{base}.png",
        f"pack/assets/minecraft/optifine/cit/armor/{base}.png",
        f"pack/assets/minecraft/optifine/cit/{base}.png",
        f"pack/assets/oraxen/textures/models/armor/{base}.png",
        f"pack/assets/minecraft/textures/models/armor/{base}.png",
        f"pack/assets/{clean}.png"
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    # Recursive search
    found = glob.glob(f"pack/assets/**/{base}.png", recursive=True)
    if found:
        return found[0]
    return None


def get_slot_from_name(name):
    name_lower = name.lower()
    if "helmet" in name_lower or "cap" in name_lower or "head" in name_lower:
        return "helmet"
    if "chestplate" in name_lower or "tunic" in name_lower or "chest" in name_lower:
        return "chestplate"
    if "leggings" in name_lower or "pants" in name_lower or "legs" in name_lower:
        return "leggings"
    if "boots" in name_lower or "feet" in name_lower:
        return "boots"
    return "helmet"


def convert_armors():
    target_armor_dir = "staging/target/rp/textures/armor_layer"
    os.makedirs(target_armor_dir, exist_ok=True)

    # 1. Search for all Optifine / CIT properties files in pack
    prop_files = glob.glob("pack/assets/**/cit/**/*.properties", recursive=True)
    prop_files += glob.glob("pack/assets/**/optifine/**/*.properties", recursive=True)
    prop_files = list(set(prop_files))

    properties_by_item = {}  # (item, cmd) or item_name -> (layer_1, layer_2)

    for pf in prop_files:
        try:
            prop = Properties()
            with open(pf, "rb") as f:
                prop.load(f)

            ptype = prop.get("type", None)
            ptype_str = ptype.data if ptype else ""
            if ptype_str and ptype_str != "armor":
                continue

            items_prop = prop.get("items", None) or prop.get("matchItems", None)
            items_list = items_prop.data.split() if items_prop else []

            # Layer textures
            layer1 = None
            layer2 = None
            for k in prop.keys():
                k_str = str(k)
                if "layer_1" in k_str or "layer1" in k_str:
                    layer1 = prop.get(k).data.replace(".png", "")
                elif "layer_2" in k_str or "layer2" in k_str:
                    layer2 = prop.get(k).data.replace(".png", "")

            # If not explicitly named layer_1/layer_2, check texture property
            if not layer1 and prop.get("texture"):
                layer1 = prop.get("texture").data.replace(".png", "")

            cmd_prop = prop.get("nbt.CustomModelData", None)
            cmd_val = int(cmd_prop.data) if cmd_prop else None

            base_prop_name = os.path.splitext(os.path.basename(pf))[0]

            for item_name in items_list:
                item_clean = item_name.replace("minecraft:", "")
                properties_by_item[(item_clean, cmd_val)] = (layer1 or base_prop_name, layer2 or base_prop_name)
                properties_by_item[base_prop_name] = (layer1 or base_prop_name, layer2 or base_prop_name)

        except Exception as e:
            print(f"[ARMOR] Warning reading properties {pf}: {e}")

    # 2. Iterate through all armor item model files
    armor_model_files = []
    for item in ALL_ARMOR_ITEMS:
        found_models = glob.glob(f"pack/assets/**/models/item/{item}.json", recursive=True)
        armor_model_files.extend(found_models)

    processed_count = 0

    for amf in armor_model_files:
        try:
            item_type = os.path.splitext(os.path.basename(amf))[0]
            slot_type = get_slot_from_name(item_type)

            with open(amf, "r", encoding="utf-8") as f:
                data = json.load(f)

            overrides = data.get("overrides", [])
            for override in overrides:
                pred = override.get("predicate", {})
                cmd = pred.get("custom_model_data", None)
                model_ref = override.get("model", "")
                if not model_ref or model_ref in ALL_ARMOR_ITEMS or model_ref.endswith(f"/{item_type}"):
                    continue

                namespace = model_ref.split(":")[0] if ":" in model_ref else "minecraft"
                model_path = model_ref.split(":")[-1]
                model_name = os.path.basename(model_path)

                # Look up layer texture
                layer_tuple = properties_by_item.get((item_type, cmd))
                if not layer_tuple:
                    layer_tuple = properties_by_item.get(f"{namespace}_{model_name}")
                if not layer_tuple:
                    layer_tuple = properties_by_item.get(model_name)

                if layer_tuple:
                    l1, l2 = layer_tuple
                    layer_name = l2 if slot_type == "leggings" else l1
                else:
                    # Default heuristic from model name
                    layer_suffix = "_layer_2" if slot_type == "leggings" else "_layer_1"
                    layer_name = f"{model_name}{layer_suffix}"

                # Find and copy armor texture
                tex_src = find_texture_in_pack(layer_name)
                if tex_src:
                    dest_tex = os.path.join(target_armor_dir, f"{os.path.basename(layer_name)}.png")
                    shutil.copyfile(tex_src, dest_tex)
                    layer_file_basename = os.path.splitext(os.path.basename(layer_name))[0]
                else:
                    layer_file_basename = os.path.splitext(os.path.basename(layer_name))[0]

                # Find generated attachable file
                attachable_matches = glob.glob(f"staging/target/rp/attachables/{namespace}/{model_path}*.json")
                if not attachable_matches:
                    attachable_matches = glob.glob(f"staging/target/rp/attachables/**/{model_name}*.json", recursive=True)

                for af in attachable_matches:
                    if af.endswith(".player.json"):
                        continue
                    try:
                        with open(af, "r", encoding="utf-8") as f_att:
                            att_data = json.load(f_att)
                        desc = att_data["minecraft:attachable"]["description"]
                        gmdl = desc["identifier"].split(":")[-1]

                        player_attachable_file = af.replace(".attachable.json", ".player.json")
                        if player_attachable_file == af:
                            player_attachable_file = af.replace(".json", ".player.json")

                        write_armor_attachable(player_attachable_file, gmdl, layer_file_basename, slot_type)
                        processed_count += 1
                        break
                    except Exception as e:
                        print(f"[ARMOR] Error generating player attachable for {af}: {e}")

        except Exception as e:
            print(f"[ARMOR] Error processing armor model {amf}: {e}")

    print(f"[ARMOR] Armor conversion complete. Total player armor attachables written: {processed_count}")


if __name__ == "__main__" or True:
    convert_armors()
