"""
font_sprite.py - Bedrock glyph sheet assembler.
Implements the exact sizing and layout for Bedrock font sheets:
1. Normalizes glyph heights to the Java font height (default 8px, matching standard player ranks).
2. Calculates tile_size = max(16, max_w, max_h) + 1 for each page.
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
    Creates a Bedrock glyph sheet (16x16 grid) for a given unicode page,
    matching the exact player rank size and proportions.

    glyph_page: 2-character hex string (e.g. 'E0', 'E2', '00', '1F')
    glyph_entries: dict mapping sub_index (0..255) -> dict with "img", "height", "ascent" or PIL Image
    output_dir: directory where glyph_XX.png will be saved
    """
    if not glyph_entries:
        return None

    # Process and normalize all glyphs
    images = {}
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

        # If image height exceeds target font height (e.g. 16px/24px HD rank badges),
        # scale down proportionally so height matches standard player rank height (8px)
        if ch > target_h and target_h >= 1.0:
            scale = target_h / float(ch)
            new_w = max(1, int(round(cw * scale)))
            new_h = max(1, int(round(ch * scale)))
            resample_filter = RESAMPLING_NEAREST if (cw % new_w == 0 and ch % new_h == 0) else RESAMPLING_LANCZOS
            img_processed = img.resize((new_w, new_h), resample_filter)
        else:
            img_processed = img

        images[sub_idx] = img_processed

    if not images:
        return None

    # Calculate tile size from normalized glyph dimensions
    max_w = max(img.size[0] for img in images.values())
    max_h = max(img.size[1] for img in images.values())
    tile_dim = max(16, max(max_w, max_h) + 1)
    tile_size = (tile_dim, tile_dim)

    # 16x16 grid dimensions
    sheet_w = tile_dim * 16
    sheet_h = tile_dim * 16
    spritesheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))

    for sub_idx, logo in images.items():
        row = sub_idx // 16
        col = sub_idx % 16

        wl, hl = logo.size

        # Create isolated blank cell
        cell = Image.new("RGBA", tile_size, (0, 0, 0, 0))

        # Position within cell:
        # If glyph is larger than half the cell in both dimensions: top-left (0, 0)
        # Otherwise: flush-left (X=0), centered vertically at (0, (tile_dim - hl) // 2)
        if wl > (tile_dim // 2) and hl > (tile_dim // 2):
            position = (0, 0)
        else:
            position = (0, (tile_dim // 2) - (hl // 2))

        cell.paste(logo, position, logo if logo.mode == "RGBA" else None)

        # Paste cell into sheet at grid position
        pos_x = col * tile_dim
        pos_y = row * tile_dim
        spritesheet.paste(cell, (pos_x, pos_y), cell)

    # Save output
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

    print(f"[FONT] Saved Bedrock font sheet: glyph_{glyph_page.upper()}.png ({sheet_w}x{sheet_h}, tile={tile_dim}x{tile_dim}, {len(images)} glyphs)")
    return out_file
