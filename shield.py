import os
import json
import glob

shield_models = glob.glob("pack/assets/**/models/item/shield.json", recursive=True)

for shield_file in shield_models:
    try:
        with open(shield_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        overrides = data.get("overrides", [])
        for entry in overrides:
            p = entry.get("predicate", {})
            m = entry.get("model", "")
            if not m or "custom_model_data" not in p:
                continue
            if m in ["item/shield", "minecraft:item/shield", "item/shield_blocking", "minecraft:item/shield_blocking"]:
                continue

            cmd = p["custom_model_data"]
            fpath = f"cache/shield/{cmd}.json"
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            cached_data = {}
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as f_c:
                        cached_data = json.load(f_c)
                except Exception:
                    cached_data = {}

            if p.get("blocking") == 1:
                cached_data["blocking"] = m
            else:
                cached_data["default"] = m

            cached_data["check"] = len([k for k in ["default", "blocking"] if k in cached_data])

            with open(fpath, "w", encoding="utf-8") as f_c:
                json.dump(cached_data, f_c, indent=2)

    except Exception as e:
        print(f"[SHIELD] Error processing shield model {shield_file}: {e}")

shield_cache_files = glob.glob("cache/shield/*.json")
for file in shield_cache_files:
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        default_model = data.get("default")
        blocking_model = data.get("blocking", default_model)

        if not default_model:
            continue

        animation = {}
        saf = None
        adata = None

        for mode in ["default", "blocking"]:
            model_ref = data.get(mode, default_model)
            namespace = model_ref.split(":")[0] if ":" in model_ref else "minecraft"
            path = model_ref.split(":")[-1]
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
            animationitem = desc.get("animations", {})
            gmdl = desc["identifier"]

            if mode == "default":
                saf = fa
                adata = dataA
                animation["mainhand.first_person"] = animationitem.get("firstperson_main_hand", "animation.geyser_custom.disable")
                animation["mainhand.third_person"] = animationitem.get("thirdperson_main_hand", "animation.geyser_custom.disable")
                animation["offhand.first_person"] = animationitem.get("firstperson_off_hand", "animation.geyser_custom.disable")
                animation["offhand.third_person"] = animationitem.get("thirdperson_off_hand", "animation.geyser_custom.disable")

                animate = [
                    {"mainhand.third_person.block": f"!c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && query.is_sneaking"},
                    {"mainhand.first_person.block": f"c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && query.is_sneaking"},
                    {"mainhand.first_person": f"c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && !query.is_sneaking"},
                    {"mainhand.third_person": f"!c.is_first_person && c.item_slot == 'main_hand' && q.is_item_name_any('slot.weapon.mainhand', '{gmdl}') && !query.is_sneaking"},

                    {"offhand.third_person.block": f"!c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && query.is_sneaking"},
                    {"offhand.first_person.block": f"c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && query.is_sneaking"},
                    {"offhand.first_person": f"c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && !query.is_sneaking"},
                    {"offhand.third_person": f"!c.is_first_person && c.item_slot == 'off_hand' && q.is_item_name_any('slot.weapon.offhand', '{gmdl}') && !query.is_sneaking"}
                ]
            else:
                animation["mainhand.first_person.block"] = animationitem.get("firstperson_main_hand", "animation.geyser_custom.disable")
                animation["mainhand.third_person.block"] = animationitem.get("thirdperson_main_hand", "animation.geyser_custom.disable")
                animation["offhand.first_person.block"] = animationitem.get("firstperson_off_hand", "animation.geyser_custom.disable")
                animation["offhand.third_person.block"] = animationitem.get("thirdperson_off_hand", "animation.geyser_custom.disable")
                if os.path.exists(fa) and fa != saf:
                    try:
                        os.remove(fa)
                    except Exception:
                        pass

        if saf and adata:
            with open(saf, "w", encoding="utf-8") as f_out:
                adata["minecraft:attachable"]["description"]["animations"] = animation
                if "scripts" not in adata["minecraft:attachable"]["description"]:
                    adata["minecraft:attachable"]["description"]["scripts"] = {}
                adata["minecraft:attachable"]["description"]["scripts"]["animate"] = animate
                json.dump(adata, f_out, indent=2)

    except Exception as e:
        print(f"[SHIELD] Error processing shield cache {file}: {e}")