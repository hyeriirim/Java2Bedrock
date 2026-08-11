import os
import json
import glob
import shutil


def find_sound_file_in_pack(sound_ref, default_namespace="minecraft"):
    if ":" in sound_ref:
        parts = sound_ref.split(":", 1)
        namespace = parts[0]
        subpath = parts[1]
    else:
        namespace = default_namespace
        subpath = sound_ref

    if not subpath.endswith(".ogg"):
        subpath_ogg = subpath + ".ogg"
    else:
        subpath_ogg = subpath

    candidates = [
        os.path.join("pack", "assets", namespace, "sounds", subpath_ogg),
        os.path.join("pack", "assets", namespace, subpath_ogg),
        os.path.join("pack", "assets", "minecraft", "sounds", subpath_ogg),
        os.path.join("pack", "assets", "minecraft", subpath_ogg),
    ]

    for c in candidates:
        if os.path.isfile(c):
            return c, namespace, subpath.replace(".ogg", "")

    # Fallback search by basename
    base = os.path.basename(subpath_ogg)
    found = glob.glob(f"pack/assets/**/{base}", recursive=True)
    if found:
        return found[0], namespace, subpath.replace(".ogg", "")

    return None, namespace, subpath.replace(".ogg", "")


def convert_sounds():
    files = glob.glob("pack/assets/**/sounds.json", recursive=True)
    print(f"[SOUND] Found sound definition files: {files}")

    out_dir = "staging/target/rp/sounds"
    os.makedirs(out_dir, exist_ok=True)
    sound_defs_file = os.path.join(out_dir, "sound_definitions.json")

    sound_definitions = {}
    if os.path.isfile(sound_defs_file):
        try:
            with open(sound_defs_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                sound_definitions = existing_data.get("sound_definitions", {})
        except Exception:
            sound_definitions = {}

    copied_sounds = 0

    for sfile in files:
        try:
            norm_path = sfile.replace("\\", "/")
            parts = norm_path.split("/")
            # pack/assets/<namespace>/sounds.json
            namespace = parts[2] if len(parts) >= 4 and parts[1] == "assets" else "minecraft"

            with open(sfile, "r", encoding="utf-8") as f:
                data = json.load(f)

            for sound_key, sound_info in data.items():
                if not isinstance(sound_info, dict):
                    continue

                full_key = f"{namespace}:{sound_key}" if ":" not in sound_key else sound_key
                category = sound_info.get("category", "neutral")
                raw_sounds = sound_info.get("sounds", [])

                bedrock_sounds = []
                for s in raw_sounds:
                    if isinstance(s, dict):
                        s_name = s.get("name", "")
                        src_path, sound_ns, clean_sub = find_sound_file_in_pack(s_name, default_namespace=namespace)
                        bedrock_sound_path = f"sounds/{sound_ns}/{clean_sub}"
                        dest_file = os.path.join("staging/target/rp", f"{bedrock_sound_path}.ogg")
                        if src_path:
                            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                            shutil.copyfile(src_path, dest_file)
                            copied_sounds += 1
                        s_copy = dict(s)
                        s_copy["name"] = bedrock_sound_path
                        bedrock_sounds.append(s_copy)
                    elif isinstance(s, str):
                        src_path, sound_ns, clean_sub = find_sound_file_in_pack(s, default_namespace=namespace)
                        bedrock_sound_path = f"sounds/{sound_ns}/{clean_sub}"
                        dest_file = os.path.join("staging/target/rp", f"{bedrock_sound_path}.ogg")
                        if src_path:
                            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                            shutil.copyfile(src_path, dest_file)
                            copied_sounds += 1
                        bedrock_sounds.append(bedrock_sound_path)

                sound_definitions[full_key] = {
                    "category": category,
                    "sounds": bedrock_sounds
                }

        except Exception as e:
            print(f"[SOUND] Error processing sound definition {sfile}: {e}")

    result_json = {
        "format_version": "1.14.0",
        "sound_definitions": sound_definitions
    }

    with open(sound_defs_file, "w", encoding="utf-8") as f:
        json.dump(result_json, f, indent=2)

    print(f"[SOUND] Sounds conversion complete. Sound definitions written: {len(sound_definitions)}, OGG files copied: {copied_sounds}")


if __name__ == "__main__" or True:
    convert_sounds()
