#!/usr/bin/env python3
"""
Mass translation pipeline for resources.assets MonoBehaviours.
1. Reads catalog of strings
2. Applies translations via UnityPy (set_raw_data + save)
3. Handles size changes correctly

Usage:
  python translate_and_apply.py [--apply]

Without --apply: generates translation template
With --apply: applies existing translations from translated/ folder
"""
import os, sys, struct, json, re
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
from pathlib import Path

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")


def find_string_in_raw(raw, text_bytes):
    """Find a length-prefixed string in raw MonoBehaviour data."""
    prefix = struct.pack('<I', len(text_bytes))
    needle = prefix + text_bytes
    positions = []
    start = 0
    while True:
        pos = raw.find(needle, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1
    return positions


def replace_string_in_raw(raw, offset, old_text, new_text):
    """Replace a length-prefixed string in raw data, handling size changes."""
    old_bytes = old_text.encode('utf-8')
    new_bytes = new_text.encode('utf-8')

    old_len = len(old_bytes)
    new_len = len(new_bytes)
    old_padding = (4 - (old_len % 4)) % 4
    new_padding = (4 - (new_len % 4)) % 4
    old_total = 4 + old_len + old_padding
    new_total = 4 + new_len + new_padding

    # Verify
    stored_len = struct.unpack_from('<I', raw, offset)[0]
    if stored_len != old_len:
        return None

    new_raw = (
        raw[:offset] +
        struct.pack('<I', new_len) +
        new_bytes +
        b'\x00' * new_padding +
        raw[offset + old_total:]
    )
    return new_raw


def apply_translations_to_resources(translations_file, output_path):
    """
    Apply translations from JSON file to resources.assets.
    translations_file: JSON with [{original, translation, path_id, offset}, ...]
    """
    with open(translations_file, 'r', encoding='utf-8') as f:
        translations = json.load(f)

    # Filter to only entries with translations
    to_apply = [t for t in translations if t.get('translation') and t['translation'] != t['original']]
    print(f"Translations to apply: {len(to_apply)} out of {len(translations)} total")

    if not to_apply:
        print("No translations to apply!")
        return

    # Group by path_id for efficient processing
    by_path_id = {}
    for t in to_apply:
        pid = t['path_id']
        if pid not in by_path_id:
            by_path_id[pid] = []
        by_path_id[pid].append(t)

    print(f"Objects to modify: {len(by_path_id)}")

    # Load resources.assets
    env = UnityPy.load(str(GAME_DATA / "resources.assets"))

    # Also apply SmartLocalization
    smartloc_path = PROJECT / "translated" / "smartloc" / "smartloc_ru.json"
    if smartloc_path.exists():
        with open(smartloc_path, 'r', encoding='utf-8') as f:
            smartloc = json.load(f)
        for obj in env.objects:
            if obj.type.name == 'TextAsset':
                data = obj.read()
                if data.m_Name in ('Language.en', 'Language'):
                    text = data.m_Script
                    for key, russian in smartloc.items():
                        if russian:
                            pattern = rf'(<data name="{re.escape(key)}"[^>]*>\s*<value>)(.*?)(</value>)'
                            text = re.sub(pattern, rf'\g<1>{russian}\3', text, flags=re.DOTALL)
                    data.m_Script = text
                    data.save()
        print("SmartLocalization applied")

    # Apply MonoBehaviour translations
    applied = 0
    failed = 0

    for obj in env.objects:
        if obj.type.name != 'MonoBehaviour':
            continue
        if obj.path_id not in by_path_id:
            continue

        raw = obj.get_raw_data()
        translations_for_obj = by_path_id[obj.path_id]

        # Sort by offset descending so replacements don't shift earlier offsets
        translations_for_obj.sort(key=lambda t: t['offset'], reverse=True)

        for t in translations_for_obj:
            orig = t['original']
            trans = t['translation']
            orig_bytes = orig.encode('utf-8')

            # Find the string in current raw data
            positions = find_string_in_raw(raw, orig_bytes)
            if not positions:
                # String might have already been replaced or offset changed
                failed += 1
                continue

            # Replace the first (or matching) occurrence
            pos = positions[0]
            new_raw = replace_string_in_raw(raw, pos, orig, trans)
            if new_raw:
                raw = new_raw
                applied += 1
            else:
                failed += 1

        obj.set_raw_data(raw)

    print(f"\nApplied: {applied}, Failed: {failed}")

    # Save
    with open(output_path, 'wb') as f:
        f.write(env.file.save())

    print(f"Saved: {output_path} ({os.path.getsize(str(output_path))} bytes)")

    # Verify object count
    env2 = UnityPy.load(str(output_path))
    count = sum(1 for _ in env2.objects)
    print(f"Objects: {count}")

    return applied


def generate_translation_template():
    """Generate a template file for manual/batch translation."""
    catalog_path = PROJECT / "originals" / "unique_strings.json"
    with open(catalog_path, 'r', encoding='utf-8') as f:
        strings = json.load(f)

    # Add translation field if not present
    for s in strings:
        if 'translation' not in s:
            s['translation'] = ""

    # Save as translation template
    out = PROJECT / "translated" / "translation_template.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(strings, f, ensure_ascii=False, indent=2)

    print(f"Template generated: {out}")
    print(f"Total strings: {len(strings)}")

    # Stats
    cats = {}
    for s in strings:
        cats[s['category']] = cats.get(s['category'], 0) + 1
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


def main():
    if '--apply' in sys.argv:
        # Apply translations
        trans_file = PROJECT / "translated" / "translation_template.json"
        if not trans_file.exists():
            print(f"Translation file not found: {trans_file}")
            return
        output = PROJECT / "patches" / "resources.assets"
        apply_translations_to_resources(str(trans_file), str(output))
    else:
        # Generate template
        generate_translation_template()


if __name__ == "__main__":
    main()
