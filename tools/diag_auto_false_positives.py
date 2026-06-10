#!/usr/bin/env python3
"""
Deep diagnostic: find why batch_level3_auto.json translations break the game.
Checks for false positive binary matches, unexpected offsets, and structural corruption.
"""
import os, sys, struct, json
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, r"C:\Projects\OrwellRU\tools")
from unity_serialized_patcher import UnitySerializedFile, find_and_replace_strings

LEVEL3_PATH = r"C:\Projects\OrwellRU\backup\level3"
AUTO_JSON   = r"C:\Projects\OrwellRU\translated\batch_level3_auto.json"

SKIP_PIDS = {
    44155, 44858,
    # website page controllers (from patch_level3.py)
    43998,43999,44000,44001,44002,44003,44004,44005,44006,44007,
    44008,44009,44010,44011,44012,44013,44014,44015,44016,44017,
    44018,44019,44020,44021,44022,44023,44024,44025,44026,44027,
    44028,44029,44030,44031,44032,44033,44034,44035,44036,44037,
    44038,44039,44040,44041,44042,44043,44044,44045,44046,44047,
    44048,44049,44050,44051,44052,44053,44054,44055,44056,44057,
    44058,44059,44060,44061,44062,44063,44064,44065,44066,44067,
    44068,44069,44070,44071,44072,44073,44074,44075,44076,44077,
    44078,44079,44080,44081,44082,44083,
}

def parse_strings_from_raw(data):
    """Extract all length-prefixed strings from raw object data."""
    strings = []
    i = 0
    while i < len(data) - 4:
        slen = struct.unpack_from('<I', data, i)[0]
        if 1 <= slen <= 50000 and i + 4 + slen <= len(data):
            try:
                s = data[i+4:i+4+slen].decode('utf-8')
                strings.append((i, slen, s))
                padding = (4 - (slen % 4)) % 4
                i += 4 + slen + padding
                continue
            except:
                pass
        i += 1
    return strings

def check_structural_integrity(raw_data, label=""):
    """
    Check if raw_data has valid MonoBehaviour structure.
    MonoBehaviours start with: [game_object_ref: 8 bytes][enabled: 1][padding: 3][script_ref: 8 bytes] = 20 bytes
    Then m_Name string (length-prefixed).
    Returns True if m_Name is readable.
    """
    try:
        # m_Name is at offset 20
        name_len = struct.unpack_from('<I', raw_data, 20)[0]
        if name_len > 10000:
            return False, f"m_Name length={name_len} (too large!)"
        name = raw_data[24:24+name_len].decode('utf-8', errors='replace')
        return True, f"m_Name='{name}' len={name_len}"
    except Exception as e:
        return False, str(e)

def find_all_binary_matches(data_bytes, key_bytes):
    """Find all positions where [4-byte LE len][key_bytes] occurs in data."""
    prefix = struct.pack('<I', len(key_bytes))
    needle = prefix + key_bytes
    positions = []
    pos = 0
    while True:
        pos = data_bytes.find(needle, pos)
        if pos == -1:
            break
        positions.append(pos)
        pos += 1
    return positions

def main():
    print("=" * 70)
    print("DIAGNOSTIC: Auto-translation false positive detection in level3")
    print("=" * 70)

    print(f"\nLoading {LEVEL3_PATH} ...")
    usf = UnitySerializedFile(LEVEL3_PATH)
    print(f"Parsed OK: {len(usf.objects)} objects, {len(usf.types)} types")
    print(f"Data offset: {usf.data_offset}, File size: {usf.file_size}")

    print(f"\nLoading {AUTO_JSON} ...")
    with open(AUTO_JSON, 'r', encoding='utf-8') as f:
        auto_translations = json.load(f)
    print(f"Loaded {len(auto_translations)} auto-translations")

    # Build lookup: class_id per type_index
    type_class = {i: t['class_id'] for i, t in enumerate(usf.types)}

    # Build object map
    obj_by_pid = {o['path_id']: o for o in usf.objects}

    # -----------------------------------------------------------------------
    # PHASE 1: Scan entire file binary for each key
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 1: Full binary scan — matches outside expected objects")
    print("=" * 70)

    # Build the raw data section for scanning
    raw_file = bytes(usf.data)

    # Build a map: byte_offset_in_file -> path_id for the object containing it
    # So we can identify which object a match belongs to
    sorted_objs = sorted(usf.objects, key=lambda o: o['offset'])
    def find_owner(abs_offset):
        """Find which object owns this file offset."""
        rel = abs_offset - usf.data_offset
        for obj in sorted_objs:
            if obj['offset'] <= rel < obj['offset'] + obj['size']:
                return obj['path_id'], rel - obj['offset']
        return None, None

    # Focus on short/dangerous keys
    dangerous_keys = []
    for key in auto_translations:
        key_bytes = key.encode('utf-8')
        if len(key_bytes) <= 20:  # Short keys most likely to false-positive
            dangerous_keys.append((key, key_bytes))
    dangerous_keys.sort(key=lambda x: len(x[1]))

    print(f"\nChecking {len(dangerous_keys)} short keys (<=20 bytes) for false positives...")

    false_positives = []  # (key, abs_offset, pid, offset_in_obj, class_id, is_skip)

    for key, key_bytes in dangerous_keys:
        prefix = struct.pack('<I', len(key_bytes))
        needle = prefix + key_bytes
        pos = 0
        while True:
            pos = raw_file.find(needle, pos)
            if pos == -1:
                break
            # Find which object owns this offset
            pid, off_in_obj = find_owner(pos)
            if pid is None:
                print(f"  MATCH OUTSIDE ANY OBJECT: key={repr(key)} at file_offset={pos}")
                false_positives.append((key, pos, None, None, None, False))
            else:
                obj = obj_by_pid[pid]
                type_idx = obj['type_index']
                class_id = type_class.get(type_idx, -1)
                is_skip = pid in SKIP_PIDS

                # For non-MonoBehaviour objects (class_id != 114), this is always suspicious
                if class_id != 114:
                    print(f"  NON-MONOBEHAVIOUR MATCH: key={repr(key)}")
                    print(f"    PID={pid}, class_id={class_id}, offset_in_obj={off_in_obj}")
                    false_positives.append((key, pos, pid, off_in_obj, class_id, is_skip))
                elif is_skip:
                    print(f"  SKIP_PID MATCH: key={repr(key)}")
                    print(f"    PID={pid} (SKIP!), offset_in_obj={off_in_obj}")
                    false_positives.append((key, pos, pid, off_in_obj, class_id, True))
                else:
                    # MonoBehaviour, not skipped — this is expected. But check offset.
                    # m_text in TextMeshProUGUI is typically at offset ~196 (after headers)
                    # But it varies. Flag if match is at very early offset (would be in headers)
                    if off_in_obj < 20:
                        print(f"  SUSPICIOUS EARLY OFFSET: key={repr(key)}")
                        print(f"    PID={pid}, class_id={class_id}, offset_in_obj={off_in_obj} (<20!)")
                        false_positives.append((key, pos, pid, off_in_obj, class_id, False))
            pos += 1

    print(f"\nTotal suspicious matches found: {len(false_positives)}")

    # -----------------------------------------------------------------------
    # PHASE 2: Check if any key matches in SKIP_PIDS at all
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 2: ALL keys — do any match in SKIP_PIDS objects?")
    print("=" * 70)

    skip_pid_matches = {}
    for key, rus in auto_translations.items():
        key_bytes = key.encode('utf-8')
        prefix = struct.pack('<I', len(key_bytes))
        needle = prefix + key_bytes
        pos = 0
        while True:
            pos = raw_file.find(needle, pos)
            if pos == -1:
                break
            pid, off_in_obj = find_owner(pos)
            if pid is not None and pid in SKIP_PIDS:
                if pid not in skip_pid_matches:
                    skip_pid_matches[pid] = []
                skip_pid_matches[pid].append((key, off_in_obj))
            pos += 1

    if skip_pid_matches:
        print(f"FOUND {len(skip_pid_matches)} SKIP_PIDS with auto-translation matches!")
        for pid, matches in sorted(skip_pid_matches.items()):
            obj = obj_by_pid[pid]
            class_id = type_class.get(obj['type_index'], -1)
            print(f"\n  PID={pid} class_id={class_id} size={obj['size']}")
            for key, off in matches[:10]:
                print(f"    key={repr(key[:40])} at offset={off}")
    else:
        print("No auto-translation keys match in SKIP_PIDS objects. Good.")

    # -----------------------------------------------------------------------
    # PHASE 3: Check non-MonoBehaviour objects for matches
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 3: Matches in non-MonoBehaviour objects (class_id != 114)")
    print("=" * 70)

    non_mono_matches = {}
    for key, rus in auto_translations.items():
        key_bytes = key.encode('utf-8')
        prefix = struct.pack('<I', len(key_bytes))
        needle = prefix + key_bytes
        pos = 0
        while True:
            pos = raw_file.find(needle, pos)
            if pos == -1:
                break
            pid, off_in_obj = find_owner(pos)
            if pid is not None:
                obj = obj_by_pid[pid]
                class_id = type_class.get(obj['type_index'], -1)
                if class_id != 114:
                    if pid not in non_mono_matches:
                        non_mono_matches[pid] = {'class_id': class_id, 'matches': []}
                    non_mono_matches[pid]['matches'].append((key, off_in_obj))
            pos += 1

    if non_mono_matches:
        print(f"FOUND matches in {len(non_mono_matches)} non-MonoBehaviour objects!")
        for pid, info in sorted(non_mono_matches.items()):
            print(f"\n  PID={pid} class_id={info['class_id']}")
            for key, off in info['matches'][:10]:
                print(f"    key={repr(key[:50])} at offset={off}")
    else:
        print("No auto-translation keys match in non-MonoBehaviour objects. Good.")

    # -----------------------------------------------------------------------
    # PHASE 4: The CHAIN REPLACEMENT problem — check for substring collisions
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 4: Key substring collisions (short key matches inside longer key after first replacement)")
    print("=" * 70)

    # find_and_replace_strings sorts by length descending, so longer keys replace first
    # But check if any SHORT key is a binary substring of a longer key's RUSSIAN translation
    # (i.e., after translating a longer string, a short key might match in the result)

    all_keys = sorted(auto_translations.keys(), key=lambda k: len(k.encode('utf-8')), reverse=True)
    collision_found = False

    for i, long_key in enumerate(all_keys):
        long_rus = auto_translations[long_key]
        long_rus_bytes = long_rus.encode('utf-8')

        for short_key in all_keys[i+1:]:
            if len(short_key.encode('utf-8')) > len(long_rus_bytes):
                continue
            short_bytes = short_key.encode('utf-8')
            short_prefix = struct.pack('<I', len(short_bytes))
            short_needle = short_prefix + short_bytes

            # Does the short key's length-prefixed form appear in the Russian translation?
            if short_needle in (struct.pack('<I', len(long_rus_bytes)) + long_rus_bytes):
                print(f"  COLLISION: After translating '{long_key[:40]}' -> '{long_rus[:40]}'")
                print(f"    Short key '{short_key}' would match in result!")
                collision_found = True

    if not collision_found:
        print("No chain-replacement collisions found. Good.")

    # -----------------------------------------------------------------------
    # PHASE 5: Check structural corruption by simulating replacement
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 5: Simulate replacements on all objects, check structural integrity")
    print("=" * 70)

    corrupted = []
    total_modified = 0

    for obj in sorted_objs:
        pid = obj['path_id']
        if pid in SKIP_PIDS:
            continue
        class_id = type_class.get(obj['type_index'], -1)
        if class_id != 114:
            continue

        abs_offset = usf.data_offset + obj['offset']
        raw = bytes(usf.data[abs_offset:abs_offset + obj['size']])

        # Check original integrity
        orig_ok, orig_msg = check_structural_integrity(raw)
        if not orig_ok:
            # Not a standard MonoBehaviour (maybe no m_Name)
            continue

        # Apply auto-translations
        new_raw, count = find_and_replace_strings(raw, auto_translations)

        if count == 0:
            continue

        total_modified += 1

        # Check new integrity
        new_ok, new_msg = check_structural_integrity(new_raw)
        if not new_ok:
            print(f"\n  CORRUPTION DETECTED! PID={pid}")
            print(f"    Original: {orig_msg}")
            print(f"    After {count} replacements: {new_msg}")
            corrupted.append(pid)
            continue

        # Additional check: verify string at offset 20 is still valid after replacement
        # by looking for where the m_Name position shifted
        orig_name_len = struct.unpack_from('<I', raw, 20)[0]
        new_name_len = struct.unpack_from('<I', new_raw, 20)[0]
        if orig_name_len != new_name_len:
            print(f"\n  WARNING: m_Name length changed! PID={pid}")
            print(f"    Original name_len={orig_name_len}, new name_len={new_name_len}")
            print(f"    Original {orig_msg}")
            print(f"    After {count} replacements: {new_msg}")
            corrupted.append(pid)

    print(f"\nSimulated replacements on {total_modified} objects")
    if corrupted:
        print(f"CORRUPTED OBJECTS: {len(corrupted)}")
        for pid in corrupted:
            print(f"  PID={pid}")
    else:
        print("No structural corruption detected.")

    # -----------------------------------------------------------------------
    # PHASE 6: The KEY OVERLAP problem — does any key match as a SUBSTRING
    # in a DIFFERENT key's binary representation?
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 6: Key binary overlap (short key embedded in longer key's bytes)")
    print("=" * 70)

    # find_and_replace_strings searches the OBJECT DATA, not the key list.
    # But after a longer key is replaced, the position advances by new_total.
    # If a short key's length-prefix bytes appear WITHIN the longer key's text bytes,
    # a subsequent scan would match.

    # More importantly: does a short key appear as a substring of a longer key?
    # Since replacements modify data in-place and pos advances, this is about
    # whether a short key's [prefix+bytes] appears WITHIN [prefix+longer_bytes].

    overlap_found = False
    all_keys_by_len = sorted(auto_translations.keys(), key=lambda k: len(k.encode('utf-8')), reverse=True)

    for i, long_key in enumerate(all_keys_by_len):
        long_bytes = long_key.encode('utf-8')
        long_prefix = struct.pack('<I', len(long_bytes))
        full_long = long_prefix + long_bytes

        for j, short_key in enumerate(all_keys_by_len):
            if i == j:
                continue
            short_bytes = short_key.encode('utf-8')
            if len(short_bytes) >= len(long_bytes):
                continue
            short_prefix = struct.pack('<I', len(short_bytes))
            short_needle = short_prefix + short_bytes

            # Does the short needle appear INSIDE the full_long binary?
            # (i.e., starting at some offset > 0 inside full_long)
            idx = full_long.find(short_needle, 1)
            if idx != -1:
                print(f"  OVERLAP: short key '{short_key}' found at offset {idx} inside long key '{long_key[:50]}'")
                overlap_found = True

    if not overlap_found:
        print("No binary key overlaps found. Good.")

    # -----------------------------------------------------------------------
    # PHASE 7: Look for actual string that exists in GameFlow/state machine
    # objects that ALSO appears in auto-translations
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 7: Content of SKIP_PIDS 44155 and 44858 — what strings do they contain?")
    print("=" * 70)

    for pid in [44155, 44858]:
        if pid not in obj_by_pid:
            print(f"PID {pid} not found in file")
            continue
        obj = obj_by_pid[pid]
        abs_offset = usf.data_offset + obj['offset']
        raw = bytes(usf.data[abs_offset:abs_offset + obj['size']])
        class_id = type_class.get(obj['type_index'], -1)
        print(f"\nPID={pid} class_id={class_id} size={obj['size']}")

        # Extract all strings
        strings = parse_strings_from_raw(raw)
        print(f"  Contains {len(strings)} length-prefixed strings:")
        for off, slen, s in strings[:50]:
            display = repr(s[:60]) if len(s) > 60 else repr(s)
            print(f"    @{off}: [{slen}] {display}")

    # -----------------------------------------------------------------------
    # PHASE 8: Check what the patch_level3.py actually does with SKIP_PIDS
    # — does find_and_replace_strings get called on them?
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 8: Verify — do any auto keys match EXACTLY in PID 44155 or 44858?")
    print("=" * 70)

    for pid in [44155, 44858]:
        if pid not in obj_by_pid:
            continue
        obj = obj_by_pid[pid]
        abs_offset = usf.data_offset + obj['offset']
        raw = bytes(usf.data[abs_offset:abs_offset + obj['size']])

        matches_found = []
        for key, rus in auto_translations.items():
            key_bytes = key.encode('utf-8')
            prefix = struct.pack('<I', len(key_bytes))
            needle = prefix + key_bytes
            if needle in raw:
                matches_found.append(key)

        if matches_found:
            print(f"PID={pid}: {len(matches_found)} auto-keys match!")
            for k in matches_found:
                print(f"  '{k}'")
        else:
            print(f"PID={pid}: no auto-keys match (safe)")

    # -----------------------------------------------------------------------
    # PHASE 9: The REAL question — does patch_level3.py apply auto-translations
    # to SKIP_PIDS? Let's check the actual patcher source.
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 9: Check if patch_level3.py correctly skips PIDs for auto-translations")
    print("=" * 70)

    patch_level3_path = r"C:\Projects\OrwellRU\tools\patch_level3.py"
    try:
        with open(patch_level3_path, 'r', encoding='utf-8') as f:
            src = f.read()
        # Look for where auto-translations are applied
        if 'batch_level3_auto' in src:
            print("batch_level3_auto IS loaded in patch_level3.py")
        else:
            print("batch_level3_auto is NOT loaded in patch_level3.py!")

        # Check if SKIP_PIDS is applied when auto-translations are used
        lines = src.split('\n')
        for i, line in enumerate(lines):
            if 'auto' in line.lower() or 'SKIP_PIDS' in line:
                print(f"  Line {i+1}: {line.rstrip()}")
    except FileNotFoundError:
        print(f"File not found: {patch_level3_path}")

    # -----------------------------------------------------------------------
    # PHASE 10: Cross-contamination — does any auto-key appear in objects
    # that contain GAME FLOW strings (like "Aptitude Test")?
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 10: Objects containing 'Aptitude Test' or flow strings — do auto-keys match?")
    print("=" * 70)

    flow_strings = [b"Aptitude Test", b"Episode", b"Task ", b"Flow", b"State"]
    flow_objects = []

    for obj in sorted_objs:
        abs_offset = usf.data_offset + obj['offset']
        raw = bytes(usf.data[abs_offset:abs_offset + obj['size']])
        for fs in flow_strings:
            if fs in raw:
                flow_objects.append(obj['path_id'])
                break

    print(f"Found {len(flow_objects)} objects containing flow-related strings")

    for pid in flow_objects[:30]:
        obj = obj_by_pid[pid]
        class_id = type_class.get(obj['type_index'], -1)
        abs_offset = usf.data_offset + obj['offset']
        raw = bytes(usf.data[abs_offset:abs_offset + obj['size']])

        auto_matches = []
        for key, rus in auto_translations.items():
            key_bytes = key.encode('utf-8')
            prefix = struct.pack('<I', len(key_bytes))
            needle = prefix + key_bytes
            if needle in raw:
                auto_matches.append(key)

        if auto_matches:
            is_skip = pid in SKIP_PIDS
            print(f"\n  PID={pid} class_id={class_id} is_skip={is_skip} - {len(auto_matches)} auto matches!")
            for k in auto_matches[:5]:
                print(f"    '{k}'")

    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    main()
