import json
import glob
import os
import blocks_util

files = glob.glob("pack/assets/**/blockstates/*.json", recursive=True)
if files:
    blocks_util.write_animated_cube()
    blocks_util.write_geometry_cube()

for file in files:
    try:
        norm_file = file.replace("\\", "/")
        block = os.path.splitext(os.path.basename(norm_file))[0]
        if block == "fire":
            continue

        block_material = os.getenv("BLOCK_MATERIAL", "alpha_test")
        blocks_util.write_mapping_block(block)

        with open(file, "r", encoding="utf-8") as f:
            bdata = json.load(f)

        variants = bdata.get("variants", {})
        if not isinstance(variants, dict):
            continue

        for k, v in variants.items():
            if isinstance(v, list) and v:
                v = v[0]
            if not isinstance(v, dict) or "model" not in v:
                continue

            model_ref = v["model"]
            if "block/original" in model_ref or "block/tripwire_attached_n" in model_ref:
                continue

            am = blocks_util.get_am_file(model_ref)
            if am is None or not os.path.isfile(am):
                continue

            with open(am, "r", encoding="utf-8") as f_am:
                data_am = json.load(f_am)

            desc = data_am["minecraft:attachable"]["description"]
            gmdl = desc["identifier"].split(":")[-1]
            geometry = blocks_util.get_geometry_block(model_ref)
            texture = blocks_util.create_terrain_texture(gmdl, desc["textures"]["default"])

            if geometry == "geometry.cube":
                desc["geometry"]["default"] = "geometry.cube"
                desc["animations"] = {
                    "thirdperson_main_hand": "animation.geo_cube.thirdperson_main_hand",
                    "thirdperson_off_hand": "animation.geo_cube.thirdperson_off_hand",
                    "thirdperson_head": "animation.geo_cube.head",
                    "firstperson_main_hand": "animation.geo_cube.firstperson_main_hand",
                    "firstperson_off_hand": "animation.geo_cube.firstperson_off_hand",
                    "firstperson_head": "animation.geyser_custom.disable"
                }
                with open(am, "w", encoding="utf-8") as f_am:
                    json.dump(data_am, f_am, indent=2)

            if block == "tripwire":
                sstate = k.split(",")
                if len(sstate) >= 7:
                    k = f"{sstate[0]},{sstate[4]},{sstate[1]},{sstate[2]},{sstate[6]},{sstate[3]},{sstate[5]}"

            blocks_util.regsister_block(block, gmdl, k, texture, block_material, geometry)

    except Exception as e:
        print(f"[BLOCK] Error processing blockstate {file}: {e}")
