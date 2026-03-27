#!/usr/bin/env python3
"""
Add Cyrillic glyphs to LiberationSans SDF in resources.assets.
v7: Per-case baseline correction — Cyrillic lowercase yOffset adjusted to match
    Latin lowercase baseline, fixing punctuation vertical misalignment.
v6: Brightness boost +12 for thicker strokes without changing render_size.
v5: Proper SDF generation with spread=5 using distance_transform_edt.
    Render size calibrated so bitmap + 2*spread ≈ original atlas glyph dimensions.
    Adds № symbol (U+2116).
    Per-glyph max rescaling (Option A) so thin-stroke Cyrillic glyphs reach target_max,
    eliminating the weight mismatch between Cyrillic (~162) and Latin (~182) SDF values.
"""
import os, sys, struct, math
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
import numpy as np
from PIL import Image
from pathlib import Path
import freetype
from scipy.ndimage import distance_transform_edt

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")
BACKUP = PROJECT / "backup"

FONT_PATH_ID = 5003
ATLAS_PATH_ID = 178
ATLAS_HEIGHT_OFFSET = 172
GLYPH_COUNT_OFFSET = 188
GLYPH_TABLE_OFFSET = 192

# LiberationSans SDF material path_ids in resources.assets.
# Their _TextureHeight must match the atlas height for correct SDF rendering.
LIBERATION_MATERIAL_IDS = {9, 10, 11, 12, 13, 23}

# Spread for SDF generation — matches TextMeshPro Font Asset Creator default
SDF_SPREAD = 5

# Calibrated render size: at size=71, 'A' bitmap is 48x49.
# With spread=5: padded = 58x59 which matches atlas 'A' height (59.16) exactly.
RENDER_SIZE = 71

# Average max pixel value of original Latin A-Z glyphs in the atlas (~181).
# Used to match the gradient intensity of new Cyrillic glyphs to Latin ones.
TARGET_MAX = 182

# Cyrillic characters to add, including № (U+2116) which is missing and shows as a square.
CYRILLIC_CHARS = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя№"


def read_original_atlas():
    """Read original atlas texture from backup, preserving exact pixel data."""
    # Load from backup to get pristine data
    env = UnityPy.load(str(BACKUP / "resources.assets"))
    for obj in env.objects:
        if obj.path_id == ATLAS_PATH_ID:
            tex = obj.read()
            img = tex.image
            print(f"Original atlas: {tex.m_Name}, {tex.m_Width}x{tex.m_Height}, fmt={tex.m_TextureFormat}")
            # Convert to grayscale array
            arr = np.array(img)
            if arr.ndim == 3:
                arr = arr[:, :, -1]  # Alpha channel for Alpha8
            print(f"  Array shape: {arr.shape}, nonzero: {np.count_nonzero(arr)}")
            # Verify data integrity
            for cp_name, x, y, w, h in [('A', 751, 871, 57, 59), ('O', 414, 828, 59, 61)]:
                region = arr[int(y):int(y+h), int(x):int(x+w)]
                print(f"  Verify '{cp_name}' at ({x},{y}): max={region.max()}, nonzero={np.count_nonzero(region)}")
            return arr, tex.m_Width, tex.m_Height
    return None, 0, 0


def generate_sdf_glyph(face, char, render_size, spread, target_max=TARGET_MAX):
    """
    Render a glyph and generate a proper SDF using distance_transform_edt.

    The glyph is rendered at render_size so that (bitmap + 2*spread) ≈ the original
    atlas slot dimensions, matching how TextMeshPro Font Asset Creator works.

    Normalization: sdf / spread maps to [-1, +1], shifted to [0, 1].
    Then scaled to target_max so inside-center ≈ target_max and the
    gradient range matches the original Latin glyphs.
    """
    face.set_pixel_sizes(0, render_size)
    try:
        face.load_char(char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
    except Exception:
        return None

    bitmap = face.glyph.bitmap
    if bitmap.width == 0 or bitmap.rows == 0:
        return None

    buffer = np.array(bitmap.buffer, dtype=np.uint8).reshape(bitmap.rows, bitmap.width)

    # Pad the bitmap by spread on all sides so the SDF can extend to the edge of the atlas slot
    padded = np.zeros((bitmap.rows + spread * 2, bitmap.width + spread * 2), dtype=np.uint8)
    padded[spread:spread + bitmap.rows, spread:spread + bitmap.width] = buffer

    # Threshold at 128: anti-aliased edge pixels treated as outside for clean SDF
    inside = padded > 128

    # Compute signed distance field using Euclidean distance transform
    dist_outside = distance_transform_edt(~inside)   # distance from outside pixels to nearest inside
    dist_inside  = distance_transform_edt(inside)    # distance from inside pixels to nearest outside

    # sdf > 0 inside glyph, sdf < 0 outside, boundary = 0
    sdf = dist_inside - dist_outside

    # Normalize: divide by spread so the meaningful gradient fits in [-1, +1],
    # shift to [0, 1] so the glyph boundary maps to exactly 0.5.
    # Then scale to target_max so the deep-interior of thick strokes reaches ~target_max,
    # matching the empirically observed max (~182) of the original Latin SDF glyphs.
    sdf_normalized = ((sdf / spread) * 0.5 + 0.5).clip(0.0, 1.0)
    sdf_uint8 = (sdf_normalized * target_max).clip(0, 255).astype(np.uint8)

    # Option A fix: for thin-stroke glyphs the theoretical maximum (target_max) is never
    # reached because the center of a thin stroke is only 2-3px from the boundary, so
    # sdf/spread peaks at 0.4-0.6 rather than 1.0.  Re-scale each glyph so its ACTUAL
    # maximum matches target_max, making Cyrillic SDF intensity match the Latin originals.
    actual_max = int(sdf_uint8.max())
    if actual_max > 0 and actual_max < target_max:
        scale = target_max / actual_max
        sdf_uint8 = (sdf_uint8.astype(np.float32) * scale).clip(0, 255).astype(np.uint8)

    # v6: brightness boost — lift midtones by 12 to make strokes visually thicker.
    # This shifts the 0.5 boundary (edge detection threshold) outward, so glyphs
    # render with more "ink" and better match the weight of original Latin glyphs.
    sdf_float = sdf_uint8.astype(np.float32)
    # Only boost pixels that are already inside or near boundary (> 40), avoid lifting background
    mask = sdf_float > 40
    sdf_float[mask] = sdf_float[mask] + 12
    sdf_uint8 = sdf_float.clip(0, 255).astype(np.uint8)

    return {
        'bitmap': sdf_uint8,
        'width': sdf_uint8.shape[1],
        'height': sdf_uint8.shape[0],
        'bearingX': face.glyph.bitmap_left,
        'bearingY': face.glyph.bitmap_top,
        'advance': face.glyph.advance.x / 64.0,
    }


def main():
    print("=" * 60)
    print("ADD CYRILLIC TO LiberationSans SDF (v7 - lowercase baseline fix)")
    print("=" * 60)

    ttf_path = str(PROJECT / "fonts" / "LiberationSans-Regular.ttf")

    # === STEP 1: Read ORIGINAL atlas from backup ===
    print("\n--- Reading original atlas from backup ---")
    orig_atlas, orig_w, orig_h = read_original_atlas()
    if orig_atlas is None:
        print("ERROR: Cannot read original atlas")
        return

    # === STEP 2: Read font metadata from backup ===
    print("\n--- Reading font metadata from backup ---")
    backup_env = UnityPy.load(str(BACKUP / "resources.assets"))
    font_raw_orig = None
    for obj in backup_env.objects:
        if obj.path_id == FONT_PATH_ID:
            font_raw_orig = bytearray(obj.get_raw_data())
            break

    glyph_count = struct.unpack_from('<I', font_raw_orig, GLYPH_COUNT_OFFSET)[0]
    print(f"  Original glyphs: {glyph_count}")

    # Parse existing glyphs
    existing = {}
    for i in range(glyph_count):
        off = GLYPH_TABLE_OFFSET + i * 36
        cp = struct.unpack_from('<I', font_raw_orig, off)[0]
        floats = struct.unpack_from('<8f', font_raw_orig, off + 4)
        existing[cp] = {
            'atlas_x': floats[0], 'atlas_y': floats[1],
            'width': floats[2], 'height': floats[3],
            'xOffset': floats[4], 'yOffset': floats[5],
            'xAdvance': floats[6], 'scale': floats[7],
        }

    ref_A = existing[65]
    print(f"  Ref 'A': w={ref_A['width']:.1f} h={ref_A['height']:.1f} xAdv={ref_A['xAdvance']:.1f}")

    needed = [c for c in CYRILLIC_CHARS if ord(c) not in existing]
    print(f"  Cyrillic to add: {len(needed)}")

    # === STEP 3: Analyze original SDF characteristics ===
    print("\n--- Analyzing original SDF characteristics ---")
    sample_maxes = []
    for cp in [65, 66, 67, 68, 69, 72, 77, 79]:  # A,B,C,D,E,H,M,O
        g = existing.get(cp)
        if g:
            x, y, w, h = int(g['atlas_x']), int(g['atlas_y']), int(g['width']+1), int(g['height']+1)
            if y+h <= orig_h and x+w <= orig_w:
                region = orig_atlas[y:y+h, x:x+w]
                mx = int(region.max())
                sample_maxes.append(mx)
                if cp in [65, 79]:
                    print(f"  '{chr(cp)}' at ({x},{y}) {w}x{h}: max={mx}")
    avg_max = np.mean(sample_maxes) if sample_maxes else 175
    print(f"  Average max pixel value: {avg_max:.0f}")

    # === STEP 4: Generate Cyrillic SDF glyphs ===
    print("\n--- Generating Cyrillic SDF glyphs ---")
    face = freetype.Face(ttf_path)

    # Calibrated parameters (see script header for derivation):
    #   render_size=71 → 'A' bitmap is 48x49; with spread=5 the padded SDF is 58x59.
    #   Atlas 'A' height = 59.16, so the height matches exactly.
    #   Width is 58 vs 57.03 in atlas — 1px extra, acceptable.
    #   v6: render_size stays at 71 for correct baseline alignment with Latin.
    #   Thickness is controlled via brightness boost in generate_sdf_glyph(), not render_size.
    render_size = RENDER_SIZE
    spread = SDF_SPREAD

    face.set_pixel_sizes(0, render_size)
    face.load_char('A', freetype.FT_LOAD_RENDER)
    cal_A_bm = face.glyph.bitmap
    cal_A_w_padded = cal_A_bm.width + 2 * spread
    cal_A_h_padded = cal_A_bm.rows + 2 * spread
    print(f"  'A' at size {render_size}: bitmap={cal_A_bm.width}x{cal_A_bm.rows}, "
          f"padded(spread={spread})={cal_A_w_padded}x{cal_A_h_padded} "
          f"(atlas: {ref_A['width']:.1f}x{ref_A['height']:.1f})")

    # Calibrate metrics: derive scaling factors from 'A' so Cyrillic
    # advance/offset values will be consistent with the original Latin glyphs.
    cal_A_advance = face.glyph.advance.x / 64.0
    adv_scale = ref_A['xAdvance'] / cal_A_advance if cal_A_advance > 0 else 1.0

    # xOffset in TMP = bearingX + spread_correction (spread makes left edge move left by spread)
    # yOffset in TMP = bearingY + spread_correction (spread makes top edge move up by spread)
    # We solve corrections from the known 'A' reference values:
    cal_xOff_correction = ref_A['xOffset'] - (face.glyph.bitmap_left - spread)
    cal_yOff_correction = ref_A['yOffset'] - (face.glyph.bitmap_top + spread)
    print(f"  adv_scale={adv_scale:.4f}, x_corr={cal_xOff_correction:.2f}, y_corr={cal_yOff_correction:.2f}")

    # Verify calibration with lowercase 'a' (independent reference)
    ref_a = existing[97]
    face.load_char('a', freetype.FT_LOAD_RENDER)
    latin_a_bearingY = face.glyph.bitmap_top
    cal_a_xOff = face.glyph.bitmap_left - spread + cal_xOff_correction
    cal_a_yOff = latin_a_bearingY + spread + cal_yOff_correction
    cal_a_adv = (face.glyph.advance.x / 64.0) * adv_scale
    print(f"  Verify 'a': xOff={cal_a_xOff:.1f} (ref {ref_a['xOffset']:.1f}), "
          f"yOff={cal_a_yOff:.1f} (ref {ref_a['yOffset']:.1f}), "
          f"xAdv={cal_a_adv:.1f} (ref {ref_a['xAdvance']:.1f})")

    # v7 BASELINE FIX: Cyrillic lowercase has different bearingY in freetype than Latin.
    # Calibrating yOffset from uppercase 'A' works perfectly for uppercase (identical glyphs),
    # but lowercase Cyrillic gets ~2.91 units too high, causing punctuation misalignment.
    # Compute per-case correction by comparing Latin 'a' with Cyrillic 'а'.
    face.set_pixel_sizes(0, render_size)
    face.load_char('\u0430', freetype.FT_LOAD_RENDER)  # Cyrillic 'а'
    cyrillic_a_bearingY = face.glyph.bitmap_top
    cyrillic_a_computed_yOff = cyrillic_a_bearingY + spread + cal_yOff_correction
    lc_yOff_delta = ref_a['yOffset'] - cyrillic_a_computed_yOff
    print(f"  Lowercase baseline fix: Latin 'a' yOff={ref_a['yOffset']:.2f}, "
          f"Cyrillic 'а' computed={cyrillic_a_computed_yOff:.2f}, delta={lc_yOff_delta:.2f}")

    # target_max from analysis of original atlas: avg max of Latin A-Z ≈ 181-182
    target_sdf_max = int(avg_max)
    print(f"  SDF target_max={target_sdf_max} (avg max of original Latin A-Z glyphs)")

    # Generate all Cyrillic glyphs with proper SDF (spread=5)
    new_glyphs = []
    for char in needed:
        glyph = generate_sdf_glyph(face, char, render_size, spread, target_sdf_max)
        if glyph:
            new_glyphs.append((char, glyph))

    print(f"  Generated {len(new_glyphs)} glyphs")

    # === STEP 5: Create expanded atlas preserving original data ===
    print("\n--- Building atlas ---")
    new_atlas_h = orig_h * 2
    new_atlas = np.zeros((new_atlas_h, orig_w), dtype=np.uint8)
    # Copy ORIGINAL atlas data byte-for-byte
    new_atlas[:orig_h, :] = orig_atlas
    print(f"  Copied original {orig_w}x{orig_h} to top half")

    # Verify copy
    for cp in [65, 79]:  # A, O
        g = existing[cp]
        x, y, w, h = int(g['atlas_x']), int(g['atlas_y']), int(g['width']+1), int(g['height']+1)
        region = new_atlas[y:y+h, x:x+w]
        print(f"  Verify copy '{chr(cp)}': max={region.max()}, nonzero={np.count_nonzero(region)}")

    # Pack new Cyrillic glyphs into bottom half
    padding = 2
    cur_x = padding
    cur_y = orig_h + padding
    row_height = 0
    positions = []

    for char, glyph in new_glyphs:
        gw, gh = glyph['width'], glyph['height']
        if cur_x + gw + padding > orig_w:
            cur_x = padding
            cur_y += row_height + padding
            row_height = 0
        positions.append((cur_x, cur_y))
        cur_x += gw + padding
        row_height = max(row_height, gh)

    # Write Cyrillic glyphs to atlas
    for (char, glyph), (px, py) in zip(new_glyphs, positions):
        new_atlas[py:py + glyph['height'], px:px + glyph['width']] = glyph['bitmap']

    print(f"  Cyrillic packed: last row y={cur_y + row_height}")
    Image.fromarray(new_atlas, 'L').save(str(PROJECT / "fonts" / "liberation_cyrillic_atlas_v3.png"))

    # Verify Cyrillic data
    sample_char, sample_glyph = new_glyphs[0]
    sx, sy = positions[0]
    region = new_atlas[sy:sy+sample_glyph['height'], sx:sx+sample_glyph['width']]
    print(f"  Verify Cyrillic '{sample_char}': max={region.max()}, nonzero={np.count_nonzero(region)}")

    # === STEP 6: Build glyph entries ===
    new_entries = b''
    for (char, glyph), (px, py) in zip(new_glyphs, positions):
        face.set_pixel_sizes(0, render_size)
        face.load_char(char, freetype.FT_LOAD_RENDER)

        xOffset = face.glyph.bitmap_left - spread + cal_xOff_correction
        yOffset = face.glyph.bitmap_top + spread + cal_yOff_correction
        xAdvance = (face.glyph.advance.x / 64.0) * adv_scale

        # v7: Apply lowercase baseline correction so Cyrillic lowercase
        # sits at the same baseline as Latin lowercase and punctuation.
        cp = ord(char)
        is_lowercase = (0x0430 <= cp <= 0x044F) or cp == 0x0451  # а-я, ё
        if is_lowercase:
            yOffset += lc_yOff_delta

        new_entries += struct.pack('<I', cp)
        new_entries += struct.pack('<8f',
            float(px), float(py),
            float(glyph['width']), float(glyph['height']),
            xOffset, yOffset, xAdvance, 1.0)

    # Splice into font raw data (use ORIGINAL font data as base)
    insert_point = GLYPH_TABLE_OFFSET + glyph_count * 36
    new_total = glyph_count + len(new_glyphs)

    new_raw = bytearray()
    new_raw += font_raw_orig[:GLYPH_COUNT_OFFSET]
    new_raw += struct.pack('<I', new_total)
    new_raw += font_raw_orig[GLYPH_COUNT_OFFSET + 4:insert_point]
    new_raw += new_entries
    new_raw += font_raw_orig[insert_point:]

    struct.pack_into('<f', new_raw, ATLAS_HEIGHT_OFFSET, float(new_atlas_h))
    struct.pack_into('<I', new_raw, 104, new_total)

    print(f"\n  Font: {len(font_raw_orig)} -> {len(new_raw)} bytes, glyphs: {glyph_count} -> {new_total}")

    # === STEP 7: Apply to game's resources.assets ===
    print("\n--- Applying to resources.assets ---")
    # Load from BACKUP (original, unmodified) — never chain UnityPy saves!
    env = UnityPy.load(str(PROJECT / "backup" / "resources.assets"))

    for obj in env.objects:
        if obj.path_id == FONT_PATH_ID:
            obj.set_raw_data(bytes(new_raw))
        elif obj.path_id == ATLAS_PATH_ID:
            tex = obj.read()
            # Create RGBA from grayscale (Alpha8 format)
            rgba = Image.new('RGBA', (orig_w, new_atlas_h), (255, 255, 255, 0))
            gray = Image.fromarray(new_atlas, 'L')
            r, g, b, a = rgba.split()
            rgba = Image.merge('RGBA', (r, g, b, gray))
            tex.m_Width = orig_w
            tex.m_Height = new_atlas_h
            tex.image = rgba
            tex.save()

    # === STEP 7.5: Update _TextureHeight in LiberationSans SDF materials ===
    # The TMP SDF shader uses _TextureHeight for gradient scale calculations.
    # When the atlas height changes, materials must be updated to match,
    # otherwise SDF rendering (especially for small glyphs like periods/commas)
    # will have incorrect edge detection and anti-aliasing.
    print("\n--- Updating material _TextureHeight ---")
    mat_updated = 0
    for obj in env.objects:
        if obj.type.name == 'Material' and obj.path_id in LIBERATION_MATERIAL_IDS:
            mat = obj.read()
            mat_name = getattr(mat, 'm_Name', '?')
            if hasattr(mat, 'm_SavedProperties') and hasattr(mat.m_SavedProperties, 'm_Floats'):
                for i, fp in enumerate(mat.m_SavedProperties.m_Floats):
                    key = fp[0] if isinstance(fp, (list, tuple)) else getattr(fp, 'first', '?')
                    val = fp[1] if isinstance(fp, (list, tuple)) else getattr(fp, 'second', 0)
                    if key == '_TextureHeight' and val != float(new_atlas_h):
                        if isinstance(fp, (list, tuple)):
                            mat.m_SavedProperties.m_Floats[i] = (key, float(new_atlas_h))
                        else:
                            fp.second = float(new_atlas_h)
                        print(f"  {mat_name} (id={obj.path_id}): _TextureHeight {val:.0f} -> {new_atlas_h}")
                        mat_updated += 1
                mat.save()
    print(f"  Updated {mat_updated} materials")

    out_path = PROJECT / "patches" / "resources.assets"
    with open(out_path, 'wb') as f:
        f.write(env.file.save())

    print(f"  Saved: {out_path} ({os.path.getsize(str(out_path))} bytes)")

    # === STEP 8: Verify ===
    print("\n--- Verification ---")
    env2 = UnityPy.load(str(out_path))

    # Verify font data
    for obj in env2.objects:
        if obj.path_id == FONT_PATH_ID:
            raw = obj.get_raw_data()
            gc = struct.unpack_from('<I', raw, GLYPH_COUNT_OFFSET)[0]
            print(f"  Glyph count: {gc}")
            for i in range(gc):
                off = GLYPH_TABLE_OFFSET + i * 36
                cp = struct.unpack_from('<I', raw, off)[0]
                floats = struct.unpack_from('<8f', raw, off + 4)
                if cp in [65, 0x410]:
                    print(f"  {chr(cp)} (U+{cp:04X}): w={floats[2]:.1f} h={floats[3]:.1f} "
                          f"xOff={floats[4]:.1f} yOff={floats[5]:.1f} xAdv={floats[6]:.1f}")
            break

    # Verify atlas: compare Latin and Cyrillic SDF pixel values
    for obj in env2.objects:
        if obj.path_id == ATLAS_PATH_ID:
            tex = obj.read()
            img = tex.image
            arr = np.array(img)
            if arr.ndim == 3:
                arr = arr[:, :, -1]
            print(f"  Atlas: {tex.m_Width}x{tex.m_Height}")

            # Latin 'A' (preserved from original)
            g_A = existing[65]
            x, y, w, h = int(g_A['atlas_x']), int(g_A['atlas_y']), int(g_A['width']+1), int(g_A['height']+1)
            region_A = arr[y:y+h, x:x+w]
            latin_A_max = int(region_A.max())
            print(f"  Latin  'A' (U+0041) at ({x},{y}) {w}x{h}: max={latin_A_max}, nonzero={np.count_nonzero(region_A)}")

            # Find Cyrillic 'А' (U+0410) in new glyph list to get its atlas position
            cyr_A_max = None
            for (ch, glyph), (px, py) in zip(new_glyphs, positions):
                if ord(ch) == 0x410:  # Cyrillic А
                    cyr_region = arr[py:py+glyph['height'], px:px+glyph['width']]
                    cyr_A_max = int(cyr_region.max())
                    print(f"  Cyrillic 'А' (U+0410) at ({px},{py}) {glyph['width']}x{glyph['height']}: "
                          f"max={cyr_A_max}, nonzero={np.count_nonzero(cyr_region)}")
                    break

            if cyr_A_max is not None:
                diff = abs(latin_A_max - cyr_A_max)
                print(f"\n  *** SDF max comparison: Latin A={latin_A_max}, Cyrillic А={cyr_A_max}, diff={diff} ***")
                if diff <= 15:
                    print("  *** PASS: Cyrillic max pixel value closely matches Latin (diff <= 15) ***")
                else:
                    print(f"  *** WARN: Larger than expected diff ({diff}) — check normalization ***")

            # Also verify № if present
            for (ch, glyph), (px, py) in zip(new_glyphs, positions):
                if ord(ch) == 0x2116:  # №
                    nr_region = arr[py:py+glyph['height'], px:px+glyph['width']]
                    print(f"  '№' (U+2116) at ({px},{py}) {glyph['width']}x{glyph['height']}: "
                          f"max={int(nr_region.max())}, nonzero={np.count_nonzero(nr_region)}")
                    break
            break

    print("\nDone!")


if __name__ == "__main__":
    main()
