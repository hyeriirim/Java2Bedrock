"""
font_sprite.py - Bedrock glyph sheet assembler.
Renders HD Bedrock font glyph sheets (16x16 character grid, 4096x4096) where
each character is strictly contained within its own 256x256 cell tile, preventing
any overlapping or bleeding into adjacent character slots.
"""
from PIL import Image
import os

try:
    RESAMPLING_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLING_NEAREST = Image.Resampling.NEAREST
except AttributeError:
    RESAMPLING_LANCZOS = Image.LANCZOS
    RESAMPLING_NEAREST = Image.NEAREST


def create_glyph_sheet(glyph_page, glyph_entries, output_dir="staging/target/rp/font", tile_size=256):
    """
    Creates an HD Bedrock font glyph sheet (16x16 grid of character cells) for a given unicode page.

    glyph_page: 2-character hex string (e.g. 'E0', 'E2', '00', '1F')
    glyph_entries: dict mapping sub_index (0..255) -> dict containing:
        - "img": PIL Image object of the character crop
        - "height": Java height property (optional)
        - "ascent": Java ascent property (optional)
        - "gui_offset": [dx, dy] optional GUI offset
    output_dir: directory where glyph_XX.png will be saved
    tile_size: pixel size per cell (default 256 for crisp 4096x4096 HD sheets)
    """
    if not glyph_entries:
        return None

    sheet_dim = tile_size * 16
    sheet = Image.new("RGBA", (sheet_dim, sheet_dim), (0, 0, 0, 0))

    for sub_idx, entry in glyph_entries.items():
        if not (0 <= sub_idx <= 255):
            continue

        if isinstance(entry, dict):
            char_img = entry.get("img")
        else:
            char_img = entry

        if char_img is None:
            continue

        cw, ch = char_img.size
        if cw <= 0 or ch <= 0:
            continue

        row = sub_idx // 16
        col = sub_idx % 16

        # Scale image to fit within the tile_size x tile_size cell while preserving aspect ratio
        scale = min(float(tile_size) / float(cw), float(tile_size) / float(ch))
        target_w = max(1, min(tile_size, int(round(cw * scale))))
        target_h = max(1, min(tile_size, int(round(ch * scale))))

        # Choose resampling filter
        resample_filter = RESAMPLING_NEAREST if (cw == target_w and ch == target_h) else RESAMPLING_LANCZOS
        img_resized = char_img.resize((target_w, target_h), resample_filter)

        # Create a single isolated cell image
        cell_img = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))

        # Center the glyph within its own cell (so wide ranks are centered vertically, tall icons centered horizontally)
        offset_x = (tile_size - target_w) // 2
        offset_y = (tile_size - target_h) // 2

        cell_img.paste(img_resized, (offset_x, offset_y), img_resized if img_resized.mode == "RGBA" else None)

        # Paste the cell strictly at (col * tile_size, row * tile_size)
        pos_x = col * tile_size
        pos_y = row * tile_size

        sheet.paste(cell_img, (pos_x, pos_y), cell_img)

    # Save to output directories
    out_dirs = [output_dir, "target/rp/font"] if output_dir != "target/rp/font" else [output_dir]
    out_file = None
    for od in out_dirs:
        try:
            os.makedirs(od, exist_ok=True)
            target_path = os.path.join(od, f"glyph_{glyph_page.upper()}.png")
            sheet.save(target_path, "PNG")
            out_file = target_path
        except Exception as e:
            print(f"[FONT] Warning saving {od}: {e}")

    print(f"[FONT] Saved Bedrock HD font sheet: glyph_{glyph_page.upper()}.png ({sheet_dim}x{sheet_dim}, {len(glyph_entries)} glyphs)")
    return out_file
