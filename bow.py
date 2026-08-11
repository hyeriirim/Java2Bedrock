import os
import json
import glob
from bow_util import Bow_Util

bow_models = glob.glob("pack/assets/**/models/item/bow.json", recursive=True)
bow_models += glob.glob("pack/assets/**/models/item/crossbow.json", recursive=True)
bow_models = list(set(bow_models))

for bow_file in bow_models:
    try:
        with open(bow_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        overrides = data.get("overrides", [])
        for entry in overrides:
            p = entry.get("predicate", {})
            m = entry.get("model", "")
            if not m or "custom_model_data" not in p:
                continue
            if m in ["item/bow", "item/bow_pulling_0", "item/bow_pulling_1", "item/bow_pulling_2",
                     "minecraft:item/bow", "minecraft:item/bow_pulling_0", "minecraft:item/bow_pulling_1", "minecraft:item/bow_pulling_2",
                     "item/crossbow", "item/crossbow_pulling_0", "item/crossbow_pulling_1", "item/crossbow_pulling_2",
                     "minecraft:item/crossbow", "minecraft:item/crossbow_pulling_0", "minecraft:item/crossbow_pulling_1", "minecraft:item/crossbow_pulling_2"]:
                continue

            cmd = p["custom_model_data"]
            stage = 0
            if p.get("pulling") == 1 or p.get("charged") == 1:
                pull = float(p.get("pull", 0.0))
                if pull >= 0.9:
                    stage = 3
                elif pull >= 0.65:
                    stage = 2
                else:
                    stage = 1

            fpath = f"cache/bow/{cmd}.json"
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            cached_data = {}
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as f_c:
                        cached_data = json.load(f_c)
                except Exception:
                    cached_data = {}

            cached_data[f"texture_{stage}"] = m
            cached_data["check"] = len([k for k in cached_data if k.startswith("texture_")])

            with open(fpath, "w", encoding="utf-8") as f_c:
                json.dump(cached_data, f_c, indent=2)

    except Exception as e:
        print(f"[BOW] Error processing bow model {bow_file}: {e}")

files = glob.glob("cache/bow/*.json")
if files:
    Bow_Util.animation()
    Bow_Util.rendercontrollers()

gmdllist = []
for file in files:
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Fallback missing stages to texture_0 if needed
        base_tex = data.get("texture_0")
        if not base_tex:
            continue

        for st in range(4):
            if f"texture_{st}" not in data:
                data[f"texture_{st}"] = base_tex

        textures = []
        geometry = []
        mfile = None
        mdefault = "entity_alphatest_one_sided"
        menchanted = "entity_alphatest_one_sided"
        gmdl = None
        animations = {}
        animate = []
        pre_animation = []
        is2Dbow = False

        for i in range(4):
            tex_entry = data[f"texture_{i}"]
            namespace = tex_entry.split(":")[0] if ":" in tex_entry else "minecraft"
            path = tex_entry.split(":")[-1]
            model_name = os.path.basename(path)

            fa_matches = glob.glob(f"staging/target/rp/attachables/{namespace}/{path}*.json")
            if not fa_matches:
                fa_matches = glob.glob(f"staging/target/rp/attachables/**/{model_name}*.json", recursive=True)

            fa = fa_matches[0] if fa_matches else None
            if not fa:
                continue

            with open(fa, "r", encoding="utf-8") as f_a:
                dataA = json.load(f_a)

            desc = dataA["minecraft:attachable"]["description"]
            textures.append(desc["textures"]["default"])

            geo_matches = glob.glob(f"staging/target/rp/models/blocks/{namespace}/{path}.json")
            if not geo_matches:
                geo_matches = glob.glob(f"staging/target/rp/models/blocks/**/{model_name}.json", recursive=True)

            is2Dbow = Bow_Util.is2Dbow(geo_matches[0]) if geo_matches else False

            if is2Dbow:
                if i == 0:
                    geometry.append("geometry.bow_standby")
                else:
                    geometry.append(f"geometry.bow_pulling_{i-1}")
            else:
                geometry.append(desc["geometry"]["default"])

            if i == 0:
                if is2Dbow:
                    animate = [
                        {"wield": "c.is_first_person"},
                        {"third_person": "!c.is_first_person"},
                        {"wield_first_person_pull": "query.main_hand_item_use_duration > 0.0f && c.is_first_person"}
                    ]
                    pre_animation = [
                        "v.charge_amount = math.clamp((q.main_hand_item_max_duration - (q.main_hand_item_use_duration - q.frame_alpha + 1.0)) / 10.0, 0.0, 1.0f);",
                        "v.total_frames = 3;",
                        "v.step = v.total_frames / 60;",
                        "v.frame = query.is_using_item ? math.clamp((v.frame ?? 0) + v.step, 1, v.total_frames) : 0;"
                    ]
                else:
                    animate = [
                        {"thirdperson_main_hand": "v.main_hand && !c.is_first_person"},
                        {"thirdperson_off_hand": "v.off_hand && !c.is_first_person"},
                        {"thirdperson_head": "v.head && !c.is_first_person"},
                        {"firstperson_main_hand": "v.main_hand && c.is_first_person"},
                        {"firstperson_off_hand": "v.off_hand && c.is_first_person"},
                        {"firstperson_head": "c.is_first_person && v.head"}
                    ]
                    pre_animation = [
                        "v.charge_amount = math.clamp((q.main_hand_item_max_duration - (q.main_hand_item_use_duration - q.frame_alpha + 1.0)) / 10.0, 0.0, 1.0f);",
                        "v.total_frames = 3;",
                        "v.step = v.total_frames / 60;",
                        "v.frame = query.is_using_item ? math.clamp((v.frame ?? 0) + v.step, 1, v.total_frames) : 0;",
                        "v.main_hand = c.item_slot == 'main_hand';",
                        "v.off_hand = c.item_slot == 'off_hand';",
                        "v.head = c.item_slot == 'head';"
                    ]
                mfile = fa
                mdefault = desc["materials"]["default"]
                menchanted = desc["materials"]["enchanted"]
                gmdl = desc["identifier"].split(":")[-1]
                animations = desc.get("animations", {})
                animations["wield"] = "animation.player.bow_custom.first_person"
                animations["third_person"] = "animation.player.bow_custom"
                animations["wield_first_person_pull"] = "animation.bow.wield_first_person_pull"
                gmdllist.append(f"geyser_custom:{gmdl}")
                Bow_Util.item_texture(gmdl, textures[0])
            else:
                if os.path.exists(fa) and fa != mfile:
                    try:
                        os.remove(fa)
                    except Exception:
                        pass

        if mfile and gmdl and len(textures) == 4 and len(geometry) == 4:
            Bow_Util.write(mfile, gmdl, textures, geometry, mdefault, menchanted, animations, animate, pre_animation)

    except Exception as e:
        print(f"[BOW] Error processing bow cache {file}: {e}")

if gmdllist:
    Bow_Util.acontroller(gmdllist)
