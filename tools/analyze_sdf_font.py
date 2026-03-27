#!/usr/bin/env python3
"""
Analyze TMP SDF font asset structure in sharedassets3.assets.
Understand the binary layout to add Cyrillic glyphs.
"""
import os, sys, struct, json
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
from pathlib import Path

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")


def analyze_sdf_font(env, path_id):
    """Analyze the binary structure of a TMP SDF font MonoBehaviour."""
    for obj in env.objects:
        if obj.path_id != path_id:
            continue

        raw = obj.get_raw_data()
        print(f"=== SDF Font path_id={path_id} ({len(raw)} bytes) ===")

        # Dump first 200 bytes as hex + ASCII
        print("\nFirst 300 bytes (hex dump):")
        for i in range(0, min(300, len(raw)), 16):
            hex_part = ' '.join(f'{b:02x}' for b in raw[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw[i:i+16])
            print(f"  {i:04x}: {hex_part:<48} {ascii_part}")

        # Find string fields
        print("\nString fields found:")
        i = 0
        while i < len(raw) - 4:
            str_len = struct.unpack_from('<I', raw, i)[0]
            if 1 <= str_len <= 200 and i + 4 + str_len <= len(raw):
                try:
                    s = raw[i+4:i+4+str_len].decode('utf-8')
                    if s.isprintable() and len(s) >= 1:
                        padding = (4 - (str_len % 4)) % 4
                        print(f"  offset={i}: \"{s}\" ({str_len} bytes, pad={padding})")
                        i += 4 + str_len + padding
                        continue
                except:
                    pass
            i += 1

        # Look for float arrays (font metrics typically have lots of floats)
        print("\nSearching for glyph table patterns...")

        # In TMP fonts, the glyph table is an array of structs
        # Each glyph has: index, metrics (x, y, w, h as floats), scale
        # Let's look for array length markers followed by sequential data

        # Find array markers (4-byte int that could be array length)
        for i in range(0, len(raw) - 8, 4):
            arr_len = struct.unpack_from('<I', raw, i)[0]
            if 50 <= arr_len <= 500:  # Reasonable glyph count
                # Check if the next values look like glyph data
                # A glyph entry might be: uint index, float x, float y, float w, float h, ...
                # Typical glyph struct is ~40-60 bytes
                possible_entry_sizes = [28, 32, 36, 40, 44, 48, 52, 56, 60]
                for entry_size in possible_entry_sizes:
                    total = arr_len * entry_size
                    if i + 4 + total <= len(raw):
                        # Check first few entries for reasonable values
                        valid = True
                        for j in range(min(3, arr_len)):
                            entry_start = i + 4 + j * entry_size
                            # First field might be a small uint (glyph index)
                            val0 = struct.unpack_from('<I', raw, entry_start)[0]
                            if val0 > 10000:
                                valid = False
                                break
                        if valid:
                            print(f"  Potential array at offset={i}: length={arr_len}, entry_size={entry_size}")
                            # Show first 3 entries
                            for j in range(min(3, arr_len)):
                                entry_start = i + 4 + j * entry_size
                                entry_bytes = raw[entry_start:entry_start+entry_size]
                                ints = [struct.unpack_from('<I', entry_bytes, k)[0] for k in range(0, min(20, entry_size), 4)]
                                floats = [struct.unpack_from('<f', entry_bytes, k)[0] for k in range(0, min(20, entry_size), 4)]
                                print(f"    entry[{j}] ints: {ints[:5]}")
                                print(f"    entry[{j}] floats: {[f'{f:.2f}' for f in floats[:5]]}")

        # Also check for Texture2D references (atlas texture)
        print("\nLooking for texture references (PPtr)...")
        # PPtr format: int m_FileID, long m_PathID
        for i in range(0, len(raw) - 12, 4):
            file_id = struct.unpack_from('<i', raw, i)[0]
            path_id_ref = struct.unpack_from('<q', raw, i+4)[0]
            if file_id == 0 and 100 <= path_id_ref <= 10000:
                # Could be a reference to a texture in the same file
                print(f"  Possible PPtr at offset={i}: fileID={file_id}, pathID={path_id_ref}")

        break


def list_textures(env):
    """List all Texture2D assets that might be font atlases."""
    print("\n=== Texture2D assets (possible font atlases) ===")
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            data = obj.read()
            name = data.m_Name
            w = data.m_Width
            h = data.m_Height
            fmt = data.m_TextureFormat
            if "ubuntu" in name.lower() or "font" in name.lower() or "sdf" in name.lower():
                print(f"  path_id={obj.path_id}: {name} ({w}x{h}, format={fmt})")


def main():
    env = UnityPy.load(str(GAME_DATA / "sharedassets3.assets"))

    # List font-related textures
    list_textures(env)

    # Analyze Ubuntu-Bold SDF (path_id=2411)
    print()
    analyze_sdf_font(env, 2411)


if __name__ == "__main__":
    main()
