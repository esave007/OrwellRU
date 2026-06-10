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
    """Load translation batches for resources.assets.

    Pipeline safety:
    - batch_resources_*.json — curated translations (highest priority)
    - batch_level3_*.json — reused for shared dialogue/text
    - Game logic objects are protected by SKIP_TYPE_INDICES (not here)
    """
    translations = {}

    # Load batch_resources_*.json files (curated, highest priority)
    pattern = str(PROJECT / "translated" / "batch_resources_*.json")
    batch_files = sorted(glob.glob(pattern))
    for fpath in batch_files:
        fname = Path(fpath).name
        with open(fpath, 'r', encoding='utf-8') as f:
            batch = json.load(f)
        filled = {k: v for k, v in batch.items() if v and v != k}
        translations.update(filled)
        print(f"  {fname}: {len(filled)}/{len(batch)} entries")

    # Reuse level3 translations (many strings appear in both)
    # Safe because game logic objects are filtered by SKIP_TYPE_INDICES
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

    # Type indices to SKIP — pure game logic, NO display text.
    # Translating internal state names/identifiers breaks game flow.
    SKIP_TYPE_INDICES = {
        7,   # FacebookSettings (1 obj)
        8,   # PlayFabSharedSettings (1 obj)
        9,   # DocumentViewedState — has _documentId, _chatId, _personId (4 objs)
        10,  # EmptyState — logic gates (960 objs)
        11,  # FadeAtmoLayerState — audio (75 objs)
        12,  # IfElseState — logic (284 objs)
        13,  # NewBookmarkState — has _onlinePresenceName lookup (76 objs)
        14,  # NewDataChunkState — has _chunkId, _personId CRITICAL (48 objs)
        15,  # NewPersonState — has _personId (1 obj)
        16,  # NewTargetPersonState — has _personId (12 objs)
        17,  # OrState — logic (207 objs)
        18,  # PlayMusicState — audio (13 objs)
        19,  # StartEndingFlowState — has _flowName lookup (4 objs)
        20,  # UpdateProfileState — has field identifiers (53 objs)
        21,  # AtClockTimeState — timing (145 objs)
        22,  # AtLeastState — logic (14 objs)
        23,  # BlockCommentsState — logic (3 objs)
        24,  # ChangeInsiderStatusState — logic (14 objs)
        25,  # DelayState — timing (73 objs)
        26,  # InfluencerFollowerCountState — logic (35 objs)
        27,  # InsiderObject — has CHAR_* person IDs (3 objs)
        28,  # InsiderDocumentObject — has insider_* doc IDs (22 objs)
        29,  # LevelCompleteState — logic (2 objs)
        31,  # UpdateDropRepeatableState — has _dropId (28 objs)
        37,  # OnlinePresenceBookmarkData — has document IDs (4 objs)
        39,  # ObjectiveSolvedState — logic (31 objs)
        40,  # OnGameEventCallbackState — logic (12 objs)
        41,  # UnlockAchievementState — logic (18 objs)
        45,  # WeatherState — logic (9 objs)
        46,  # MergePersonsState — logic (1 obj)
        47,  # OpenDocumentState — has document IDs (6 objs)
        48,  # OpenAppOrTabState — logic (22 objs)
        49,  # ToolEventState — logic (1 obj)
        50,  # WaitState — logic (3 objs)
        51,  # GameFlow controllers — episode transitions (8 objs)
        52,  # VoiceOverTimings — timing data (1 obj)
        53,  # Font objects — handled by font patcher (6 objs)
        54,  # DropCap Numbers — glyph data (3 objs)
        55,  # TMP Default Style Sheet (1 obj)
    }

    # PIDs to SKIP — specific objects with internal lookup keys
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
    }

    skipped_type = 0
    skipped_pid = 0
    print("\nApplying translations to MonoBehaviour objects:")
    for obj in usf.objects:
        if obj['type_index'] >= len(usf.types):
            continue
        class_id = usf.types[obj['type_index']]['class_id']
        if class_id != 114:
            continue
        if obj['type_index'] in SKIP_TYPE_INDICES:
            skipped_type += 1
            continue
        if obj['path_id'] in SKIP_PIDS:
            skipped_pid += 1
            continue
        raw = usf.get_object_data(obj['path_id'])
        if not raw or len(raw) < 20:
            continue
        new_raw, count = find_and_replace_strings(raw, translations)
        if count > 0:
            replacements[obj['path_id']] = new_raw
            total_replaced += count

    print(f"\n  Skipped {skipped_type} objects by type_index (game logic)")
    print(f"  Skipped {skipped_pid} objects by PID (internal controllers)")
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
