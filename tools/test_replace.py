#!/usr/bin/env python3
"""
Тест: замена строк в MonoBehaviour по байтовому смещению.
Проверяем что Unity принимает файл с заменённой строкой.
"""
import os, sys, struct, shutil
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
from pathlib import Path

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")


def find_string_in_asset(asset_path, search_text):
    """Find a specific string in an asset file by raw byte scanning."""
    with open(asset_path, "rb") as f:
        data = f.read()

    encoded = search_text.encode("utf-8")
    # Unity format: 4-byte length prefix + string bytes + padding to 4-byte boundary
    length_prefix = struct.pack("<I", len(encoded))
    needle = length_prefix + encoded

    positions = []
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1

    return positions, data


def replace_string_in_asset(data, offset, old_text, new_text):
    """
    Replace a length-prefixed string in binary data.
    Unity strings: [4-byte LE length][utf-8 bytes][padding to 4-byte alignment]
    """
    old_encoded = old_text.encode("utf-8")
    new_encoded = new_text.encode("utf-8")

    old_len = len(old_encoded)
    new_len = len(new_encoded)

    # Calculate old padding
    old_padding = (4 - (old_len % 4)) % 4
    old_total = 4 + old_len + old_padding

    # Calculate new padding
    new_padding = (4 - (new_len % 4)) % 4
    new_total = 4 + new_len + new_padding

    # Verify the old string is at this offset
    stored_len = struct.unpack_from("<I", data, offset)[0]
    if stored_len != old_len:
        print(f"  WARNING: Expected length {old_len} but found {stored_len} at offset {offset}")
        return None

    stored_text = data[offset+4:offset+4+old_len].decode("utf-8")
    if stored_text != old_text:
        print(f"  WARNING: Text mismatch at offset {offset}")
        return None

    if old_total == new_total:
        # Same total size - simple replacement
        new_data = bytearray(data)
        struct.pack_into("<I", new_data, offset, new_len)
        new_data[offset+4:offset+4+old_len] = new_encoded + b'\x00' * (old_len - new_len + old_padding)
        # Actually need to be more careful
        new_data = bytearray(data)
        struct.pack_into("<I", new_data, offset, new_len)
        new_data[offset+4:offset+4+new_len] = new_encoded
        # Fill remaining with zeros
        for i in range(new_len, old_len + old_padding):
            if offset + 4 + i < len(new_data):
                new_data[offset+4+i] = 0
        # Add new padding
        for i in range(new_len, new_len + new_padding):
            if offset + 4 + i < len(new_data):
                new_data[offset+4+i] = 0
        return bytes(new_data)
    else:
        # Different total size - need to splice
        before = data[:offset]
        after = data[offset + old_total:]
        new_prefix = struct.pack("<I", new_len)
        new_chunk = new_prefix + new_encoded + b'\x00' * new_padding
        return before + new_chunk + after


def test_smartloc_replacement():
    """Test replacing a SmartLocalization TextAsset string."""
    res_path = GAME_DATA / "resources.assets"

    # Look for "New Game" in the file
    search = "New Game"
    positions, data = find_string_in_asset(res_path, search)
    print(f"\nFound '{search}' at {len(positions)} positions: {positions}")

    # Look for "Menu"
    search2 = "Menu"
    positions2, _ = find_string_in_asset(res_path, search2)
    print(f"Found '{search2}' at {len(positions2)} positions: {positions2}")

    # Look for "Quit"
    search3 = "Quit"
    positions3, _ = find_string_in_asset(res_path, search3)
    print(f"Found '{search3}' at {len(positions3)} positions: {positions3}")


def test_textasset_via_unitypy():
    """Test modifying TextAsset via UnityPy."""
    res_path = GAME_DATA / "resources.assets"
    test_output = PROJECT / "patches" / "resources_test.assets"

    print("\n--- Testing UnityPy TextAsset modification ---")
    env = UnityPy.load(str(res_path))

    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            name = data.m_Name
            if name == "Language.en":
                raw = data.m_Script
                if isinstance(raw, bytes):
                    text = raw.decode("utf-8")
                else:
                    text = str(raw)

                print(f"Found Language.en TextAsset (path_id={obj.path_id})")
                print(f"  Original size: {len(text)} chars")

                # Replace a few values
                text_new = text.replace(
                    "<value>New Game</value>",
                    "<value>Новая игра</value>"
                ).replace(
                    "<value>Quit</value>",
                    "<value>Выход</value>"
                ).replace(
                    "<value>Menu</value>",
                    "<value>Меню</value>"
                ).replace(
                    "<value>Save</value>",
                    "<value>Сохранить</value>"
                ).replace(
                    "<value>Load</value>",
                    "<value>Загрузить</value>"
                )

                print(f"  Modified size: {len(text_new)} chars")

                # Apply modification
                data.m_Script = text_new.encode("utf-8")
                data.save()

                print("  TextAsset saved in memory")
                break

    # Save modified file
    with open(test_output, "wb") as f:
        f.write(env.file.save())

    print(f"  Modified file saved: {test_output}")
    print(f"  Original size: {res_path.stat().st_size}")
    print(f"  Modified size: {test_output.stat().st_size}")

    # Verify by re-reading
    env2 = UnityPy.load(str(test_output))
    for obj in env2.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            if data.m_Name == "Language.en":
                raw = data.m_Script
                text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                if "Новая игра" in text:
                    print("  VERIFICATION: Russian text found in modified file!")
                else:
                    print("  VERIFICATION FAILED: Russian text not found")
                break


def test_raw_monobehaviour_replacement():
    """Test replacing a string in a MonoBehaviour via raw byte editing."""
    res_path = GAME_DATA / "resources.assets"

    # Find a known string
    search = "WE PROTECT THE NATION."
    positions, data = find_string_in_asset(res_path, search)
    print(f"\nFound '{search}' at {len(positions)} positions: {positions}")

    if positions:
        # Test replacement without actually saving
        replacement = "МЫ ЗАЩИЩАЕМ НАЦИЮ."
        result = replace_string_in_asset(data, positions[0], search, replacement)
        if result:
            print(f"  Raw replacement successful")
            print(f"  Size change: {len(data)} -> {len(result)} ({len(result) - len(data):+d} bytes)")

            # Verify
            verify_positions, _ = find_string_in_asset_bytes(result, replacement)
            if verify_positions:
                print(f"  Verification: '{replacement}' found at positions {verify_positions}")
            else:
                print(f"  Verification FAILED: replacement text not found")


def find_string_in_asset_bytes(data, search_text):
    """Find string in raw bytes."""
    encoded = search_text.encode("utf-8")
    length_prefix = struct.pack("<I", len(encoded))
    needle = length_prefix + encoded

    positions = []
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1

    return positions, data


def main():
    print("=" * 60)
    print("REPLACEMENT TEST")
    print("=" * 60)

    test_smartloc_replacement()
    test_textasset_via_unitypy()
    test_raw_monobehaviour_replacement()


if __name__ == "__main__":
    main()
