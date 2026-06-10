#!/usr/bin/env python3
"""
Diagnostic script: compare glyph metrics (yOffset, xOffset, xAdvance)
between Latin, Latin punctuation, and Cyrillic glyphs in the patched
resources.assets font (path_id=5003).

Purpose: investigate why Latin punctuation renders slightly ABOVE
Cyrillic text baseline in the game.
"""
import os, sys, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
from pathlib import Path

PATCHED = Path(r"C:\Projects\OrwellRU\patches\resources.assets")
FONT_PATH_ID = 5003
GLYPH_COUNT_OFFSET = 188
GLYPH_TABLE_OFFSET = 192

# Glyph groups to compare
GROUPS = {
    "Latin uppercase": {
        65: 'A', 66: 'B', 77: 'M', 72: 'H',
    },
    "Latin lowercase": {
        97: 'a', 98: 'b', 103: 'g', 112: 'p',
    },
    "Latin punctuation": {
        46: '.', 44: ',', 59: ';', 58: ':', 33: '!', 63: '?',
        45: '-', 39: "'", 34: '"', 40: '(', 41: ')',
    },
    "Cyrillic uppercase": {
        0x410: '\u0410', 0x411: '\u0411', 0x41C: '\u041C', 0x41D: '\u041D',
    },
    "Cyrillic lowercase": {
        0x430: '\u0430', 0x431: '\u0431', 0x433: '\u0433', 0x440: '\u0440',
    },
}


def main():
    print("=" * 80)
    print("FONT BASELINE DIAGNOSTIC — patched resources.assets")
    print(f"File: {PATCHED}")
    print(f"Size: {os.path.getsize(str(PATCHED)):,} bytes")
    print("=" * 80)

    env = UnityPy.load(str(PATCHED))

    font_raw = None
    for obj in env.objects:
        if obj.path_id == FONT_PATH_ID:
            font_raw = obj.get_raw_data()
            break

    if font_raw is None:
        print("ERROR: Font object (path_id=5003) not found!")
        return

    glyph_count = struct.unpack_from('<I', font_raw, GLYPH_COUNT_OFFSET)[0]
    print(f"\nTotal glyphs in font: {glyph_count}")

    # Parse all glyphs into dict
    glyphs = {}
    for i in range(glyph_count):
        off = GLYPH_TABLE_OFFSET + i * 36
        cp = struct.unpack_from('<I', font_raw, off)[0]
        floats = struct.unpack_from('<8f', font_raw, off + 4)
        glyphs[cp] = {
            'atlas_x': floats[0],
            'atlas_y': floats[1],
            'width': floats[2],
            'height': floats[3],
            'xOffset': floats[4],
            'yOffset': floats[5],
            'xAdvance': floats[6],
            'scale': floats[7],
        }

    # Print comparison table for each group
    header = f"{'Char':<6} {'CP':>6}  {'atlas_x':>8} {'atlas_y':>8} {'width':>7} {'height':>7} {'xOffset':>8} {'yOffset':>8} {'xAdvance':>9} {'scale':>6}"
    sep = "-" * len(header)

    for group_name, codepoints in GROUPS.items():
        print(f"\n--- {group_name} ---")
        print(header)
        print(sep)
        for cp, label in sorted(codepoints.items()):
            g = glyphs.get(cp)
            if g is None:
                print(f"{label:<6} U+{cp:04X}  *** NOT FOUND ***")
            else:
                print(f"{label:<6} U+{cp:04X}  {g['atlas_x']:8.2f} {g['atlas_y']:8.2f} "
                      f"{g['width']:7.2f} {g['height']:7.2f} "
                      f"{g['xOffset']:8.2f} {g['yOffset']:8.2f} "
                      f"{g['xAdvance']:9.2f} {g['scale']:6.2f}")

    # Baseline comparison
    print("\n" + "=" * 80)
    print("BASELINE COMPARISON")
    print("=" * 80)

    comparisons = [
        ("Latin 'A' vs Cyrillic '\u0410'", 65, 0x410),
        ("Latin 'a' vs Cyrillic '\u0430'", 97, 0x430),
        ("Latin 'B' vs Cyrillic '\u0411'", 66, 0x411),
        ("Latin 'M' vs Cyrillic '\u041C'", 77, 0x41C),
    ]

    print(f"\n{'Comparison':<35} {'yOff_L':>8} {'yOff_C':>8} {'diff_y':>8}  {'xOff_L':>8} {'xOff_C':>8} {'diff_x':>8}  {'xAdv_L':>8} {'xAdv_C':>8} {'diff_a':>8}")
    print("-" * 120)

    for label, cp_lat, cp_cyr in comparisons:
        gl = glyphs.get(cp_lat)
        gc = glyphs.get(cp_cyr)
        if gl and gc:
            dy = gc['yOffset'] - gl['yOffset']
            dx = gc['xOffset'] - gl['xOffset']
            da = gc['xAdvance'] - gl['xAdvance']
            print(f"{label:<35} {gl['yOffset']:8.2f} {gc['yOffset']:8.2f} {dy:+8.2f}  "
                  f"{gl['xOffset']:8.2f} {gc['xOffset']:8.2f} {dx:+8.2f}  "
                  f"{gl['xAdvance']:8.2f} {gc['xAdvance']:8.2f} {da:+8.2f}")
        else:
            print(f"{label:<35}  *** one or both glyphs missing ***")

    # Punctuation vs Cyrillic comparison
    print(f"\n{'Punctuation vs Cyrillic baseline (using yOffset of Cyrillic A = reference)':}")
    cyr_A = glyphs.get(0x410)
    lat_A = glyphs.get(65)
    if cyr_A and lat_A:
        # In TMP, the baseline is at yOffset - height (bottom of the glyph bounding box)
        # Actually yOffset is from baseline to top of glyph. So baseline_top = yOffset.
        # The glyph bottom = yOffset - height.
        print(f"\n  Latin 'A':    yOffset={lat_A['yOffset']:.2f}, height={lat_A['height']:.2f}, bottom={lat_A['yOffset'] - lat_A['height']:.2f}")
        print(f"  Cyrillic 'A': yOffset={cyr_A['yOffset']:.2f}, height={cyr_A['height']:.2f}, bottom={cyr_A['yOffset'] - cyr_A['height']:.2f}")
        print(f"  yOffset difference (Cyr - Lat): {cyr_A['yOffset'] - lat_A['yOffset']:+.2f}")
        print(f"  bottom difference  (Cyr - Lat): {(cyr_A['yOffset'] - cyr_A['height']) - (lat_A['yOffset'] - lat_A['height']):+.2f}")

    print(f"\n--- Punctuation detail ---")
    punct_cps = {46: '.', 44: ',', 59: ';', 58: ':', 33: '!', 63: '?', 45: '-'}
    ref_yoff = lat_A['yOffset'] if lat_A else 0
    cyr_ref_yoff = cyr_A['yOffset'] if cyr_A else 0

    print(f"\n  Reference: Latin A yOffset = {ref_yoff:.2f}, Cyrillic A yOffset = {cyr_ref_yoff:.2f}")
    print(f"  If Cyrillic has HIGHER yOffset, TMP places it higher -> punctuation (calibrated to Latin) appears lower relative to Cyrillic")
    print(f"  If Cyrillic has LOWER yOffset, punctuation appears higher relative to Cyrillic\n")

    print(f"  {'Char':<6} {'yOffset':>8} {'height':>8} {'top_above_baseline':>20} {'bottom_below_baseline':>22}")
    print(f"  {'-'*70}")
    # Show Latin A, Cyrillic A, then punctuation
    for cp, label in [(65, 'Lat A'), (0x410, 'Cyr A'), (97, 'Lat a'), (0x430, 'Cyr a')] + list(punct_cps.items()):
        if isinstance(label, int):
            label = chr(label)
        g = glyphs.get(cp if isinstance(cp, int) else ord(cp))
        if cp in punct_cps:
            g = glyphs.get(cp)
        if g:
            # yOffset = distance from baseline to top of glyph (positive = above baseline)
            top = g['yOffset']
            bottom = g['yOffset'] - g['height']
            print(f"  {label:<6} {g['yOffset']:8.2f} {g['height']:8.2f} {top:20.2f} {bottom:22.2f}")

    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    if lat_A and cyr_A:
        dy = cyr_A['yOffset'] - lat_A['yOffset']
        if abs(dy) > 0.5:
            print(f"\n  ** yOffset MISMATCH detected: Cyrillic A is {dy:+.2f} vs Latin A **")
            if dy > 0:
                print(f"  Cyrillic glyphs sit HIGHER than Latin by {dy:.2f} units.")
                print(f"  This means Latin punctuation (., , etc.) will appear ABOVE Cyrillic text")
                print(f"  because punctuation yOffset was calibrated for the Latin baseline.")
            else:
                print(f"  Cyrillic glyphs sit LOWER than Latin by {abs(dy):.2f} units.")
        else:
            print(f"\n  yOffset difference is small ({dy:+.2f}). The issue may be in:")
            print(f"  - Atlas glyph rendering (SDF bitmap position)")
            print(f"  - Punctuation height vs Cyrillic height difference")
            print(f"  - TMP line layout algorithm treating mixed scripts differently")

    print()


if __name__ == "__main__":
    main()
