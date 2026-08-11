import zipfile
import os

if os.path.exists("staging/input_pack.zip"):
    with zipfile.ZipFile("staging/input_pack.zip", "r") as file:
        file.extractall("pack/")
elif os.path.exists("input_pack.zip"):
    with zipfile.ZipFile("input_pack.zip", "r") as file:
        file.extractall("pack/")

try:
    if os.getenv("SOUNDS_CONVERSION") == "true":
        import sound
except Exception as e:
    print(f"[MANAGER] Sound error: {e}")

try:
    if os.getenv("PAINTING_CONVERSION") == "true":
        import painting
except Exception as e:
    print(f"[MANAGER] Painting error: {e}")

try:
    if os.getenv("MEG3_FIX") == "true":
        import meg3
except Exception as e:
    print(f"[MANAGER] MEG error: {e}")

try:
    if os.getenv("ARMOR_CONVERSION") == "true":
        import armor
except Exception as e:
    print(f"[MANAGER] Armor error: {e}")

try:
    if os.getenv("FONT_CONVERSION") == "true":
        import font
except Exception as e:
    print(f"[MANAGER] Font error: {e}")

try:
    if os.getenv("BOW_CONVERSION") == "true":
        import bow
except Exception as e:
    print(f"[MANAGER] Bow error: {e}")

try:
    if os.getenv("SHIELD_CONVERSION") == "true":
        import shield
except Exception as e:
    print(f"[MANAGER] Shield error: {e}")

try:
    if os.getenv("BLOCK_CONVERSION") == "true":
        import blocks
except Exception as e:
    print(f"[MANAGER] Block error: {e}")
