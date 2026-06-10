#!/usr/bin/env python3
"""
Bisect auto-translations in level3.
Modes:
  --no-auto      : ALL manual batches, NO auto batches
  --auto-only    : ONLY auto batch (no manual)
  --dates        : manual + only date translations from auto
  --counters     : manual + only counter translations from auto
  --readmore     : manual + only "read more" translations from auto
  --joined       : manual + only "Joined:" translations from auto
  --posted       : manual + only "Posted" translations from auto
  --full-dates   : manual + only "Month DD, YYYY" full dates from auto
  --short-dates  : manual + only "Month DD" short dates (no year)
"""
import os, sys, json, glob, struct, re, shutil
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile, find_and_replace_strings

PROJECT = Path(r"C:\Projects\OrwellRU")
BACKUP = PROJECT / "backup"
GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")

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

MANUAL_BATCHES = [
    "batch_level3_01.json", "batch_level3_02.json", "batch_level3_03.json",
    "batch_level3_04.json", "batch_level3_04_long.json", "batch_level3_05.json",
    "batch_level3_05_medium.json", "batch_level3_06_short.json",
    "batch_level3_07.json", "batch_level3_08.json", "batch_level3_09.json",
    "batch_level3_podcasts.json",
]


def categorize_auto(translations):
    """Split auto translations into categories."""
    cats = {
        'counters': {},    # "N likes", "N comments", etc.
        'full_dates': {},  # "Month DD, YYYY"
        'short_dates': {}, # "Month DD" (no year)
        'joined': {},      # "Joined: ..."
        'posted': {},      # "Posted ..."
        'readmore': {},    # "<link>read more</link>"
        'comments_viewed': {},  # "N comments, viewed M times"
    }
    months = '(?:January|February|March|April|May|June|July|August|September|October|November|December)'

    for eng, rus in translations.items():
        t = eng.strip().rstrip('\r')
        if re.match(r'^\d+\s+(?:likes?|re-blabbers?|comments?|answers?|upvotes?)$', t, re.I):
            cats['counters'][eng] = rus
        elif re.match(r'^\d+\s+comments?,\s+viewed\s+\d+\s+times?$', t):
            cats['comments_viewed'][eng] = rus
        elif t.startswith('Joined:'):
            cats['joined'][eng] = rus
        elif t.startswith('Posted '):
            cats['posted'][eng] = rus
        elif 'read more' in t:
            cats['readmore'][eng] = rus
        elif re.match(rf'^{months}\s+\d{{1,2}},?\s*\d{{4}}$', t):
            cats['full_dates'][eng] = rus
        elif re.match(rf'^{months}\s+\d{{1,2}}\s*$', t):
            cats['short_dates'][eng] = rus
        else:
            # Standalone month or unknown
            cats['full_dates'][eng] = rus  # put with full dates

    return cats


def load_manual():
    translations = {}
    for fname in MANUAL_BATCHES:
        fpath = PROJECT / "translated" / fname
        if not fpath.exists():
            continue
        with open(fpath, 'r', encoding='utf-8') as f:
            batch = json.load(f)
        filled = {k: v for k, v in batch.items() if v}
        translations.update(filled)
        print(f"  {fname}: {len(filled)}")
    return translations


def load_auto():
    fpath = PROJECT / "translated" / "batch_level3_auto.json"
    with open(fpath, 'r', encoding='utf-8') as f:
        batch = json.load(f)
    return {k: v for k, v in batch.items() if v}


def patch_and_deploy(translations, label):
    print(f"\n  TOTAL translations: {len(translations)}")
    print(f"\nParsing backup/level3...")
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

    output = PROJECT / "patches" / "level3"
    usf.rebuild_with_replacements(replacements, str(output))

    shutil.copy2(str(output), str(GAME_DATA / "level3"))
    print(f"\n*** Deployed [{label}] to game. Launch and test! ***")


def main():
    args = set(sys.argv[1:])

    if not args:
        print("Usage: python bisect_auto_level3.py <mode>")
        print("Modes:")
        print("  --no-auto       : manual only, NO auto")
        print("  --auto-only     : ONLY auto batch")
        print("  --dates         : manual + all dates from auto")
        print("  --full-dates    : manual + full dates only (Month DD, YYYY)")
        print("  --short-dates   : manual + short dates only (Month DD)")
        print("  --counters      : manual + counters from auto")
        print("  --readmore      : manual + 'read more' from auto")
        print("  --joined        : manual + 'Joined:' from auto")
        print("  --posted        : manual + 'Posted' from auto")
        print("  --no-short-dates: manual + auto MINUS short dates")
        print("  --no-counters   : manual + auto MINUS counters")
        return

    print("Loading manual batches:")
    manual = load_manual()
    print(f"  Manual total: {len(manual)}")

    auto = load_auto()
    cats = categorize_auto(auto)

    print(f"\nAuto categories:")
    for cat, entries in cats.items():
        print(f"  {cat}: {len(entries)}")
    print(f"  TOTAL: {sum(len(v) for v in cats.values())}")

    if '--no-auto' in args:
        patch_and_deploy(manual, "MANUAL ONLY — no auto")
        return

    if '--auto-only' in args:
        patch_and_deploy(auto, "AUTO ONLY — no manual")
        return

    # Build combined based on flags
    translations = dict(manual)
    label_parts = ["manual"]

    if '--dates' in args:
        translations.update(cats['full_dates'])
        translations.update(cats['short_dates'])
        label_parts.append("all dates")
    if '--full-dates' in args:
        translations.update(cats['full_dates'])
        label_parts.append("full dates")
    if '--short-dates' in args:
        translations.update(cats['short_dates'])
        label_parts.append("short dates")
    if '--counters' in args:
        translations.update(cats['counters'])
        translations.update(cats['comments_viewed'])
        label_parts.append("counters")
    if '--readmore' in args:
        translations.update(cats['readmore'])
        label_parts.append("read more")
    if '--joined' in args:
        translations.update(cats['joined'])
        label_parts.append("joined")
    if '--posted' in args:
        translations.update(cats['posted'])
        label_parts.append("posted")

    # Exclusion modes: add ALL auto, then remove specific category
    if '--no-short-dates' in args:
        translations.update(auto)
        for k in cats['short_dates']:
            translations.pop(k, None)
        label_parts = ["manual + auto MINUS short dates"]
    if '--no-counters' in args:
        translations.update(auto)
        for k in cats['counters']:
            translations.pop(k, None)
        for k in cats['comments_viewed']:
            translations.pop(k, None)
        label_parts = ["manual + auto MINUS counters"]

    patch_and_deploy(translations, " + ".join(label_parts))


if __name__ == "__main__":
    main()
