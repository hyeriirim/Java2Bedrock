"""
font_sprite.py - Bedrock glyph sheet assembler.
Replicates the original sprite() function that creates 16x16 glyph grid sheets,
but works in-memory without requiring disk-based export/ and images/ folders.

The original code:
1. Listed all 256 exported PNGs in export/<page>/ (sorted by filename)
2. Got tile size from the first frame
3. Created a 16-row spritesheet with up to 16 columns per row
4. Pasted each frame in order

This version does the same but accepts an in-memory dict of glyph images.
"""
from PIL import Image
import os

try:
    RESAMPLING_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING_LANCZOS = Image.LANCZOS


def sprite(glyph_page, tile_size, glyph_images, output_dir="staging/target/rp/font"):
    """
    Creates a Bedrock glyph sheet (16x16 grid) for a given unicode page.

    Args:
        glyph_page: 2-character hex string (e.g. 'E0')
        tile_size: (width, height) tuple for each cell - matches original behavior
                   where tile_size = (max_w+1, max_w+1) of all glyphs in this page
        glyph_images: dict mapping hex suffix (2-char string like 'a3') -> PIL Image
                      These images should already be processed (thumbnailed and pasted
                      onto blank backgrounds by the caller).
        output_dir: directory where glyph_XX.png will be saved
    """
    os.makedirs(output_dir, exist_ok=True)

    if not glyph_images:
        return None

    max_frames_row = 16
    tile_w, tile_h = tile_size

    # We need exactly 256 slots (16x16 grid) but only non-blank ones will have content
    # Calculate sheet dimensions
    spritesheet_width = int(tile_w * max_frames_row)
    spritesheet_height = int(tile_h * max_frames_row)

    spritesheet = Image.new("RGBA", (spritesheet_width, spritesheet_height), (0, 0, 0, 0))

    for hex_suffix, img in glyph_images.items():
        # hex_suffix is like "a3" -> decimal index = 0xa3 = 163
        try:
            idx = int(hex_suffix, 16)
        except ValueError:
            continue

        if not (0 <= idx <= 255):
            continue

        row = idx // max_frames_row
        col = idx % max_frames_row

        left = int(col * tile_w)
        top = int(row * tile_h)

        # Resize image to tile size if needed
        if img.size != (int(tile_w), int(tile_h)):
            # Create a blank tile and paste the image onto it
            tile_img = Image.new("RGBA", (int(tile_w), int(tile_h)), (0, 0, 0, 0))
            tile_img.paste(img, (0, 0), img if img.mode == "RGBA" else None)
            spritesheet.paste(tile_img, (left, top), tile_img)
        else:
            spritesheet.paste(img, (left, top), img if img.mode == "RGBA" else None)

    out_file = os.path.join(output_dir, f"glyph_{glyph_page}.png")
    spritesheet.save(out_file, "PNG")
    print(f"[FONT] Saved glyph sheet: {out_file} ({spritesheet_width}x{spritesheet_height})")
    return out_file
