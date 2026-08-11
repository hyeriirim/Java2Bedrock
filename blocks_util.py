import json
import glob
import os


def get_am_file(model):
    if ":" in model:
        namespace = model.split(":")[0]
        path = model.split(":")[1]
    else:
        namespace = "minecraft"
        path = model

    files = glob.glob(f"staging/target/rp/attachables/{namespace}/{path}*.json")
    if not files:
        files = glob.glob(f"staging/target/rp/attachables/**/{os.path.basename(path)}*.json", recursive=True)

    for fa in files:
        if f"{path.split('/')[-1]}." in fa:
            return fa
    return files[0] if files else None


def write_animated_cube():
    data = {
        "format_version": "1.8.0",
        "animations": {
            "animation.geo_cube.thirdperson_main_hand": {
                "loop": True,
                "bones": {"block": {"rotation": [-20, 145, -10], "position": [0, 14, -6], "scale": [0.375, 0.375, 0.375]}}
            },
            "animation.geo_cube.thirdperson_off_hand": {
                "loop": True,
                "bones": {"block": {"rotation": [20, 40, 20], "position": [0, 13, -6], "scale": [0.375, 0.375, 0.375]}}
            },
            "animation.geo_cube.head": {
                "loop": True,
                "bones": {"block": {"position": [0, 19.9, 0], "scale": 0.625}}
            },
            "animation.geo_cube.firstperson_main_hand": {
                "loop": True,
                "bones": {"block": {"rotation": [140, 45, 15], "position": [-1, 17, 0], "scale": [0.52, 0.52, 0.52]}}
            },
            "animation.geo_cube.firstperson_off_hand": {
                "loop": True,
                "bones": {"block": {"rotation": [-5, 45, -5], "position": [-17.5, 17.5, 15], "scale": [0.52, 0.52, 0.52]}}
            }
        }
    }
    os.makedirs("staging/target/rp/animations", exist_ok=True)
    with open("staging/target/rp/animations/cube.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def write_geometry_cube():
    data = {
        "format_version": "1.19.40",
        "minecraft:geometry": [
            {
                "description": {
                    "identifier": "geometry.cube",
                    "texture_width": 16,
                    "texture_height": 16,
                    "visible_bounds_width": 2,
                    "visible_bounds_height": 2.5,
                    "visible_bounds_offset": [0, 0.75, 0]
                },
                "bones": [
                    {
                        "name": "block",
                        "binding": "c.item_slot == 'head' ? 'head' : q.item_slot_to_bone_name(c.item_slot)",
                        "pivot": [0, 8, 0],
                        "cubes": [
                            {
                                "origin": [-8, 0, -8],
                                "size": [16, 16, 16],
                                "uv": {
                                    "north": {"uv": [0, 0], "uv_size": [16, 16]},
                                    "east": {"uv": [0, 0], "uv_size": [16, 16]},
                                    "south": {"uv": [0, 0], "uv_size": [16, 16]},
                                    "west": {"uv": [0, 0], "uv_size": [16, 16]},
                                    "up": {"uv": [16, 16], "uv_size": [-16, -16]},
                                    "down": {"uv": [16, 16], "uv_size": [-16, -16]}
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }
    os.makedirs("staging/target/rp/models/blocks", exist_ok=True)
    with open("staging/target/rp/models/blocks/cube.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def write_mapping_block(block: str):
    data = {
        "format_version": 1,
        "blocks": {
            f"minecraft:{block}": {
                "name": f"{block}",
                "geometry": "geometry.cube",
                "included_in_creative_inventory": False,
                "only_override_states": True,
                "place_air": True,
                "state_overrides": {}
            }
        }
    }
    os.makedirs("staging/target", exist_ok=True)
    with open(f"staging/target/geyser_block_{block}_mappings.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def regsister_block(block: str, gmdl: str, state: str, texture: str, block_material: str, geometry: str):
    mapping_file = f"staging/target/geyser_block_{block}_mappings.json"
    if not os.path.isfile(mapping_file):
        write_mapping_block(block)

    with open(mapping_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if f"minecraft:{block}" not in data["blocks"]:
        data["blocks"][f"minecraft:{block}"] = {
            "name": f"{block}",
            "geometry": "geometry.cube",
            "included_in_creative_inventory": False,
            "only_override_states": True,
            "place_air": True,
            "state_overrides": {}
        }

    data["blocks"][f"minecraft:{block}"]["state_overrides"][state] = {
        "name": f"block_{gmdl}",
        "display_name": f"block_{gmdl}",
        "geometry": geometry,
        "material_instances": {
            "*": {
                "texture": texture,
                "render_method": block_material or "alpha_test",
                "face_dimming": True,
                "ambient_occlusion": True
            }
        }
    }
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def create_terrain_texture(gmdl: str, texture_file: str):
    terrain_file = "staging/target/rp/textures/terrain_texture.json"
    data = {"resource_pack_name": "geyser_custom", "texture_name": "atlas.terrain", "texture_data": {}}
    if os.path.isfile(terrain_file):
        try:
            with open(terrain_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    if "texture_data" not in data:
        data["texture_data"] = {}

    data["texture_data"][f"block_{gmdl}"] = {"textures": texture_file}
    with open(terrain_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return f"block_{gmdl}"


def get_geometry_block(model: str):
    if ":" in model:
        namespace = model.split(":")[0]
        path = model.split(":")[1]
    else:
        namespace = "minecraft"
        path = model

    files = glob.glob(f"staging/target/rp/models/blocks/{namespace}/{path}.json")
    if not files:
        files = glob.glob(f"staging/target/rp/models/blocks/**/{os.path.basename(path)}.json", recursive=True)

    if files:
        geometry_file = files[0]
        try:
            with open(geometry_file, "r", encoding="utf-8") as f:
                geo_data = f.read()
            if not geo_data.strip():
                os.remove(geometry_file)
                return "geometry.cube"
            data = json.loads(geo_data)
            return data["minecraft:geometry"][0]["description"]["identifier"]
        except Exception:
            return "geometry.cube"

    return "geometry.cube"
