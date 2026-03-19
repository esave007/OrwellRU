#!/usr/bin/env python3
"""
Apply SmartLocalization translation to resources.assets.
Replaces English values in the Language.en TextAsset XML with Russian translations.
Also replaces in Language (master) and Language.en.de (delta).
"""
import os, sys, json
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
from pathlib import Path

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")


def apply_translations(env, asset_name, translations):
    """Replace translation values in a SmartLocalization TextAsset."""
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        if data.m_Name != asset_name:
            continue

        text = data.m_Script
        modified = False

        for key, russian in translations.items():
            if not russian:
                continue  # Skip empty values

            # Find the XML pattern: <data name="KEY" ...><value>ENGLISH</value></data>
            # We need to find the value within the correct data element
            import re
            pattern = rf'(<data name="{re.escape(key)}"[^>]*>\s*<value>)(.*?)(</value>)'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                old_value = match.group(2)
                if old_value and old_value != russian:
                    text = text[:match.start(2)] + russian + text[match.end(2):]
                    modified = True
                    print(f"  {key}: '{old_value}' -> '{russian}'")

        if modified:
            data.m_Script = text
            data.save()
            return True
    return False


def main():
    print("=" * 60)
    print("APPLYING SmartLocalization TRANSLATION")
    print("=" * 60)

    # Load translations
    with open(PROJECT / "translated" / "smartloc" / "smartloc_ru.json", encoding="utf-8") as f:
        translations = json.load(f)

    print(f"Loaded {len(translations)} translation entries")

    # Load resources.assets
    env = UnityPy.load(str(GAME_DATA / "resources.assets"))

    # Apply to Language.en (main English)
    print("\n--- Language.en ---")
    ok1 = apply_translations(env, "Language.en", translations)
    print(f"  Applied: {ok1}")

    # Apply to Language (master, same as en)
    print("\n--- Language (master) ---")
    ok2 = apply_translations(env, "Language", translations)
    print(f"  Applied: {ok2}")

    # Save
    out_path = PROJECT / "patches" / "resources.assets"
    with open(out_path, "wb") as f:
        f.write(env.file.save())

    orig_size = (GAME_DATA / "resources.assets").stat().st_size
    new_size = out_path.stat().st_size
    print(f"\nSaved: {out_path}")
    print(f"Original: {orig_size} bytes")
    print(f"Modified: {new_size} bytes ({new_size - orig_size:+d})")

    # Verify
    print("\n--- Verification ---")
    env2 = UnityPy.load(str(out_path))
    for obj in env2.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            if data.m_Name == "Language.en":
                text = data.m_Script
                # Check a few translations
                checks = [
                    ("Новая игра", "MAINMENU_NEW_GAME"),
                    ("Меню", "INGAMEMENU_TITLE"),
                    ("Сохранить", "INGAMEMENU_SAVE_GAME"),
                    ("Загрузить", "INGAMEMENU_LOAD_GAME"),
                    ("Профиль", "PROFILER_TAB_PROFILE"),
                    ("Связи", "PROFILER_TAB_RELATIONSHIPS"),
                    ("Закладки", "READER_TAB_BOOKMARKS"),
                ]
                all_ok = True
                for ru_text, key in checks:
                    if ru_text in text:
                        print(f"  {key}: OK ({ru_text})")
                    else:
                        print(f"  {key}: FAIL ('{ru_text}' not found)")
                        all_ok = False
                if all_ok:
                    print("\n  ALL VERIFICATIONS PASSED!")
                break

    obj_count_orig = sum(1 for _ in UnityPy.load(str(GAME_DATA / "resources.assets")).objects)
    obj_count_new = sum(1 for _ in env2.objects)
    print(f"\n  Object count: original={obj_count_orig}, modified={obj_count_new}")


if __name__ == "__main__":
    main()
