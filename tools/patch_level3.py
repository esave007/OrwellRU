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

    # Type indices to ALLOW — display-text classes ONLY (script class per type_index
    # resolved via m_Script PPtr -> MonoScript, see tools/diag_replacement_map.py).
    # Everything else is SKIPPED: blind binary replace in Unity system components
    # corrupts engine fields:
    #   - StandaloneInputModule (PID 49699): axis names Horizontal/Vertical/Submit/Cancel
    #     were translated -> Input.GetAxis throws every frame -> dead input
    #   - Selectable/Button/Scrollbar/Slider/Toggle: m_AnimationTriggers
    #     Normal/Highlighted/Pressed/Disabled were translated (3,764 corruptions)
    #   - Button m_OnClick: method name "Show" -> "Показать" (broken click handlers)
    #   - SaveGameManager, ImageAsset: path/asset identifiers
    ALLOWED_TYPE_INDICES = {
        16,  # TextMeshProUGUI — m_text @196 (display)
        24,  # Website — display titles (page controllers excluded via SKIP_PIDS)
        25,  # InsiderDocument — display names (Desktop, Trash, file names)
        38,  # Mail — subjects (display)
        51,  # WebsiteHeader — display titles
        61,  # PodcastTranscript — cutscene subtitles
        65,  # OnlinePresence — site display names
        70,  # InsiderDevice — device display names
    }

    # PIDs to SKIP — internal game logic, NOT display text!
    # These objects use English strings as lookup keys for the game engine.
    # Translating them breaks game flow (transitions, state machines, navigation).
    SKIP_PIDS = {
        # DateTool._dateLabel (TMP): game calls DateTime.Parse(_dateLabel.text) on
        # every new mail/chat (DateTool.GetDate) and day change (IncreaseDayIndex).
        # Mono invariant culture can't parse Russian dates -> FormatException ->
        # day-flow coroutine dies -> ETERNAL LOADING. Must stay "April 12, 2017"
        # (the game overwrites it with English ToString("MMMM dd, yyyy") anyway).
        36332,
        # RelativeTimestamp PID 45985 target label "10:25 am": translation "10:25"
        # is shorter than StampStartIndex+StampLength=8 -> Remove() throws
        # ArgumentOutOfRangeException. Runtime overwrites this text anyway.
        37848,
        # Main gameflow controller — episode transitions, flow lookups
        # Contains "Aptitude Test", "Ignorance Is Strength - Day 1/2/3",
        # "Episode One/Two/Three", Assets/Resources/Flows/ paths
        44155,
        # Character database — CHAR_* identifiers, Ntt_* hashes, image refs
        44858,
        # Website page controllers — website_* navigation/state identifiers
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

    replacements = {}
    total_replaced = 0
    skipped = 0

    # Apply text translations to MonoBehaviour objects (display text only)
    print("\nApplying translations to MonoBehaviour objects:")
    for obj in usf.objects:
        if obj['type_index'] >= len(usf.types):
            continue
        class_id = usf.types[obj['type_index']]['class_id']
        if class_id != 114:  # MonoBehaviour only
            continue
        if obj['type_index'] not in ALLOWED_TYPE_INDICES:
            skipped += 1
            continue
        if obj['path_id'] in SKIP_PIDS:
            skipped += 1
            continue
        raw = usf.get_object_data(obj['path_id'])
        if not raw or len(raw) < 20:
            continue
        new_raw, count = find_and_replace_strings(raw, translations)
        if count > 0:
            replacements[obj['path_id']] = new_raw
            total_replaced += count

    print(f"  Skipped {skipped} internal game logic objects")

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
        "Памятник Свободы",
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
