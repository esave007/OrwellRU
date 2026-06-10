#!/usr/bin/env python3
"""
Diagnostic: scan backup/level3 and show WHERE each auto-translation hits.
For each translation from batch_level3_auto.json, shows:
- Which objects contain the source string
- How many times per object
- Object type_index and whether it's in SKIP_PIDS
- Flag DANGEROUS matches (same string in multiple objects, or in non-text fields)
"""
import os, sys, json, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

PROJECT = Path(r"C:\Projects\OrwellRU")
BACKUP = PROJECT / "backup"

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


def find_string_occurrences(data, search_str):
    """Find all occurrences of a length-prefixed UTF-8 string in binary data."""
    eng_bytes = search_str.encode('utf-8')
    prefix = struct.pack('<I', len(eng_bytes))
    needle = prefix + eng_bytes
    positions = []
    pos = 0
    while True:
        pos = data.find(needle, pos)
        if pos == -1:
            break
        positions.append(pos)
        pos += len(needle)
    return positions


def extract_all_strings(data, min_len=3):
    """Extract all length-prefixed strings from object data."""
    strings = []
    i = 0
    while i < len(data) - 4:
        slen = struct.unpack_from('<I', data, i)[0]
        if min_len <= slen <= 10000 and i + 4 + slen <= len(data):
            try:
                s = data[i+4:i+4+slen].decode('utf-8')
                if s.isprintable() or '\r' in s or '\n' in s:
                    strings.append((i, s))
                    padding = (4 - (slen % 4)) % 4
                    i += 4 + slen + padding
                    continue
            except:
                pass
        i += 1
    return strings


def main():
    print("=" * 70)
    print("DIAGNOSTIC: Auto-translation impact analysis on level3")
    print("=" * 70)

    # Load auto translations
    auto_path = PROJECT / "translated" / "batch_level3_auto.json"
    with open(auto_path, 'r', encoding='utf-8') as f:
        auto_trans = json.load(f)
    auto_trans = {k: v for k, v in auto_trans.items() if v}
    print(f"\nAuto translations loaded: {len(auto_trans)}")

    # Parse level3 backup
    print(f"\nParsing backup/level3...")
    usf = UnitySerializedFile(str(BACKUP / "level3"))
    print(f"  Objects: {len(usf.objects)}")

    # Build object data cache for MonoBehaviour objects
    print("\nScanning MonoBehaviour objects...")
    obj_data = {}  # pid -> (raw_data, type_index, class_id)
    for obj in usf.objects:
        if obj['type_index'] >= len(usf.types):
            continue
        class_id = usf.types[obj['type_index']]['class_id']
        if class_id != 114:
            continue
        raw = usf.get_object_data(obj['path_id'])
        if raw and len(raw) >= 20:
            obj_data[obj['path_id']] = (raw, obj['type_index'], class_id)

    print(f"  MonoBehaviour objects: {len(obj_data)}")
    print(f"  SKIP_PIDS: {len(SKIP_PIDS)}")

    # For each auto-translation, find where it hits
    print("\n" + "=" * 70)
    print("SCANNING EACH AUTO-TRANSLATION...")
    print("=" * 70)

    dangerous = []
    multi_hit = []
    skipped_only = []
    safe = []

    for eng, rus in sorted(auto_trans.items(), key=lambda x: len(x[0])):
        hits_in_skipped = []
        hits_in_active = []

        for pid, (raw, type_idx, cid) in obj_data.items():
            positions = find_string_occurrences(raw, eng)
            if positions:
                if pid in SKIP_PIDS:
                    hits_in_skipped.append((pid, len(positions), type_idx))
                else:
                    hits_in_active.append((pid, len(positions), type_idx))

        total_active_hits = sum(h[1] for h in hits_in_active)
        total_skip_hits = sum(h[1] for h in hits_in_skipped)

        # Categorize
        eng_display = eng.replace('\r', '\\r').replace('\n', '\\n')
        if len(eng_display) > 60:
            eng_display = eng_display[:57] + "..."

        if hits_in_active and len(hits_in_active) > 1:
            # Same string in MULTIPLE active objects — DANGEROUS
            dangerous.append((eng, rus, hits_in_active, hits_in_skipped))
        elif hits_in_active:
            safe.append((eng, rus, hits_in_active, hits_in_skipped))
        elif hits_in_skipped:
            skipped_only.append((eng, rus, hits_in_skipped))
        # else: no match at all (orphan)

    # Report DANGEROUS (multi-object hits)
    print(f"\n{'='*70}")
    print(f"DANGEROUS: String found in MULTIPLE active objects ({len(dangerous)})")
    print(f"{'='*70}")
    for eng, rus, active, skipped in dangerous:
        eng_d = eng.replace('\r', '\\r').replace('\n', '\\n')
        if len(eng_d) > 80:
            eng_d = eng_d[:77] + "..."
        print(f"\n  \"{eng_d}\"")
        print(f"  -> \"{rus[:60]}\"")
        print(f"  Active objects ({len(active)}):")
        for pid, count, tidx in active:
            print(f"    PID {pid} (type_idx={tidx}): {count} hit(s)")
        if skipped:
            print(f"  Also in SKIP objects: {[p for p,_,_ in skipped]}")

    # Report strings that ONLY hit skipped objects (translations are wasted)
    print(f"\n{'='*70}")
    print(f"SKIPPED-ONLY: String only in SKIP_PIDS objects ({len(skipped_only)})")
    print(f"{'='*70}")
    for eng, rus, skipped in skipped_only[:20]:
        eng_d = eng.replace('\r', '\\r').replace('\n', '\\n')
        print(f"  \"{eng_d[:60]}\" -> only in SKIP PIDs: {[p for p,_,_ in skipped]}")

    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"  Total auto translations: {len(auto_trans)}")
    print(f"  DANGEROUS (multi-object): {len(dangerous)}")
    print(f"  Safe (single object):     {len(safe)}")
    print(f"  Skipped-only (wasted):    {len(skipped_only)}")
    no_match = len(auto_trans) - len(dangerous) - len(safe) - len(skipped_only)
    print(f"  No match (orphan):        {no_match}")

    # Now check: for DANGEROUS entries, dump the context of each object
    if dangerous:
        print(f"\n{'='*70}")
        print(f"DEEP INSPECTION: Context around dangerous matches")
        print(f"{'='*70}")
        for eng, rus, active, skipped in dangerous[:30]:
            eng_d = eng.replace('\r', '\\r').replace('\n', '\\n')
            print(f"\n  --- \"{eng_d[:80]}\" ---")
            for pid, count, tidx in active:
                raw = obj_data[pid][0]
                all_strings = extract_all_strings(raw)
                # Find our string and show context (strings before/after)
                for idx, (offset, s) in enumerate(all_strings):
                    if s == eng or s.strip() == eng.strip():
                        print(f"\n  PID {pid} (type_idx={tidx}) — strings around match:")
                        # Show 3 before, the match, 3 after
                        start = max(0, idx - 3)
                        end = min(len(all_strings), idx + 4)
                        for j in range(start, end):
                            off, st = all_strings[j]
                            marker = " >>>" if j == idx else "    "
                            st_d = st.replace('\r', '\\r').replace('\n', '\\n')
                            if len(st_d) > 80:
                                st_d = st_d[:77] + "..."
                            print(f"  {marker} @{off}: \"{st_d}\"")
                        break


if __name__ == "__main__":
    main()
