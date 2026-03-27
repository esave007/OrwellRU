#!/usr/bin/env python3
"""
Patch resources.assets MonoBehaviour objects with translations.
Separate from apply_smartloc.py which handles SmartLocalization TextAssets.
This patches the m_text fields in MonoBehaviour objects directly.
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
    """Load ALL translation batches for resources.assets."""
    translations = {}

    # Load batch_resources_*.json files
    pattern = str(PROJECT / "translated" / "batch_resources_*.json")
    batch_files = sorted(glob.glob(pattern))
    for fpath in batch_files:
        fname = Path(fpath).name
        with open(fpath, 'r', encoding='utf-8') as f:
            batch = json.load(f)
        filled = {k: v for k, v in batch.items() if v and v != k}
        translations.update(filled)
        print(f"  {fname}: {len(filled)}/{len(batch)} entries")

    # Also load from translation_template.json (entries that have translations)
    template_path = PROJECT / "translated" / "translation_template.json"
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        template_trans = {e['original']: e['translation'] for e in template
                         if e.get('translation') and e['translation'] != e['original']}
        # Don't overwrite batch translations (they're more recent/reviewed)
        for k, v in template_trans.items():
            if k not in translations:
                translations[k] = v
        print(f"  translation_template.json: {len(template_trans)} entries (non-duplicate)")

    # Also reuse level3 translations (many strings appear in both)
    l3_pattern = str(PROJECT / "translated" / "batch_level3_*.json")
    l3_count = 0
    for fpath in sorted(glob.glob(l3_pattern)):
        with open(fpath, 'r', encoding='utf-8') as f:
            batch = json.load(f)
        for k, v in batch.items():
            if v and k not in translations:
                translations[k] = v
                l3_count += 1
    if l3_count:
        print(f"  Reused from level3 batches: {l3_count} entries")

    print(f"  TOTAL: {len(translations)} translations")
    return translations


def main():
    print("=" * 60)
    print("RESOURCES.ASSETS PATCHER: MonoBehaviour translations")
    print("=" * 60)

    print("\nLoading translations:")
    translations = load_translations()

    if not translations:
        print("\nNo translations found!")
        return

    # Parse from the CURRENT patched resources.assets (already has SmartLoc + fonts)
    # We build on top of existing patches
    src_path = PROJECT / "patches" / "resources.assets"
    if not src_path.exists():
        src_path = BACKUP / "resources.assets"
    print(f"\nParsing {src_path}...")
    usf = UnitySerializedFile(str(src_path))
    print(f"  Objects: {len(usf.objects)}, File size: {usf.file_size}")

    replacements = {}
    total_replaced = 0

    # PIDs to SKIP — internal game controllers, NOT display text!
    SKIP_PIDS = {
        # Aptitude test screen state controllers (website_aptitudetest_*)
        696, 697, 698, 699, 700,
        # Flow state objects ("Aptitude Test" lookup key)
        733, 734, 735, 736, 737, 738, 739, 740, 741, 742,
        # "Update: Task *" internal event identifiers
        796, 797, 798, 799, 800, 801, 802, 803, 804, 805,
        806, 807, 808, 809, 810, 811, 812, 813, 814, 815,
        816, 817, 818, 819, 820, 821, 822, 823, 824, 825,
        826, 827, 828,
        # Main gameflow controller
        4988,
    }

    print("\nApplying translations to MonoBehaviour objects:")
    for obj in usf.objects:
        if obj['type_index'] >= len(usf.types):
            continue
        class_id = usf.types[obj['type_index']]['class_id']
        if class_id != 114:
            continue
        if obj['path_id'] in SKIP_PIDS:
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
    output_path = PROJECT / "patches" / "resources.assets"
    print(f"\nRebuilding {output_path}...")
    usf.rebuild_with_replacements(replacements, str(output_path))

    # Verify
    print("\nVerification:")
    with open(output_path, 'rb') as f:
        data = f.read()
    checks = [
        "Нация",
        "Площадь Свободы",
        "Рабан Вхарт",
        "Загрузка",
    ]
    ok = sum(1 for c in checks if c.encode('utf-8') in data)
    print(f"  {ok}/{len(checks)} verified OK")

    orig_size = os.path.getsize(str(src_path))
    new_size = os.path.getsize(str(output_path))
    print(f"\n  Source:   {orig_size:,} bytes")
    print(f"  Patched:  {new_size:,} bytes")
    print(f"  Delta:    {new_size - orig_size:+,} bytes")


if __name__ == "__main__":
    main()
