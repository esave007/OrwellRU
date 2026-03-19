#!/usr/bin/env python3
"""
Patch level4 with ALL translations + UI adjustments.
v2: Processes ALL MonoBehaviour objects, not just 27 aptitude ones.
"""
import os, sys, json, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile, find_and_replace_strings

PROJECT = Path(r"C:\Projects\OrwellRU")
GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
BACKUP = PROJECT / "backup"

# RectTransform adjustments for Russian text
# {rt_path_id: (new_width, new_height)}
RT_ADJUSTMENTS = {
    # === TITLES & SUBTITLES ===
    676: (1400.0, 110.0),      # Title "ТЕСТ НА ПРИГОДНОСТЬ"
    822: (1510.0, 350.0),      # Subtitle
    633: (1700.0, 120.0),      # "INSUFFICIENT RESULTS" header — widened for Russian
    737: (1700.0, 250.0),      # Subtitle "You failed..." — widened
    787: (1700.0, 200.0),      # Body text on insufficient-results screen — widened
    923: (1700.0, 120.0),      # Title "LIES DETECTED" — widened for Russian
    896: (1700.0, 250.0),      # Subtitle "You have been lying!" — widened
    764: (1700.0, 200.0),      # Lie-screen body text — widened

    # === ANSWER CONTAINERS (width only, heights MUST stay original!) ===
    900: (1600.0, 401.38),     # Task 1 answers
    693: (1600.0, 623.13),     # Task 3 answers
    870: (1600.0, 401.38),     # Fail screen answers
    754: (1600.0, 401.38),     # Lie screen answers
    650: (1600.0, 456.82),     # Task answers variant
    720: (1600.0, 401.38),     # Task answers variant
    824: (1600.0, 473.15),     # Task answers variant
    916: (1600.0, 447.91),     # Task answers variant

    # === CHUNK BOXES — the actual clickable answer strips (height~52.91) ===
    # All widened to 1400px to fit Russian text (never shrink originals)
    647: (1400.0, 52.91),
    670: (1400.0, 52.91),
    673: (1400.0, 52.91),
    681: (1400.0, 52.91),
    689: (1400.0, 52.91),
    696: (1400.0, 52.91),
    703: (1400.0, 52.91),
    # 731: SKIP — Task 6 extra (empty box, no answer text)
    745: (1400.0, 52.91),
    746: (1400.0, 52.91),
    753: (1400.0, 52.91),
    755: (1400.0, 52.91),
    762: (1400.0, 52.91),
    765: (1400.0, 52.91),
    782: (1400.0, 52.91),
    786: (1400.0, 52.91),
    821: (1400.0, 52.91),
    831: (1400.0, 52.91),
    # 835: SKIP — Task 6 extra (empty box, no answer text)
    843: (1400.0, 52.91),
    844: (1400.0, 52.91),
    845: (1400.0, 52.91),
    852: (1400.0, 52.91),
    859: (1400.0, 52.91),
    864: (1400.0, 52.91),
    880: (1400.0, 52.91),
    885: (1400.0, 0.1),       # Fail screen row 2 extra — shrunk to invisible (Button stays)
    890: (1400.0, 52.91),
    893: (1400.0, 52.91),
    895: (1400.0, 52.91),
    902: (1400.0, 52.91),
    905: (1400.0, 52.91),
    # 920: SKIP — Task 6 extra (empty box, no answer text)
    921: (1400.0, 52.91),
}

# Y position adjustments for chunk boxes.
# TMP renders Cyrillic lines with ~7px more spacing than original 70px.
# Chunk boxes grouped by row; each subsequent row shifts down by 7px more.
DELTA = 16.5  # extra px per line vs original 70px spacing

Y_ADJUSTMENTS = {
    # Row 0 (Y≈-636.85): NO SHIFT — first line aligns
    # Row 1 (Y≈-706.87): shift down by 1*DELTA
    647: -706.87 - 1 * DELTA,
    670: -706.87 - 1 * DELTA,
    673: -706.87 - 1 * DELTA,
    755: -706.87 - 1 * DELTA,
    821: -706.87 - 1 * DELTA,
    831: -706.87 - 1 * DELTA,
    895: -706.87 - 1 * DELTA,
    905: -706.73 - 1 * DELTA,  # slightly different original Y
    # Row 2 (Y≈-776.89): shift down by 2*DELTA
    703: -776.89 - 2 * DELTA,
    745: -776.89 - 2 * DELTA,
    746: -776.89 - 2 * DELTA,
    859: -776.89 - 2 * DELTA,
    885: -776.89 - 2 * DELTA,
    921: -776.75 - 2 * DELTA,  # slightly different original Y
    # Row 3 (Y≈-846.91): shift down by 3*DELTA
    681: -846.91 - 3 * DELTA,
    844: -846.91 - 3 * DELTA,
    845: -846.91 - 3 * DELTA,
    852: -846.77 - 3 * DELTA,  # slightly different original Y
    893: -846.91 - 3 * DELTA,
    # Row 4 (Y≈-916.92): shift down by 4*DELTA
    689: -916.92 - 4 * DELTA,
    765: -916.92 - 4 * DELTA,
    786: -916.92 - 4 * DELTA,
    880: -916.78 - 4 * DELTA,  # slightly different original Y
    902: -916.92 - 4 * DELTA,
    # Task 6 extras — move off-screen (Y=-5000)
    920: -5000.0,
    731: -5000.0,
    835: -5000.0,
    # Task 6 valid answers — progressive DELTA (drift accelerates)
    905: -706.73 - 8.0,       # Row 1: OK
    921: -776.75 - 16.0,      # Row 2: OK
    852: -846.77 - 36.0,      # Row 3: answer 3 (bumped +12)
    880: -916.78 - 52.0,      # Row 4: answer 4 (bumped +20)
}


def modify_rect_transform(raw_data, new_width, new_height):
    """Modify sizeDelta in a RectTransform's raw data."""
    data = bytearray(raw_data)
    children_count = struct.unpack_from('<I', data, 52)[0]
    size_delta_offset = 92 + children_count * 12
    old_w, old_h = struct.unpack_from('<ff', data, size_delta_offset)
    struct.pack_into('<ff', data, size_delta_offset, new_width, new_height)
    return bytes(data), old_w, old_h


def modify_rect_position_y(raw_data, new_y):
    """Modify anchoredPosition.Y in a RectTransform's raw data."""
    data = bytearray(raw_data)
    children_count = struct.unpack_from('<I', data, 52)[0]
    anchor_y_offset = 88 + children_count * 12  # anchoredPosition.Y (4 bytes after X)
    old_y = struct.unpack_from('<f', data, anchor_y_offset)[0]
    struct.pack_into('<f', data, anchor_y_offset, new_y)
    return bytes(data), old_y


def load_translations():
    """Load ALL translation batches for level4."""
    translations = {}
    batch_files = [
        "batch_02_aptitude_level4.json",
        "batch_02_aptitude_answers.json",
        "batch_03_level4_ui.json",
    ]
    for fname in batch_files:
        fpath = PROJECT / "translated" / fname
        if fpath.exists():
            with open(fpath, 'r', encoding='utf-8') as f:
                batch = json.load(f)
                translations.update(batch)
                print(f"  {fname}: {len(batch)} entries")
    print(f"  TOTAL: {len(translations)} translations")
    return translations


def main():
    print("=" * 60)
    print("LEVEL4 PATCHER v2: ALL translations + UI adjustments")
    print("=" * 60)

    print("\nLoading translations:")
    translations = load_translations()

    # ALWAYS parse from BACKUP (original English)
    backup_path = BACKUP / "level4"
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
            print(f"  pid={obj['path_id']:5d}: {count} replacement(s), "
                  f"{len(raw)} -> {len(new_raw)} bytes")

    print(f"\nText: {total_replaced} replacements in {len(replacements)} objects")

    # Apply RectTransform adjustments
    print("\nUI adjustments (RectTransform sizeDelta):")
    for rt_pid, (new_w, new_h) in RT_ADJUSTMENTS.items():
        raw = usf.get_object_data(rt_pid)
        if raw is None:
            print(f"  RT pid={rt_pid}: NOT FOUND")
            continue
        new_raw, old_w, old_h = modify_rect_transform(raw, new_w, new_h)
        replacements[rt_pid] = new_raw
        print(f"  RT pid={rt_pid}: ({old_w:.0f}x{old_h:.0f}) -> ({new_w:.0f}x{new_h:.0f})")

    # Apply Y position adjustments to chunk boxes
    print("\nY position adjustments (chunk box vertical alignment):")
    for rt_pid, new_y in Y_ADJUSTMENTS.items():
        raw = replacements.get(rt_pid) or usf.get_object_data(rt_pid)
        if raw is None:
            print(f"  RT pid={rt_pid}: NOT FOUND")
            continue
        new_raw, old_y = modify_rect_position_y(raw, new_y)
        replacements[rt_pid] = new_raw
        print(f"  RT pid={rt_pid}: Y {old_y:.1f} -> {new_y:.1f} (delta={new_y - old_y:.1f})")

    # Rebuild
    output_path = PROJECT / "patches" / "level4"
    print(f"\nRebuilding {output_path}...")
    usf.rebuild_with_replacements(replacements, str(output_path))

    # Verify
    print("\nVerification:")
    with open(output_path, 'rb') as f:
        data = f.read()
    checks = [
        "ТЕСТ НА ПРИГОДНОСТЬ",
        "Несправедливый закон",
        "Хочу быть первопроходцем",
        "Управление не терпит лжи",
        "Сексуальная ориентация",
        "Задание 1",
        "Задание 3",
        "Задание 5",
        "Кандидат",
        "Профессия",
        "В паре с",
        "Эл. почта",
        "Операционная система",
        "СПАСИБО",
        "Ответить",
        "ОБНАРУЖЕНА ЛОЖЬ",
        "НЕТОЧНАЯ ИНФОРМАЦИЯ",
        "Тест на пригодность",
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

    # Also verify no English remnants for key strings
    print("\nEnglish remnants check:")
    english_checks = [
        "APTITUDE TEST",
        "INSUFFICIENT RESULTS",
        "Send Answer",
        "Operating System",
        "Applicant-ID",
        "Paired with",
    ]
    for c in english_checks:
        found = c.encode('utf-8') in data
        status = "STILL PRESENT" if found else "removed"
        print(f"  [{status}] {c}")


if __name__ == "__main__":
    main()
