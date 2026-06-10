#!/usr/bin/env python3
"""
Binary search tool to find which translations break level3.
Usage: python tools/bisect_level3.py <batch_file1> [batch_file2] ...
       python tools/bisect_level3.py --first-half
       python tools/bisect_level3.py --second-half
"""
import os, sys, json, glob, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile, find_and_replace_strings

PROJECT = Path(r"C:\Projects\OrwellRU")
BACKUP = PROJECT / "backup"
GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")

ALL_BATCHES = [
    "batch_level3_01.json",
    "batch_level3_02.json",
    "batch_level3_03.json",
    "batch_level3_04.json",
    "batch_level3_04_long.json",
    "batch_level3_05.json",
    "batch_level3_05_medium.json",
    "batch_level3_06_short.json",
    "batch_level3_07.json",
    "batch_level3_08.json",
    "batch_level3_09.json",
    "batch_level3_auto.json",
    "batch_level3_final.json",
    "batch_level3_podcasts.json",
]

SKIP_PIDS = {
    44155, 44858,
    41412, 41652, 41856, 41931, 42208, 42221, 42226, 42419, 42683, 42822,
    43123, 43702, 43741, 44066, 44067, 44072, 44443, 44527, 44790, 44983,
    45023, 45149, 45221, 45251, 45329, 45550, 45654, 45705, 45729, 46450,
    46583, 46947, 46965, 47041, 47147, 47196, 47252, 47281, 47362, 47405,
    47510, 47519, 47584, 47596, 47909, 48018, 48057, 48097, 48490, 48559,
    48716, 48723, 48728, 48759, 48767, 48961, 49061, 49114, 49134, 49247,
    49304, 49392, 50181, 50759, 50868, 50969, 50982, 51002, 51035, 51052,
    51190, 51532, 51860, 52012, 52354, 53255, 53494, 53564, 53661, 53706,
    53809, 53942, 54421,
}


def main():
    args = sys.argv[1:]

    if "--first-half" in args:
        selected = ALL_BATCHES[:7]
    elif "--second-half" in args:
        selected = ALL_BATCHES[7:]
    elif args:
        selected = args
    else:
        print("Usage: python bisect_level3.py --first-half | --second-half | <file1> [file2] ...")
        print(f"\nAll batches: {ALL_BATCHES}")
        return

    # Load translations from selected files only
    translations = {}
    for fname in selected:
        fpath = PROJECT / "translated" / fname
        if not fpath.exists():
            print(f"  SKIP (not found): {fname}")
            continue
        with open(fpath, 'r', encoding='utf-8') as f:
            batch = json.load(f)
        filled = {k: v for k, v in batch.items() if v}
        translations.update(filled)
        print(f"  {fname}: {len(filled)} entries")

    print(f"  TOTAL: {len(translations)} translations from {len(selected)} files")

    # Parse and patch
    usf = UnitySerializedFile(str(BACKUP / "level3"))

    replacements = {}
    total_replaced = 0
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

    print(f"\n{total_replaced} replacements in {len(replacements)} objects")

    # Rebuild and deploy
    output = PROJECT / "patches" / "level3"
    usf.rebuild_with_replacements(replacements, str(output))

    # Copy to game
    import shutil
    shutil.copy2(str(output), str(GAME_DATA / "level3"))
    print(f"\nDeployed to game. Launch and test!")


if __name__ == "__main__":
    main()
