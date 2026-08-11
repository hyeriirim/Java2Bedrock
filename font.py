"""
font.py - Java to Bedrock font glyph conversion.
Scans font definition JSON files across all namespaces (ItemsAdder, Oraxen, Nexo,
Minecraft, custom packs), parses bitmap providers, and converts them to Bedrock
glyph sheets with exact Java font height & aspect-ratio parity for custom ranks,
chat badges, emojis, and icons.
"""
import os
import json
import glob
from PIL import Image
from font_sprite import create_glyph_sheet


def resolve_font_texture(file_ref, default_namespace="minecraft", pack_dir="pack"):
    """Resolve a font texture reference to a local file path."""
    if ":" in file_ref:
        parts = file_ref.split(":", 1)
        namespace = parts[0]
        subpath = parts[1]
    else:
        namespace = default_namespace
        subpath = file_ref

    if not subpath.endswith(".png"):
        subpath += ".png"

    # Candidate paths across pack directory structures
    candidates = [
        os.path.join(pack_dir, "assets", namespace, "textures", subpath),
        os.path.join(pack_dir, "assets", namespace, "textures", "font", subpath),
        os.path.join(pack_dir, "assets", namespace, "font", subpath),
        os.path.join(pack_dir, "assets", namespace, subpath),
        os.path.join(pack_dir, "assets", "minecraft", "textures", subpath),
        os.path.join(pack_dir, "assets", "minecraft", "textures", "font", subpath),
        # Also check without pack/ prefix
        os.path.join("assets", namespace, "textures", subpath),
        os.path.join("assets", namespace, "textures", "font", subpath),
        os.path.join("assets", namespace, "font", subpath),
        os.path.join("assets", namespace, subpath),
    ]

    for cand in candidates:
        if os.path.isfile(cand):
            return cand

    # Fallback: search by basename
    basename = os.path.basename(subpath)
    found = glob.glob(f"pack/assets/**/{basename}", recursive=True)
    if found:
        return found[0]
    found = glob.glob(f"assets/**/{basename}", recursive=True)
    if found:
        return found[0]

    return None


def process_font_files():
    """Main font conversion entry point."""
    search_dirs = [
        "pack/assets/*/font/*.json",
        "pack/assets/*/font/**/*.json",
        "assets/*/font/*.json",
        "assets/*/font/**/*.json",
    ]
    font_files = []
    for sdir in search_dirs:
        font_files.extend(glob.glob(sdir, recursive=True))
    font_files = list(set(font_files))

    if not font_files:
        print("[FONT] No font definition files found.")
        return

    print(f"[FONT] Found {len(font_files)} font definition file(s): {font_files}")

    # Check for optional font config / skip file
    skip_chars = set()
    gui_offsets = {}
    config_paths = ["font_config.json", "pack/font_config.json", "pack/gui_font.json"]
    for cp in config_paths:
        if os.path.isfile(cp):
            try:
                with open(cp, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if isinstance(cfg, dict):
                        for k, v in cfg.items():
                            try:
                                cp_val = int(k, 16) if k.startswith("0x") else ord(k[0])
                                if v.get("skip"):
                                    skip_chars.add(cp_val)
                                if "gui" in v:
                                    gui_offsets[cp_val] = v["gui"]
                            except Exception:
                                pass
            except Exception as e:
                print(f"[FONT] Warning reading {cp}: {e}")

    # pages: page_hex -> { sub_idx: { "img": Image, "height": float, "ascent": float, "gui_offset": [dx, dy] } }
    pages = {}

    for font_path in font_files:
        try:
            norm_path = font_path.replace("\\", "/")
            parts = norm_path.split("/")
            if "assets" in parts:
                ns_idx = parts.index("assets") + 1
                namespace = parts[ns_idx] if ns_idx < len(parts) else "minecraft"
            else:
                namespace = "minecraft"

            with open(font_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            providers = data.get("providers", [])
            if not isinstance(providers, list):
                continue

            for prov in providers:
                if not isinstance(prov, dict):
                    continue
                ptype = prov.get("type", "bitmap")
                if ptype == "space":
                    continue  # Space advances are handled by game engine layout
                if ptype != "bitmap" and "file" not in prov:
                    continue

                file_ref = prov.get("file")
                chars = prov.get("chars", [])

                if not file_ref or not chars or not isinstance(chars, list):
                    continue

                try:
                    prov_height = float(prov.get("height", 8.0))
                except Exception:
                    prov_height = 8.0

                try:
                    prov_ascent = float(prov.get("ascent", 7.0))
                except Exception:
                    prov_ascent = 7.0

                tex_path = resolve_font_texture(file_ref, default_namespace=namespace)
                if not tex_path:
                    print(f"[FONT] Warning: Texture {file_ref} not found for font {font_path}")
                    continue

                try:
                    src_img = Image.open(tex_path).convert("RGBA")
                except Exception as e:
                    print(f"[FONT] Error opening texture {tex_path}: {e}")
                    continue

                num_rows = len(chars)
                if num_rows == 0:
                    continue

                for r, row_str in enumerate(chars):
                    if not isinstance(row_str, str):
                        continue
                    num_cols = len(row_str)
                    if num_cols == 0:
                        continue

                    w_cell = src_img.width / float(num_cols)
                    h_cell = src_img.height / float(num_rows)

                    for c, ch in enumerate(row_str):
                        codepoint = ord(ch)
                        if codepoint == 0 or ch == ' ':
                            continue
                        if codepoint in skip_chars:
                            continue

                        box = (
                            int(round(c * w_cell)),
                            int(round(r * h_cell)),
                            int(round((c + 1) * w_cell)),
                            int(round((r + 1) * h_cell))
                        )
                        # Ensure valid bounds
                        box = (
                            max(0, min(box[0], src_img.width)),
                            max(0, min(box[1], src_img.height)),
                            max(0, min(box[2], src_img.width)),
                            max(0, min(box[3], src_img.height))
                        )
                        if box[2] <= box[0] or box[3] <= box[1]:
                            continue

                        char_crop = src_img.crop(box)

                        # Check if crop has visible pixels
                        if not char_crop.getbbox():
                            continue

                        page_hex = f"{(codepoint >> 8):02X}"
                        sub_idx = codepoint & 0xFF

                        if page_hex not in pages:
                            pages[page_hex] = {}

                        pages[page_hex][sub_idx] = {
                            "img": char_crop,
                            "height": prov_height,
                            "ascent": prov_ascent,
                            "gui_offset": gui_offsets.get(codepoint, [0, 0])
                        }

        except Exception as e:
            print(f"[FONT] Error processing {font_path}: {e}")

    # Generate Bedrock glyph sheets for all pages
    out_dir = "staging/target/rp/font"
    generated_count = 0

    for page_hex, glyph_entries in sorted(pages.items()):
        try:
            res = create_glyph_sheet(page_hex, glyph_entries, output_dir=out_dir)
            if res:
                generated_count += 1
        except Exception as e:
            print(f"[FONT] Error generating glyph sheet for page {page_hex}: {e}")

    print(f"[FONT] Font conversion complete. Total glyph sheets generated: {generated_count}")


if __name__ == "__main__" or True:
    process_font_files()
