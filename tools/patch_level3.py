#!/usr/bin/env python3
"""
Patch level3 with ALL translations.
Level3 = main game content (episodes 1-3): articles, chats, documents, profiles, UI.
"""
import os, sys, json, glob
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile, find_and_replace_strings

PROJECT = Path(r"C:\Projects\OrwellRU")
GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
BACKUP = PROJECT / "backup"


def load_translations():
    """Load ALL translation batches for level3."""
    translations = {}
    # Load all batch_level3_*.json files
    pattern = str(PROJECT / "translated" / "batch_level3_*.json")
    batch_files = sorted(glob.glob(pattern))
    for fpath in batch_files:
        fname = Path(fpath).name
        with open(fpath, 'r', encoding='utf-8') as f:
            batch = json.load(f)
        # Filter out empty translations
        filled = {k: v for k, v in batch.items() if v}
        translations.update(filled)
        print(f"  {fname}: {len(filled)}/{len(batch)} entries")
    print(f"  TOTAL: {len(translations)} translations")
    return translations


def main():
    print("=" * 60)
    print("LEVEL3 PATCHER: Main game content translations")
    print("=" * 60)

    print("\nLoading translations:")
    translations = load_translations()

    if not translations:
        print("\nNo translations found! Create batch_level3_*.json files first.")
        return

    # ALWAYS parse from BACKUP (original English)
    backup_path = BACKUP / "level3"
    print(f"\nParsing BACKUP {backup_path}...")
    usf = UnitySerializedFile(str(backup_path))
    print(f"  Objects: {len(usf.objects)}, File size: {usf.file_size}")

    replacements = {}
    total_replaced = 0

    # Apply text translations to ALL MonoBehaviour objects
    print("\nApplying translations to all MonoBehaviour objects:")
    for obj in usf.objects:
        if obj['type_index'] >= len(usf.types):
            continue
        class_id = usf.types[obj['type_index']]['class_id']
        if class_id != 114:  # MonoBehaviour only
            continue
        raw = usf.get_object_data(obj['path_id'])
        if not raw or len(raw) < 20:
            continue
        new_raw, count = find_and_replace_strings(raw, translations)
        if count > 0:
            replacements[obj['path_id']] = new_raw
            total_replaced += count

    print(f"\nText: {total_replaced} replacements in {len(replacements)} objects")

    # Rebuild
    output_path = PROJECT / "patches" / "level3"
    print(f"\nRebuilding {output_path}...")
    usf.rebuild_with_replacements(replacements, str(output_path))

    # Verify key translations
    print("\nVerification:")
    with open(output_path, 'rb') as f:
        data = f.read()
    checks = [
        "Мемориал Свободы",
        "Голос Народа",
        "главное меню",
        "Стеллиганский университет",
        "Рабан Вхарт",
        "Площадь Свободы",
        "Нации",
        "Паргес",
    ]
    ok = 0
    for c in checks:
        found = c.encode('utf-8') in data
        status = "ok" if found else "FAIL"
        if not found:
            print(f"  [{status}] {c}")
        else:
            ok += 1
    print(f"  {ok}/{len(checks)} verified OK")

    orig_size = os.path.getsize(str(backup_path))
    new_size = os.path.getsize(str(output_path))
    print(f"\n  Original: {orig_size:,} bytes")
    print(f"  Patched:  {new_size:,} bytes")
    print(f"  Delta:    {new_size - orig_size:+,} bytes")


if __name__ == "__main__":
    main()
