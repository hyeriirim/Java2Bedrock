"""
font_sprite.py - Bedrock glyph sheet assembler.
Implements HD supersampled Bedrock font sheet generation:
1. Normalizes all glyph dimensions to match standard player rank proportions.
2. Uses high-resolution supersampling (HD cell resolution) to eliminate all blurriness.
3. Places glyphs into (tile_size, tile_size) cells (flush-left, centered vertically).
4. Assembles the 16x16 grid sheet at (tile_size * 16, tile_size * 16) in-memory.
"""
from PIL import Image
import os

try:
    RESAMPLING_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLING_NEAREST = Image.Resampling.NEAREST
except AttributeError:
    RESAMPLING_LANCZOS = Image.LANCZOS
    RESAMPLING_NEAREST = Image.NEAREST


def create_glyph_sheet(glyph_page, glyph_entries, output_dir="staging/target/rp/font"):
    """
    Creates an HD crisp Bedrock glyph sheet (16x16 grid) for a given unicode page,
    matching the exact player rank size while preserving ultra-sharp HD clarity.

    glyph_page: 2-character hex string (e.g. 'E0', 'E2', '00', '1F')
    glyph_entries: dict mapping sub_index (0..255) -> dict with "img", "height" or PIL Image
    output_dir: directory where glyph_XX.png will be saved
    """
    if not glyph_entries:
        return None

    # Step 1: Collect valid images and determine normalized game dimensions
    valid_entries = {}
    for sub_idx, entry in glyph_entries.items():
        if not (0 <= sub_idx <= 255):
            continue

        if isinstance(entry, dict):
            img = entry.get("img")
            target_h = float(entry.get("height", 8.0))
        else:
            img = entry
            target_h = 8.0

        if img is None or img.size[0] <= 0 or img.size[1] <= 0:
            continue

        cw, ch = img.size
        # Normalized game dimensions (where standard text line height = 8.0)
        h_game = max(1.0, target_h)
        w_game = max(1.0, float(cw) * (h_game / float(ch)))

        valid_entries[sub_idx] = {
            "img": img,
            "h_game": h_game,
            "w_game": w_game,
        }

    if not valid_entries:
        return None

    # Step 2: Calculate base layout dimensions across all glyphs in this page
    max_w_game = max(e["w_game"] for e in valid_entries.values())
    max_h_game = max(e["h_game"] for e in valid_entries.values())
    base_dim = max(16.0, max_w_game, max_h_game) + 1.0

    # Step 3: Supersample for crystal-clear HD resolution (no blur)
    # Target tile_dim around 256px per cell (or at least 4x supersampling)
    supersample_factor = max(4.0, 256.0 / base_dim)
    tile_dim = int(round(base_dim * supersample_factor))
    tile_size = (tile_dim, tile_dim)

    # 16x16 grid dimensions
    sheet_w = tile_dim * 16
    sheet_h = tile_dim * 16
    spritesheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))

    # Step 4: Render each glyph into its cell with high-resolution scaling
    for sub_idx, entry in valid_entries.items():
        row = sub_idx // 16
        col = sub_idx % 16

        img = entry["img"]
        h_game = entry["h_game"]
        w_game = entry["w_game"]

        # Calculate exact pixel dimensions inside the HD cell
        target_w = max(1, min(tile_dim, int(round(w_game * supersample_factor))))
        target_h = max(1, min(tile_dim, int(round(h_game * supersample_factor))))

        # High quality resampling from original source image
        cw, ch = img.size
        if cw == target_w and ch == target_h:
            img_hd = img
        else:
            resample_filter = RESAMPLING_NEAREST if (cw % target_w == 0 and ch % target_h == 0) else RESAMPLING_LANCZOS
            img_hd = img.resize((target_w, target_h), resample_filter)

        # Create isolated blank cell
        cell = Image.new("RGBA", tile_size, (0, 0, 0, 0))

        # Position within cell: flush-left (X=0), centered vertically
        offset_x = 0
        offset_y = (tile_dim - target_h) // 2

        cell.paste(img_hd, (offset_x, offset_y), img_hd if img_hd.mode == "RGBA" else None)

        # Paste cell into sheet at grid position
        pos_x = col * tile_dim
        pos_y = row * tile_dim
        spritesheet.paste(cell, (pos_x, pos_y), cell)

    # Step 5: Save output
    out_dirs = [output_dir, "target/rp/font"] if output_dir != "target/rp/font" else [output_dir]
    out_file = None
    for od in out_dirs:
        try:
            os.makedirs(od, exist_ok=True)
            target_path = os.path.join(od, f"glyph_{glyph_page.upper()}.png")
            spritesheet.save(target_path, "PNG")
            out_file = target_path
        except Exception as e:
            print(f"[FONT] Warning saving to {od}: {e}")

    print(f"[FONT] Saved HD crisp Bedrock font sheet: glyph_{glyph_page.upper()}.png ({sheet_w}x{sheet_h}, tile={tile_dim}x{tile_dim}, {len(valid_entries)} glyphs)")
    return out_file
