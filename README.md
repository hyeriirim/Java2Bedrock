# Java2Bedrock – Resource Pack Conversion Tool

Java2Bedrock converts Minecraft Java Edition custom resource packs (including **ItemsAdder**, **Oraxen**, and custom server packs) into Geyser-compatible **Bedrock Edition resource packs** (`.mcpack` / `.mcaddon`) and Geyser custom mappings (`geyser_mappings.json`).

## Supported Features

- **Custom 2D & 3D Items**: Automatic model and texture conversion for custom items with CustomModelData and damage predicates across all namespaces (`minecraft`, `oraxen`, `itemsadder`, custom).
- **Font & Unicode Glyphs**: Converts Java font definitions (`pack/assets/*/font/*.json`) and bitmap glyphs to Bedrock 16x16 glyph sheets (`font/glyph_XX.png`).
- **Custom Armors**: Converts Optifine CIT armor configurations (ItemsAdder `ia_generated_armors`, Oraxen `armor/`, and generic CIT) across all armor materials (leather, diamond, iron, gold, chainmail, netherite, turtle).
- **Custom Paintings**: Automatically extracts Java painting textures (`assets/**/textures/painting/*.png`) and generates individual Bedrock painting textures and the Bedrock `textures/painting/kz.png` atlas sheet.
- **Custom Bows & Crossbows**: Pulling animations and custom attachable states (`0.0`, `0.65`, `0.9` pull stages).
- **Custom Shields**: Standby and blocking attachable states for both main-hand and off-hand blocking.
- **Custom Blocks & Blockstates**: Automatic mapping and texture terrain atlas registration for custom blocks (tripwire, note blocks, chorus, etc.).
- **Custom Sounds**: Converts Java `sounds.json` into Bedrock `sound_definitions.json` and copies OGG sound files.
- **ModelEngine Alpha Fix**: Optional MEG3/MEG4 alpha transparency correction.

## How to Use

### Local Execution (Linux / WSL / macOS)

Ensure dependencies are installed:
- `jq` (1.6+)
- `sponge` (moreutils)
- `imagemagick`
- `nodejs` & `spritesheet-js` (`npm i -g spritesheet-js`)
- `python3` & `pip install Pillow requests jproperties`

To run:
```bash
./converter.sh MyResourcePack.zip
```

#### Command Flags:
- `-w (true|false)`: Whether or not to show the warning prompt (default: `true`)
- `-m (pack_to_merge.mcpack)`: Bedrock Edition resource pack to merge with conversion output
- `-a (attachable_material)`: Material for attachables (e.g. `entity_alphatest_one_sided`)
- `-b (block_material)`: Material for blocks (e.g. `alpha_test`)
- `-f (fallback_pack_url|null)`: Direct URL of a Java resource pack for fallback textures
- `-v (default_asset_version)`: Minecraft Java version for default assets (default: `1.19.3`)

Example:
```bash
./converter.sh MyResourcePack.zip -w "false" -m "MyBedrock.mcpack" -a "entity_alphatest_one_sided" -b "alpha_test" -f "null" -v "1.19.3"
```

### Environment Flags for Python Features

Set these environment variables when running `manager.py` or via the script:
- `FONT_CONVERSION=true`: Enable font and glyph conversion
- `ARMOR_CONVERSION=true`: Enable armor attachables and layer textures conversion (ItemsAdder & Oraxen)
- `PAINTING_CONVERSION=true`: Enable custom paintings conversion & `kz.png` atlas generation
- `BOW_CONVERSION=true`: Enable custom bow and crossbow pulling animations
- `SHIELD_CONVERSION=true`: Enable custom shield blocking animations
- `BLOCK_CONVERSION=true`: Enable custom blockstates conversion
- `SOUNDS_CONVERSION=true`: Enable custom sounds conversion
- `MEG3_FIX=true`: Enable ModelEngine alpha transparency fix

### Custom GUI & Font Skip Configuration

You can provide an optional `font_config.json` in your pack root to skip specific characters or configure custom GUI offsets:
```json
{
  "0xE200": {
    "skip": true
  },
  "0xE201": {
    "skip": true,
    "gui": [0, 6]
  },
  "\uE202": {
    "skip": false,
    "gui": [0, 16]
  }
}
```

### Item Icons (2D Sprites for 3D Models)

If you have 2D sprites for your 3D models, include `sprites.json` in the root of your Java resource pack:
```json
{
    "leather": [
        {
            "custom_model_data": 1,
            "sprite": "textures/path/to/texture_in_bedrock_rp/texture1"
        }
    ],
    "diamond_axe": [
        {
            "damage_predicate": 2,
            "unbreakable": true,
            "sprite": "textures/path/to/texture_in_bedrock_rp/texture2"
        }
    ]
}
```

### GitHub Actions Automated Conversion

You can also run conversion via GitHub Actions by submitting an issue using the [Pack Conversion](https://github.com/Kas-tle/java2bedrock.sh/issues/new?template=pack-conversion.yml) template. Provide a direct download link to your Java pack, select your desired conversion modules (Armor, Fonts, Paintings, Bows, Shields, Blocks, Sounds), and download the converted `.mcpack` and `geyser_mappings.json` directly from the workflow run artifacts!
