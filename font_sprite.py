"""
font_sprite.py - Bedrock glyph sheet assembler.
Faithfully implements the original AZPixel Java2Bedrock spritesheet generation:
1. Calculates tile_size = max(max_w, max_h) + 1 for each page based on actual glyph dimensions.
2. Places unscaled original glyphs into (tile_size, tile_size) cells (flush-left, centered vertically).
3. Assembles the 16x16 grid sheet at (tile_size * 16, tile_size * 16) in-memory.
"""
from PIL import Image
import os


def create_glyph_sheet(glyph_page, glyph_entries, output_dir="staging/target/rp/font"):
    """
    Creates a Bedrock glyph sheet (16x16 grid) for a given unicode page,
    matching the exact original AZPixel Java2Bedrock sizing and layout.

    glyph_page: 2-character hex string (e.g. 'E0', 'E2', '00', '1F')
    glyph_entries: dict mapping sub_index (0..255) -> PIL Image object (or dict with "img")
    output_dir: directory where glyph_XX.png will be saved
    """
    if not glyph_entries:
        return None

    # Extract raw images
    images = {}
    for sub_idx, entry in glyph_entries.items():
        if not (0 <= sub_idx <= 255):
            continue
        if isinstance(entry, dict):
            img = entry.get("img")
        else:
            img = entry
        if img is not None and img.size[0] > 0 and img.size[1] > 0:
            images[sub_idx] = img

    if not images:
        return None

    # Calculate tile size from actual glyph dimensions (exact original logic: max(maxsw, maxsh) + 1)
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

        # Create isolated blank cell (exact original logic)
        cell = Image.new("RGBA", tile_size, (0, 0, 0, 0))

        # Position within cell (exact original logic):
        # If glyph is larger than half the cell in both dimensions: top-left (0, 0)
        # Otherwise: flush-left, centered vertically at (0, (h // 2) - (hl // 2))
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
