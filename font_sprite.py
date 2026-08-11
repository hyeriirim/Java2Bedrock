import os
from PIL import Image

try:
    Resampling_LANCZOS = Image.Resampling.LANCZOS
    Resampling_NEAREST = Image.Resampling.NEAREST
except AttributeError:
    Resampling_LANCZOS = Image.LANCZOS
    Resampling_NEAREST = Image.NEAREST


def create_glyph_sheet(glyph_page, glyph_entries, output_dir="staging/target/rp/font", tile_size=256):
    """
    Creates an HD Bedrock font glyph sheet (16x16 grid of character cells) for a given unicode page.
    glyph_page: 2-character hex string (e.g. 'E0', '00', '1F')
    glyph_entries: dict mapping sub_index (0..255) -> dict containing:
        - "img": PIL Image object of the character
        - "height": Java height property (default 8)
        - "ascent": Java ascent property (default 7)
        - "gui_offset": [dx, dy] optional GUI offset
    output_dir: directory where glyph_XX.png will be saved
    tile_size: pixel size per cell (default 256 for crisp 4096x4096 HD sheets)
    """
    os.makedirs(output_dir, exist_ok=True)

    if not glyph_entries:
        return None

    # Base scale: 1 game font unit = (tile_size / 8.0) pixels
    scale_unit = tile_size / 8.0

    sheet_dim = tile_size * 16
    sheet = Image.new("RGBA", (sheet_dim, sheet_dim), (0, 0, 0, 0))

    for sub_idx, entry in glyph_entries.items():
        if not (0 <= sub_idx <= 255):
            continue

        if isinstance(entry, dict):
            char_img = entry.get("img")
            h_java = entry.get("height", 8)
            a_java = entry.get("ascent", 7)
            gui_offset = entry.get("gui_offset", [0, 0])
        else:
            char_img = entry
            h_java = 8
            a_java = 7
            gui_offset = [0, 0]

        if char_img is None:
            continue

        cw, ch = char_img.size
        if cw <= 0 or ch <= 0:
            continue

        row = sub_idx // 16
        col = sub_idx % 16

        # Calculate exact target tile dimensions matching Java font height & aspect ratio
        target_h = max(1, int(round(h_java * scale_unit)))
        aspect_ratio = cw / float(ch)
        target_w = max(1, int(round(target_h * aspect_ratio)))

        # Choose resampling filter: LANCZOS for smooth high-res scaling
        resample_filter = Resampling_NEAREST if (cw == target_w and ch == target_h) else Resampling_LANCZOS
        img_to_paste = char_img.resize((target_w, target_h), resample_filter)

        # Baseline alignment: Java standard ascent is 7 units from baseline
        # Ascent A means baseline is A units below top of glyph
        # Standard Bedrock baseline is at 7 units from cell top
        y_baseline_offset = int(round((7 - a_java) * scale_unit))

        dx = int(round(gui_offset[0] * scale_unit)) if len(gui_offset) > 0 else 0
        dy = int(round(gui_offset[1] * scale_unit)) if len(gui_offset) > 1 else 0

        pos_x = col * tile_size + dx
        pos_y = row * tile_size + y_baseline_offset + dy

        # Paste onto sheet, preserving alpha channel
        sheet.paste(img_to_paste, (pos_x, pos_y), img_to_paste if img_to_paste.mode == "RGBA" else None)

    out_file = os.path.join(output_dir, f"glyph_{glyph_page.upper()}.png")
    sheet.save(out_file, "PNG")
    print(f"[FONT] Saved Bedrock HD font sheet: {out_file} ({sheet_dim}x{sheet_dim}, {len(glyph_entries)} glyphs)")
    return out_file
