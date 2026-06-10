#!/usr/bin/env python3
"""
Generate Cyrillic SDF glyphs and add them to existing TMP SDF font assets.

Approach:
1. Read existing SDF font atlas (Texture2D, Alpha8 format)
2. Find free space in the atlas
3. Render Cyrillic glyphs using freetype
4. Generate SDF (signed distance field) for each glyph
5. Write glyphs to atlas free space
6. Add glyph entries to the MonoBehaviour data
7. Save modified sharedassets3.assets
"""
import os, sys, struct, math, json
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
import numpy as np
from PIL import Image
from pathlib import Path
import freetype

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")

# Cyrillic characters to add
CYRILLIC_CHARS = (
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя"
)


def read_sdf_font_data(env, font_path_id):
    """Read and parse SDF font MonoBehaviour data."""
    for obj in env.objects:
        if obj.path_id != font_path_id:
            continue

        raw = obj.get_raw_data()

        # Parse glyph table at offset 188
        # First 4 bytes at 188: array length
        glyph_table_offset = 188
        num_glyphs = struct.unpack_from('<I', raw, glyph_table_offset)[0]

        glyphs = []
        for i in range(num_glyphs):
            entry_offset = glyph_table_offset + 4 + i * 36
            unicode_val = struct.unpack_from('<I', raw, entry_offset)[0]
            floats = struct.unpack_from('<8f', raw, entry_offset + 4)
            glyphs.append({
                'unicode': unicode_val,
                'char': chr(unicode_val) if unicode_val < 65536 else '?',
                'atlas_x': floats[0],
                'atlas_y': floats[1],
                'width': floats[2],
                'height': floats[3],
                'xOffset': floats[4],
                'yOffset': floats[5],
                'xAdvance': floats[6],
                'scale': floats[7],
            })

        # Get atlas PPtr
        pptr_offset = 176
        atlas_file_id = struct.unpack_from('<i', raw, pptr_offset)[0]
        atlas_path_id = struct.unpack_from('<q', raw, pptr_offset + 4)[0]

        # Get font metrics (before glyph table)
        # At offset ~96: float values for font metrics
        # Let's extract key metrics
        metrics_offset = 96
        font_size = struct.unpack_from('<f', raw, metrics_offset)[0]
        line_height = struct.unpack_from('<f', raw, metrics_offset + 4)[0]

        return {
            'raw': raw,
            'object': obj,
            'num_glyphs': num_glyphs,
            'glyphs': glyphs,
            'glyph_table_offset': glyph_table_offset,
            'atlas_path_id': atlas_path_id,
            'font_size': font_size,
            'line_height': line_height,
        }

    return None


def read_atlas_texture(env, atlas_path_id):
    """Read the SDF atlas texture."""
    for obj in env.objects:
        if obj.path_id != atlas_path_id:
            continue

        data = obj.read()
        print(f"Atlas: {data.m_Name}, {data.m_Width}x{data.m_Height}, format={data.m_TextureFormat}")

        # Get the raw image data
        img = data.image
        if img:
            print(f"Image: {img.size}, mode={img.mode}")
            return data, img, obj

    return None, None, None


def generate_sdf_glyph(face, char, render_size=32, spread=4):
    """Render a single glyph and generate its SDF."""
    face.set_pixel_sizes(0, render_size)

    try:
        face.load_char(char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
    except Exception as e:
        print(f"  Cannot render '{char}': {e}")
        return None

    bitmap = face.glyph.bitmap
    if bitmap.width == 0 or bitmap.rows == 0:
        return None

    # Convert bitmap to numpy array
    buffer = np.array(bitmap.buffer, dtype=np.uint8).reshape(bitmap.rows, bitmap.width)

    # Add padding for SDF spread
    padded = np.zeros((bitmap.rows + spread * 2, bitmap.width + spread * 2), dtype=np.uint8)
    padded[spread:spread + bitmap.rows, spread:spread + bitmap.width] = buffer

    # Generate SDF using distance transform
    # Simple approach: for each pixel, find distance to nearest edge
    h, w = padded.shape
    sdf = np.zeros((h, w), dtype=np.float32)

    # Binary mask: inside (>128) vs outside
    inside = padded > 128

    for y in range(h):
        for x in range(w):
            # Search radius
            min_dist = spread + 1
            is_inside = inside[y, x]

            for dy in range(-spread, spread + 1):
                for dx in range(-spread, spread + 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        if inside[ny, nx] != is_inside:
                            dist = math.sqrt(dx * dx + dy * dy)
                            min_dist = min(min_dist, dist)

            if is_inside:
                sdf[y, x] = min_dist
            else:
                sdf[y, x] = -min_dist

    # Normalize SDF to 0-255 range
    sdf_normalized = ((sdf / spread) * 0.5 + 0.5).clip(0, 1)
    sdf_uint8 = (sdf_normalized * 255).astype(np.uint8)

    return {
        'bitmap': sdf_uint8,
        'width': w,
        'height': h,
        'bearingX': face.glyph.bitmap_left - spread,
        'bearingY': face.glyph.bitmap_top + spread,
        'advance': face.glyph.advance.x // 64,
        'original_width': bitmap.width,
        'original_height': bitmap.rows,
    }


def find_atlas_free_space(atlas_img, glyphs, new_glyph_sizes, padding=2):
    """Find free space in the atlas for new glyphs using simple row packing."""
    w, h = atlas_img.size

    # Get atlas as array
    atlas_array = np.array(atlas_img)
    if atlas_array.ndim == 3:
        atlas_array = atlas_array[:, :, 0]  # Take first channel

    # Find the maximum Y extent of existing glyphs
    max_y = 0
    for g in glyphs:
        gy = int(g['atlas_y'] + g['height'])
        if gy > max_y:
            max_y = gy

    print(f"  Atlas size: {w}x{h}")
    print(f"  Existing glyphs max Y: {max_y}")
    print(f"  Available height: {h - max_y - padding}")

    # Simple row packing from max_y
    positions = []
    cur_x = padding
    cur_y = max_y + padding
    row_height = 0

    for gw, gh in new_glyph_sizes:
        if cur_x + gw + padding > w:
            # New row
            cur_x = padding
            cur_y += row_height + padding
            row_height = 0

        if cur_y + gh + padding > h:
            print(f"  WARNING: Atlas full! Need larger atlas.")
            return None

        positions.append((cur_x, cur_y))
        cur_x += gw + padding
        row_height = max(row_height, gh)

    print(f"  Packed {len(positions)} new glyphs, final Y: {cur_y + row_height}")
    return positions


def main():
    print("=" * 60)
    print("CYRILLIC SDF FONT GENERATOR")
    print("=" * 60)

    # Find Ubuntu font file
    # Ubuntu fonts are bundled as Font objects in sharedassets3
    # But we need the TTF file for freetype rendering
    # Check system fonts
    font_paths = [
        str(PROJECT / "fonts" / "Ubuntu-Bold.ttf"),
        r"C:\Windows\Fonts\Ubuntu-Bold.ttf",
        r"C:\Windows\Fonts\Ubuntu-B.ttf",
    ]

    # Also try to extract from the game's Font assets
    ubuntu_ttf = None
    for p in font_paths:
        if os.path.exists(p):
            ubuntu_ttf = p
            break

    if not ubuntu_ttf:
        # Try to extract from game
        print("Ubuntu font not found in system. Trying to extract from game...")
        env = UnityPy.load(str(GAME_DATA / "sharedassets3.assets"))
        for obj in env.objects:
            if obj.type.name == "Font":
                data = obj.read()
                if "Bold" in data.m_Name and "Italic" not in data.m_Name:
                    # Export the font data
                    if hasattr(data, 'm_FontData') and data.m_FontData:
                        font_data = data.m_FontData
                        if isinstance(font_data, bytes) and len(font_data) > 1000:
                            out = PROJECT / "fonts" / f"{data.m_Name}.ttf"
                            with open(out, "wb") as f:
                                f.write(font_data)
                            ubuntu_ttf = str(out)
                            print(f"  Extracted: {out} ({len(font_data)} bytes)")
                            break

    if not ubuntu_ttf:
        print("ERROR: Cannot find Ubuntu-Bold.ttf. Please install Ubuntu fonts.")
        print("Download from: https://fonts.google.com/specimen/Ubuntu")
        return

    print(f"Using font: {ubuntu_ttf}")

    # Load the game assets
    env = UnityPy.load(str(GAME_DATA / "sharedassets3.assets"))

    # Read Ubuntu-Bold SDF font data
    print("\n--- Reading Ubuntu-Bold SDF ---")
    font_data = read_sdf_font_data(env, 2411)
    if not font_data:
        print("ERROR: Font not found")
        return

    print(f"  Glyphs: {font_data['num_glyphs']}")
    print(f"  Atlas path_id: {font_data['atlas_path_id']}")

    # Check which glyphs already exist
    existing_unicodes = {g['unicode'] for g in font_data['glyphs']}
    needed_chars = [c for c in CYRILLIC_CHARS if ord(c) not in existing_unicodes]
    print(f"  Need to add: {len(needed_chars)} Cyrillic chars")

    if not needed_chars:
        print("  All Cyrillic chars already present!")
        return

    # Read atlas texture
    print("\n--- Reading atlas texture ---")
    tex_data, atlas_img, tex_obj = read_atlas_texture(env, font_data['atlas_path_id'])
    if atlas_img is None:
        print("ERROR: Cannot read atlas texture")
        return

    # Save original atlas for reference
    atlas_img.save(str(PROJECT / "fonts" / "original_atlas_bold.png"))
    print(f"  Saved original atlas: fonts/original_atlas_bold.png")

    # Generate SDF glyphs for Cyrillic characters
    print(f"\n--- Generating SDF glyphs ---")
    face = freetype.Face(ubuntu_ttf)

    # Calculate render size based on existing glyph metrics
    # Most glyphs are ~27-30 pixels tall in the atlas
    avg_height = np.mean([g['height'] for g in font_data['glyphs'] if g['height'] > 5])
    render_size = int(avg_height) + 4  # Add margin for SDF spread
    spread = 3
    print(f"  Render size: {render_size}, SDF spread: {spread}")

    new_glyphs = []
    for char in needed_chars:
        glyph = generate_sdf_glyph(face, char, render_size=render_size, spread=spread)
        if glyph:
            new_glyphs.append((char, glyph))
        else:
            print(f"  SKIP: '{char}' (U+{ord(char):04X}) - no bitmap")

    print(f"  Generated {len(new_glyphs)} SDF glyphs")

    if not new_glyphs:
        print("ERROR: No glyphs generated")
        return

    # Find free space in atlas
    print("\n--- Packing into atlas ---")
    new_sizes = [(g['width'], g['height']) for _, g in new_glyphs]
    positions = find_atlas_free_space(atlas_img, font_data['glyphs'], new_sizes)

    if positions is None:
        # Need to expand atlas - create 1024x512 or 512x1024
        print("  Expanding atlas to 512x1024...")
        new_atlas = Image.new('L', (512, 1024), 0)
        new_atlas.paste(atlas_img, (0, 0))
        atlas_img = new_atlas
        positions = find_atlas_free_space(atlas_img, font_data['glyphs'], new_sizes)

    if positions is None:
        print("ERROR: Cannot fit glyphs even in expanded atlas")
        return

    # Write glyphs to atlas
    atlas_array = np.array(atlas_img)
    for (char, glyph), (px, py) in zip(new_glyphs, positions):
        atlas_array[py:py + glyph['height'], px:px + glyph['width']] = glyph['bitmap']

    new_atlas_img = Image.fromarray(atlas_array, 'L')
    new_atlas_img.save(str(PROJECT / "fonts" / "cyrillic_atlas_bold.png"))
    print(f"  Saved new atlas: fonts/cyrillic_atlas_bold.png")

    # Build new glyph entries
    print("\n--- Building glyph table ---")

    # Calculate scaling factors from existing glyphs
    # Find a reference glyph (e.g., 'A' = 65)
    ref_glyph = None
    for g in font_data['glyphs']:
        if g['unicode'] == 65:  # 'A'
            ref_glyph = g
            break

    if ref_glyph:
        print(f"  Reference glyph 'A': width={ref_glyph['width']:.1f}, height={ref_glyph['height']:.1f}")
        print(f"    xOffset={ref_glyph['xOffset']:.1f}, yOffset={ref_glyph['yOffset']:.1f}")
        print(f"    xAdvance={ref_glyph['xAdvance']:.1f}, scale={ref_glyph['scale']:.1f}")

    # Scale factor from render_size to font metrics
    # The existing glyphs were rendered at some base size, we need to match
    face.set_pixel_sizes(0, render_size)
    face.load_char('A', freetype.FT_LOAD_RENDER)
    ref_advance_px = face.glyph.advance.x // 64
    if ref_glyph and ref_advance_px > 0:
        advance_scale = ref_glyph['xAdvance'] / ref_advance_px
    else:
        advance_scale = 1.0
    print(f"  Advance scale factor: {advance_scale:.3f}")

    new_glyph_entries = []
    for (char, glyph), (px, py) in zip(new_glyphs, positions):
        entry = {
            'unicode': ord(char),
            'atlas_x': float(px),
            'atlas_y': float(py),
            'width': float(glyph['width']),
            'height': float(glyph['height']),
            'xOffset': float(glyph['bearingX']) * advance_scale,
            'yOffset': float(glyph['bearingY']) * advance_scale,
            'xAdvance': float(glyph['advance']) * advance_scale,
            'scale': 1.0,
        }
        new_glyph_entries.append(entry)

    # Build new raw data for the MonoBehaviour
    print("\n--- Modifying font data ---")
    raw = bytearray(font_data['raw'])

    # Update glyph count
    new_total = font_data['num_glyphs'] + len(new_glyph_entries)
    glyph_table_offset = font_data['glyph_table_offset']

    # Insert new glyph entries after existing ones
    insert_offset = glyph_table_offset + 4 + font_data['num_glyphs'] * 36

    new_entries_data = b''
    for entry in new_glyph_entries:
        new_entries_data += struct.pack('<I', entry['unicode'])
        new_entries_data += struct.pack('<8f',
            entry['atlas_x'], entry['atlas_y'],
            entry['width'], entry['height'],
            entry['xOffset'], entry['yOffset'],
            entry['xAdvance'], entry['scale'])

    # Splice the data
    new_raw = bytes(raw[:glyph_table_offset])
    new_raw += struct.pack('<I', new_total)  # Updated count
    new_raw += bytes(raw[glyph_table_offset + 4:insert_offset])
    new_raw += new_entries_data
    new_raw += bytes(raw[insert_offset:])

    print(f"  Old raw size: {len(raw)}, New: {len(new_raw)}, Added: {len(new_entries_data)} bytes")
    print(f"  Glyph count: {font_data['num_glyphs']} -> {new_total}")

    # Set the modified raw data
    font_data['object'].set_raw_data(new_raw)

    # Update atlas texture
    print("\n--- Updating atlas texture ---")
    # Format 1 = Alpha8. UnityPy reads as RGBA, we need to write back as RGBA
    # where our grayscale value becomes the alpha channel
    rgba_atlas = Image.new('RGBA', new_atlas_img.size, (255, 255, 255, 0))
    # Set alpha channel from our grayscale SDF
    r, g, b, a = rgba_atlas.split()
    rgba_atlas = Image.merge('RGBA', (r, g, b, new_atlas_img))

    tex_data.m_Width = rgba_atlas.width
    tex_data.m_Height = rgba_atlas.height
    tex_data.image = rgba_atlas
    tex_data.save()
    print(f"  Atlas updated: {rgba_atlas.width}x{rgba_atlas.height}")

    # Save the modified assets file
    print("\n--- Saving modified sharedassets3.assets ---")
    out_path = PROJECT / "patches" / "sharedassets3.assets"
    with open(out_path, "wb") as f:
        f.write(env.file.save())

    orig_size = (GAME_DATA / "sharedassets3.assets").stat().st_size
    new_size = out_path.stat().st_size
    print(f"  Original: {orig_size} bytes")
    print(f"  Modified: {new_size} bytes ({new_size - orig_size:+d})")

    # Verify
    print("\n--- Verification ---")
    env2 = UnityPy.load(str(out_path))
    obj_count = sum(1 for _ in env2.objects)
    print(f"  Objects: {obj_count}")

    print("\nDone! Cyrillic SDF font generated.")
    print("Next: copy patches/sharedassets3.assets to game and test.")


if __name__ == "__main__":
    main()
