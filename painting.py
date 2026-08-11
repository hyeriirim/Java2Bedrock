import os
import glob
import json
import shutil
from PIL import Image

try:
    Resampling_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    Resampling_LANCZOS = Image.LANCZOS

# Standard Bedrock/legacy Java painting atlas coordinates (grid in 16x16 units)
VANILLA_PAINTING_LAYOUT = {
    # 1x1 (16x16)
    "kebab": (0, 0, 1, 1),
    "aztec": (1, 0, 1, 1),
    "alban": (2, 0, 1, 1),
    "aztec2": (3, 0, 1, 1),
    "bomb": (4, 0, 1, 1),
    "plant": (5, 0, 1, 1),
    "wasteland": (6, 0, 1, 1),
    "back": (12, 0, 1, 1),
    # 1x2 (16x32)
    "pool": (0, 2, 1, 2),
    "courbet": (1, 2, 1, 2),
    "sea": (2, 2, 1, 2),
    "sunset": (3, 2, 1, 2),
    "creebet": (4, 2, 1, 2),
    # 2x1 (32x16)
    "wanderer": (0, 4, 2, 1),
    "graham": (2, 4, 2, 1),
    # 2x2 (32x32)
    "match": (0, 8, 2, 2),
    "bust": (2, 8, 2, 2),
    "stage": (4, 8, 2, 2),
    "void": (6, 8, 2, 2),
    "skull_and_roses": (8, 8, 2, 2),
    "wither": (10, 8, 2, 2),
    "earth": (2, 10, 2, 2),
    "wind": (4, 10, 2, 2),
    "fire": (6, 10, 2, 2),
    "water": (8, 10, 2, 2),
    # 4x2 (64x32)
    "fighters": (0, 6, 4, 2),
    # 4x3 (64x48)
    "skeleton": (12, 4, 4, 3),
    "donkey_kong": (12, 7, 4, 3),
    # 4x4 (64x64)
    "pointer": (0, 12, 4, 4),
    "pigscene": (4, 12, 4, 4),
    "burning_skull": (8, 12, 4, 4),
    "unpacked": (12, 12, 4, 4),
}


def convert_paintings():
    out_dir = "staging/target/rp/textures/painting"
    os.makedirs(out_dir, exist_ok=True)

    painting_files = glob.glob("pack/assets/**/textures/painting/**/*.png", recursive=True)
    painting_files += glob.glob("pack/assets/**/textures/paintings/**/*.png", recursive=True)
    painting_files = list(set(painting_files))

    if not painting_files:
        print("[PAINTING] No painting textures found in pack.")
        return

    print(f"[PAINTING] Found {len(painting_files)} painting texture(s).")

    # Determine highest resolution scale (default 16px per grid unit, e.g. 256x256 atlas)
    max_scale = 1
    loaded_paintings = {}

    for pf in painting_files:
        try:
            norm = pf.replace("\\", "/")
            base_name = os.path.splitext(os.path.basename(norm))[0]
            img = Image.open(pf).convert("RGBA")
            loaded_paintings[base_name] = img

            # Copy individual painting texture
            dest_file = os.path.join(out_dir, f"{base_name}.png")
            img.save(dest_file, "PNG")

            # Check scale factor if it is a standard painting
            if base_name in VANILLA_PAINTING_LAYOUT:
                gx, gy, gw, gh = VANILLA_PAINTING_LAYOUT[base_name]
                expected_w = gw * 16
                scale = img.width / expected_w
                if scale > max_scale:
                    max_scale = scale
        except Exception as e:
            print(f"[PAINTING] Error reading painting {pf}: {e}")

    # Build kz.png Bedrock atlas
    unit_size = int(round(16 * max(1.0, max_scale)))
    atlas_dim = unit_size * 16  # 16x16 grid
    atlas = Image.new("RGBA", (atlas_dim, atlas_dim), (0, 0, 0, 0))

    # If an existing kz.png exists in pack, load it as base
    existing_kz = glob.glob("pack/assets/**/kz.png", recursive=True)
    if existing_kz:
        try:
            base_atlas = Image.open(existing_kz[0]).convert("RGBA")
            if base_atlas.size != (atlas_dim, atlas_dim):
                base_atlas = base_atlas.resize((atlas_dim, atlas_dim), Resampling_LANCZOS)
            atlas = base_atlas
        except Exception as e:
            print(f"[PAINTING] Error loading existing kz.png: {e}")

    for name, (gx, gy, gw, gh) in VANILLA_PAINTING_LAYOUT.items():
        if name in loaded_paintings:
            img = loaded_paintings[name]
            target_w = gw * unit_size
            target_h = gh * unit_size
            if img.size != (target_w, target_h):
                p_img = img.resize((target_w, target_h), Resampling_LANCZOS)
            else:
                p_img = img
            pos = (gx * unit_size, gy * unit_size)
            atlas.paste(p_img, pos, p_img if p_img.mode == "RGBA" else None)

    kz_path = os.path.join(out_dir, "kz.png")
    atlas.save(kz_path, "PNG")
    print(f"[PAINTING] Generated Bedrock painting atlas: {kz_path} ({atlas_dim}x{atlas_dim})")

    # Check for painting item overrides (e.g. ItemsAdder / Oraxen painting items)
    painting_item_models = glob.glob("pack/assets/**/models/item/painting.json", recursive=True)
    for pim in painting_item_models:
        try:
            with open(pim, "r", encoding="utf-8") as f:
                data = json.load(f)
            overrides = data.get("overrides", [])
            print(f"[PAINTING] Found painting item overrides in {pim}: {len(overrides)} custom paintings registered.")
        except Exception as e:
            print(f"[PAINTING] Error parsing painting item model {pim}: {e}")


if __name__ == "__main__" or True:
    convert_paintings()
