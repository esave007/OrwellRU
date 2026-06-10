#!/usr/bin/env python3
"""
Test v2: Replace strings using raw binary approach.
UnityPy typetree save doesn't work for this game (Unity 5.6.3 without embedded typetree).
Use direct raw byte editing instead.
"""
import os, sys, struct, shutil, copy
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
from pathlib import Path

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")


def replace_in_textasset_raw(env, asset_name, replacements):
    """
    Replace strings in a TextAsset by modifying raw data directly.
    TextAsset format:
    - m_Name: aligned string
    - m_Script: byte array (4-byte length + data)
    """
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            if data.m_Name != asset_name:
                continue

            raw = data.m_Script
            if isinstance(raw, bytes):
                text = raw.decode("utf-8")
            else:
                text = str(raw)

            # Apply replacements
            modified = text
            for old, new in replacements.items():
                modified = modified.replace(old, new)

            if modified == text:
                print(f"  No changes needed for {asset_name}")
                return False

            # Write back as raw bytes
            new_bytes = modified.encode("utf-8")

            # Rebuild the raw data for this object
            # TextAsset binary layout:
            # [PPtr m_GameObject (12 bytes: m_FileID 4 + m_PathID 8)]
            # [string m_Name: 4-byte len + chars + align4]
            # [byte[] m_Script: 4-byte len + data]

            old_raw = obj.get_raw_data()

            # Find m_Script in the raw data by looking for the original text
            old_script_bytes = raw if isinstance(raw, bytes) else raw.encode("utf-8")
            old_script_len_bytes = struct.pack("<I", len(old_script_bytes))

            # Find the position of the script data
            script_pos = old_raw.find(old_script_len_bytes + old_script_bytes[:50])
            if script_pos == -1:
                print(f"  ERROR: Could not find script data in raw bytes for {asset_name}")
                return False

            print(f"  Found script data at offset {script_pos} in raw object data")

            # Replace
            old_script_total = 4 + len(old_script_bytes)
            new_script_data = struct.pack("<I", len(new_bytes)) + new_bytes

            new_raw = old_raw[:script_pos] + new_script_data + old_raw[script_pos + old_script_total:]

            # Set raw data back
            obj.set_raw_data(new_raw)
            print(f"  Replaced in {asset_name}: {len(old_script_bytes)} -> {len(new_bytes)} bytes")
            return True

    return False


def test_textasset_raw():
    """Test modifying Language.en TextAsset via raw byte editing."""
    res_path = GAME_DATA / "resources.assets"
    test_output = PROJECT / "patches" / "resources_test.assets"

    print("--- Testing raw TextAsset modification ---")
    env = UnityPy.load(str(res_path))

    replacements = {
        "<value>New Game</value>": "<value>Новая игра</value>",
        "<value>Quit</value>": "<value>Выход</value>",
        "<value>Menu</value>": "<value>Меню</value>",
    }

    success = replace_in_textasset_raw(env, "Language.en", replacements)
    if not success:
        print("  FAILED to replace in Language.en")
        return

    # Save
    with open(test_output, "wb") as f:
        f.write(env.file.save())

    print(f"\n  Saved: {test_output}")
    print(f"  Original: {res_path.stat().st_size} bytes")
    print(f"  Modified: {test_output.stat().st_size} bytes")

    # Verify
    env2 = UnityPy.load(str(test_output))
    for obj in env2.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            if data.m_Name == "Language.en":
                raw = data.m_Script
                text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                checks = {
                    "Новая игра": "Новая игра" in text,
                    "Выход": "Выход" in text,
                    "Меню": "Меню" in text,
                }
                for term, found in checks.items():
                    status = "OK" if found else "FAIL"
                    print(f"  Verify '{term}': {status}")
                break


def test_monobehaviour_raw():
    """Test modifying a MonoBehaviour string via raw binary editing."""
    res_path = GAME_DATA / "resources.assets"

    print("\n--- Testing raw MonoBehaviour modification ---")
    env = UnityPy.load(str(res_path))

    # Find a specific object with known text
    target_text = b"End of communication."
    target_len = struct.pack("<I", len(target_text))

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        raw = obj.get_raw_data()
        if target_len + target_text in raw:
            print(f"  Found target in MonoBehaviour path_id={obj.path_id}")

            pos = raw.find(target_len + target_text)
            # Build replacement
            new_text = "Связь завершена.".encode("utf-8")
            new_chunk = struct.pack("<I", len(new_text)) + new_text
            # Pad to match old size if needed
            old_total = 4 + len(target_text)
            old_padding = (4 - (len(target_text) % 4)) % 4
            new_padding = (4 - (len(new_text) % 4)) % 4

            # If sizes differ, we need to splice
            new_raw = raw[:pos] + new_chunk + b'\x00' * new_padding + raw[pos + old_total + old_padding:]

            size_diff = len(new_raw) - len(raw)
            print(f"  Original raw size: {len(raw)}, New: {len(new_raw)}, Diff: {size_diff:+d}")

            obj.set_raw_data(new_raw)

            # Save and verify
            test_output = PROJECT / "patches" / "resources_test_mono.assets"
            with open(test_output, "wb") as f:
                f.write(env.file.save())

            print(f"  Saved: {test_output}")

            # Verify
            new_target = "Связь завершена.".encode("utf-8")
            with open(test_output, "rb") as f:
                content = f.read()
            if new_target in content:
                print(f"  VERIFICATION OK: Russian text found in modified file")
            else:
                print(f"  VERIFICATION FAILED")

            # Try to reload with UnityPy
            try:
                env3 = UnityPy.load(str(test_output))
                obj_count = sum(1 for _ in env3.objects)
                print(f"  UnityPy can read modified file: {obj_count} objects")
            except Exception as e:
                print(f"  UnityPy ERROR reading modified file: {e}")

            break


def main():
    print("=" * 60)
    print("REPLACEMENT TEST v2 (raw binary)")
    print("=" * 60)

    test_textasset_raw()
    test_monobehaviour_raw()


if __name__ == "__main__":
    main()
