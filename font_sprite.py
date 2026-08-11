import os
from PIL import Image

try:
    Resampling_LANCZOS = Image.Resampling.LANCZOS
    Resampling_NEAREST = Image.Resampling.NEAREST
except AttributeError:
    Resampling_LANCZOS = Image.LANCZOS
    Resampling_NEAREST = Image.NEAREST


def create_glyph_sheet(glyph_page, glyph_entries, output_dir="staging/target/rp/font", tile_size=None):
    """
    Creates a Bedrock font glyph sheet (16x16 grid of character cells) for a given unicode page.
    glyph_page: 2-character hex string (e.g. 'E0', '00', '1F')
    glyph_entries: dict mapping sub_index (0..255) -> PIL Image object
    output_dir: directory where glyph_XX.png will be saved
    """
    os.makedirs(output_dir, exist_ok=True)

    if not glyph_entries:
        return None

    # Calculate optimal tile size
    if tile_size is None:
        max_w = max(img.width for img in glyph_entries.values())
        max_h = max(img.height for img in glyph_entries.values())
        dim = max(max_w, max_h, 16)
        # Round up to a power of 2 or nice multiple for texture rendering
        tile_size = 16
        while tile_size < dim and tile_size < 512:
            tile_size *= 2
        if tile_size < dim:
            tile_size = dim

    sheet_dim = tile_size * 16
    sheet = Image.new("RGBA", (sheet_dim, sheet_dim), (0, 0, 0, 0))

    for sub_idx, char_img in glyph_entries.items():
        if not (0 <= sub_idx <= 255):
            continue
        row = sub_idx // 16
        col = sub_idx % 16

        cw, ch = char_img.size
        if cw > tile_size or ch > tile_size:
            # Scale down proportionally to fit tile
            scale = min(tile_size / cw, tile_size / ch)
            new_w = max(1, int(cw * scale))
            new_h = max(1, int(ch * scale))
            img_to_paste = char_img.resize((new_w, new_h), Resampling_LANCZOS)
        else:
            img_to_paste = char_img

        iw, ih = img_to_paste.size
        # Center the glyph within its cell
        offset_x = (tile_size - iw) // 2
        offset_y = (tile_size - ih) // 2

        pos_x = col * tile_size + offset_x
        pos_y = row * tile_size + offset_y

        sheet.paste(img_to_paste, (pos_x, pos_y), img_to_paste if img_to_paste.mode == "RGBA" else None)

    out_file = os.path.join(output_dir, f"glyph_{glyph_page.upper()}.png")
    sheet.save(out_file, "PNG")
    print(f"[FONT] Saved Bedrock font sheet: {out_file} ({sheet_dim}x{sheet_dim}, {len(glyph_entries)} glyphs)")
    return out_file
