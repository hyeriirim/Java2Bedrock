"""
font.py - Java to Bedrock font glyph conversion.
Based on the original AZPixel-Team/Java2Bedrock font.py logic:

1. Read font provider JSON files (default.json) from ALL namespaces
   Original: only pack/assets/minecraft/font/default.json
   Extended: pack/assets/*/font/*.json (supports oraxen, nexo, itemsadder, etc.)

2. For each bitmap provider, extract chars, file path, height, ascent

3. For each character:
   - Open the texture file
   - Crop the individual character from the sprite sheet
   - Save to images/<page>/0x<page><hex>.png

4. Process each glyph page:
   - Find max glyph dimensions across all characters in that page
   - Create blank images at (max_size+1, max_size+1)
   - Apply height-based thumbnail scaling (original logic)
   - Paste onto blank with vertical centering for small glyphs
   - Assemble into 16x16 spritesheet via font_sprite.sprite()

Key sizing behavior (from original):
- thumbnail((height, height)) downscales while maintaining aspect ratio
- If glyph is larger than half the blank cell: paste at (0, 0)
- If glyph is smaller: paste at (0, h//2 - hl//2) for vertical centering
"""
from PIL import Image
from font_sprite import sprite
import glob
import os
import json

try:
    RESAMPLING_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING_LANCZOS = Image.LANCZOS

# Hex digits for glyph page addressing
lines = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, "a", "b", "c", "d", "e", "f"]


def resolve_font_texture(file_ref, namespace="minecraft", pack_dir="pack"):
    """Resolve a font texture file reference to an actual file path."""
    if ":" in file_ref:
        parts = file_ref.split(":", 1)
        namespace = parts[0]
        subpath = parts[1]
    else:
        subpath = file_ref

    if not subpath.endswith(".png"):
        subpath += ".png"

    # Try various candidate paths
    candidates = [
        os.path.join(pack_dir, "assets", namespace, "textures", subpath),
        os.path.join(pack_dir, "assets", namespace, "textures", "font", subpath),
        os.path.join(pack_dir, "assets", "minecraft", "textures", subpath),
        os.path.join(pack_dir, "assets", "minecraft", "textures", "font", subpath),
    ]

    for cand in candidates:
        if os.path.isfile(cand):
            return cand

    # Fallback: recursive search
    basename = os.path.basename(subpath)
    found = glob.glob(os.path.join(pack_dir, "assets", "**", basename), recursive=True)
    if found:
        return found[0]

    return None


def process_font_files():
    """Main font conversion entry point."""
    # Find all font JSON files across all namespaces
    # Original: only pack/assets/minecraft/font/default.json
    # Extended: pack/assets/*/font/*.json
    font_files = glob.glob("pack/assets/*/font/*.json")
    if not font_files:
        # Also check without pack/ prefix (for direct extraction)
        font_files = glob.glob("assets/*/font/*.json")
    if not font_files:
        print("[FONT] No font definition files found.")
        return

    print(f"[FONT] Found font files: {font_files}")

    # Collect all providers from all font files
    all_symbols = []  # list of chars arrays
    all_paths = []     # list of file references
    all_heights = []   # list of height values
    all_ascents = []   # list of ascent values
    all_namespaces = []  # namespace for each provider

    for font_path in font_files:
        try:
            # Determine namespace from path
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
                if ptype != "bitmap":
                    continue

                try:
                    chars = prov["chars"]
                    file_ref = prov["file"]
                    height = prov.get("height", 8)
                    ascent = prov.get("ascent", 7)

                    all_symbols.append(chars)
                    all_paths.append(file_ref)
                    all_heights.append(height)
                    all_ascents.append(ascent)
                    all_namespaces.append(namespace)
                except (KeyError, TypeError):
                    continue

        except Exception as e:
            print(f"[FONT] Error reading {font_path}: {e}")

    if not all_symbols:
        print("[FONT] No bitmap font providers found.")
        return

    # Determine which glyph pages are used (original logic)
    glyphs = []
    for chars_list in all_symbols:
        for row_str in chars_list:
            if not isinstance(row_str, str):
                continue
            for ch in row_str:
                try:
                    codepoint = ord(ch)
                    if codepoint == 0:
                        continue
                    hex_full = hex(codepoint)
                    # Pad to at least 4 hex digits: 0xHHLL
                    hex_str = hex_full[2:].zfill(4)
                    page = hex_str[:2].upper()
                    if page not in glyphs:
                        glyphs.append(page)
                except Exception:
                    continue

    glyphs = list(dict.fromkeys(glyphs))  # Deduplicate preserving order
    print(f"[FONT] Glyph pages to process: {glyphs}")

    # Process each glyph page (replicating original converterpack() logic)
    for glyph_page in glyphs:
        try:
            _convert_glyph_page(
                glyph_page,
                all_symbols, all_paths, all_heights, all_ascents, all_namespaces
            )
        except Exception as e:
            print(f"[FONT] Error processing glyph page {glyph_page}: {e}")

    print(f"[FONT] Font conversion complete. Processed {len(glyphs)} glyph pages.")


def _convert_glyph_page(glyph_page, symbols, paths, heights, ascents, namespaces):
    """
    Convert a single glyph page, replicating the original converterpack() logic:
    1. Extract all glyph images for this page from provider textures
    2. Find max dimensions
    3. Create blank background at max size
    4. Apply height thumbnail + vertical centering
    5. Assemble spritesheet
    """
    # Step 1: Extract raw glyph images for this page
    raw_glyphs = {}  # hex_suffix -> PIL Image (raw, not yet processed)
    glyph_heights = {}  # hex_suffix -> height value from provider

    for chars_list, file_ref, height, ascent, namespace in zip(
        symbols, paths, heights, ascents, namespaces
    ):
        num_rows = len(chars_list)
        if num_rows == 0:
            continue

        # For each character in this provider, check if it belongs to this page
        for row_idx, row_str in enumerate(chars_list):
            if not isinstance(row_str, str):
                continue
            num_cols = len(row_str)
            if num_cols == 0:
                continue

            for col_idx, ch in enumerate(row_str):
                codepoint = ord(ch)
                if codepoint == 0 or ch == ' ':
                    continue

                hex_full = hex(codepoint)[2:].zfill(4)
                page = hex_full[:2].upper()

                if page.upper() != glyph_page.upper():
                    continue

                suffix = hex_full[2:]  # Last 2 hex chars

                # Open source texture and crop the character
                tex_path = resolve_font_texture(file_ref, namespace)
                if not tex_path:
                    continue

                try:
                    src_img = Image.open(tex_path).convert("RGBA")
                except Exception:
                    continue

                # Calculate crop box for this character in the sprite sheet
                cell_w = src_img.width / float(num_cols)
                cell_h = src_img.height / float(num_rows)

                box = (
                    int(round(col_idx * cell_w)),
                    int(round(row_idx * cell_h)),
                    int(round((col_idx + 1) * cell_w)),
                    int(round((row_idx + 1) * cell_h)),
                )
                # Clamp to image bounds
                box = (
                    max(0, min(box[0], src_img.width)),
                    max(0, min(box[1], src_img.height)),
                    max(0, min(box[2], src_img.width)),
                    max(0, min(box[3], src_img.height)),
                )
                if box[2] <= box[0] or box[3] <= box[1]:
                    continue

                char_img = src_img.crop(box)

                # Skip fully transparent images
                if not char_img.getbbox():
                    continue

                raw_glyphs[suffix] = char_img
                glyph_heights[suffix] = height

    if not raw_glyphs:
        return

    # Step 2: Find max dimensions across all raw glyphs (original logic)
    max_w = 0
    max_h = 0
    for img in raw_glyphs.values():
        w, h = img.size
        max_w = max(max_w, w)
        max_h = max(max_h, h)

    # Tile size = max(max_w, max_h) + 1, made square (original behavior)
    if max_w == max_h:
        tile_dim = int(max_w + 1)
    elif max_w > max_h:
        tile_dim = int(max_w + 1)
    else:
        tile_dim = int(max_h + 1)

    if tile_dim <= 1:
        return

    tile_size = (tile_dim, tile_dim)

    # Step 3: Process each glyph - apply height thumbnail + centering (original logic)
    processed_glyphs = {}

    for suffix, raw_img in raw_glyphs.items():
        height = glyph_heights.get(suffix, 8)

        # Create a copy for processing
        logo = raw_img.copy()
        wl, hl = logo.size

        # Apply height-based thumbnail (original: thumbnail((height,height), ANTIALIAS))
        # thumbnail() maintains aspect ratio and downscales to fit within the box
        if height >= 1 and height < tile_dim and height < tile_dim:
            thumb_size = (int(height), int(height))
            logo.thumbnail(thumb_size, RESAMPLING_LANCZOS)

        # Get processed dimensions
        wl_proc, hl_proc = logo.size

        # Create blank tile
        blank = Image.new("RGBA", tile_size, (0, 0, 0, 0))

        # Paste with positioning (original logic):
        # If glyph is larger than half the blank cell: paste at (0, 0)
        # Otherwise: paste centered vertically at (0, h//2 - hl//2)
        if wl_proc > (tile_dim / 2) and hl_proc > (tile_dim / 2):
            position = (0, 0)
        else:
            position = (0, (tile_dim // 2) - (hl_proc // 2))

        blank.paste(logo, position, logo if logo.mode == "RGBA" else None)
        processed_glyphs[suffix] = blank

    # Step 4: Fill empty slots with blank images (original create_empty logic)
    for line1 in lines:
        for line2 in lines:
            hex_suffix = f"{line1}{line2}"
            if hex_suffix not in processed_glyphs:
                processed_glyphs[hex_suffix] = Image.new("RGBA", tile_size, (0, 0, 0, 0))

    # Step 5: Assemble spritesheet
    sprite(glyph_page, tile_size, processed_glyphs)


if __name__ == "__main__" or True:
    process_font_files()
