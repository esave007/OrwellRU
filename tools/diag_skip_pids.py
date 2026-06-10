#!/usr/bin/env python3
"""
Diagnostic: scan backup/resources.assets for ALL gameflow/state controller
MonoBehaviour objects that should NOT be translated.
"""
import os, sys, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(__file__))
from unity_serialized_patcher import UnitySerializedFile

BACKUP = r"C:\Projects\OrwellRU\backup\resources.assets"

# Current SKIP_PIDS from patch_resources_mono.py
CURRENT_SKIP = {
    696, 697, 698, 699, 700,
    733, 734, 735, 736, 737, 738, 739, 740, 741, 742,
    796, 797, 798, 799, 800, 801, 802, 803, 804, 805,
    806, 807, 808, 809, 810, 811, 812, 813, 814, 815,
    816, 817, 818, 819, 820, 821, 822, 823, 824, 825,
    826, 827, 828,
    4988,
}

MARKERS = [
    (b"Assets/Resources", "Assets/Resources"),
    (b"Gameflow", "Gameflow"),
    (b"GameFlow", "GameFlow"),
    (b"FlowState", "FlowState"),
    (b"website_", "website_"),
    (b"IfElseState", "IfElseState"),
    (b"WaitState", "WaitState"),
    (b"ChangeVariableState", "ChangeVariableState"),
    (b"DocumentViewedState", "DocumentViewedState"),
    (b"NewBookmarkState", "NewBookmarkState"),
    (b"NewChatMessageState", "NewChatMessageState"),
    (b"NewCommentaryState", "NewCommentaryState"),
    (b"UpdateProfileState", "UpdateProfileState"),
    (b"AtClockTimeState", "AtClockTimeState"),
    (b"NewDataChunkState", "NewDataChunkState"),
    (b"_task_", "_task_"),
    (b"data_task", "data_task"),
]

SPECIAL_PIDS = {4989, 4990, 4991, 4992, 4993, 4994}

print(f"Parsing {BACKUP}...")
usf = UnitySerializedFile(BACKUP)
print(f"  Unity: {usf.unity_version}, Objects: {len(usf.objects)}, Types: {len(usf.types)}")

# Find type_index for PID 4988
pid4988_type_index = None
for obj in usf.objects:
    if obj['path_id'] == 4988:
        pid4988_type_index = obj['type_index']
        break

print(f"\n=== PID 4988 type_index: {pid4988_type_index} ===")
if pid4988_type_index is not None:
    t = usf.types[pid4988_type_index]
    print(f"  class_id={t['class_id']}, script_type_index={t['script_type_index']}")
    print(f"  script_hash={t['script_hash'].hex() if t['script_hash'] else None}")
    print(f"  type_hash={t['type_hash'].hex()}")

# List ALL objects with the same type_index as PID 4988
print(f"\n=== ALL objects with type_index={pid4988_type_index} (same type as PID 4988) ===")
same_type_pids = []
for obj in usf.objects:
    if obj['type_index'] == pid4988_type_index:
        same_type_pids.append(obj['path_id'])
        in_skip = "IN SKIP_PIDS" if obj['path_id'] in CURRENT_SKIP else "NOT in SKIP_PIDS"
        print(f"  PID {obj['path_id']:5d}  size={obj['size']:6d}  [{in_skip}]")
print(f"  Total: {len(same_type_pids)} objects")

# Scan ALL MonoBehaviour objects for markers
print(f"\n=== Scanning ALL MonoBehaviour (class_id=114) for gameflow markers ===")
gameflow_pids = set()
all_mono_pids = []

for obj in usf.objects:
    if obj['type_index'] >= len(usf.types):
        continue
    class_id = usf.types[obj['type_index']]['class_id']
    if class_id != 114:
        continue
    all_mono_pids.append(obj['path_id'])

    raw = usf.get_object_data(obj['path_id'])
    if not raw:
        continue

    found_markers = []
    for marker_bytes, marker_name in MARKERS:
        if marker_bytes in raw:
            found_markers.append(marker_name)

    if found_markers:
        gameflow_pids.add(obj['path_id'])
        in_skip = "SKIP" if obj['path_id'] in CURRENT_SKIP else "MISS"
        special = " *** SPECIAL ***" if obj['path_id'] in SPECIAL_PIDS else ""
        print(f"  [{in_skip}] PID {obj['path_id']:5d}  size={obj['size']:6d}  markers: {', '.join(found_markers)}{special}")

print(f"\n  Total MonoBehaviour objects: {len(all_mono_pids)}")
print(f"  Objects with gameflow markers: {len(gameflow_pids)}")

# Check special PIDs specifically
print(f"\n=== Special PIDs 4989-4994 detailed examination ===")
for pid in sorted(SPECIAL_PIDS):
    found = False
    for obj in usf.objects:
        if obj['path_id'] == pid:
            found = True
            class_id = usf.types[obj['type_index']]['class_id']
            raw = usf.get_object_data(pid)
            ti = obj['type_index']
            same_as_4988 = "YES - same type as PID 4988!" if ti == pid4988_type_index else f"NO (type_index={ti})"
            print(f"\n  PID {pid}: class_id={class_id}, type_index={ti}, size={obj['size']}")
            print(f"    Same type as 4988? {same_as_4988}")

            # Check markers
            found_markers = []
            for marker_bytes, marker_name in MARKERS:
                if marker_bytes in raw:
                    found_markers.append(marker_name)
            if found_markers:
                print(f"    Markers: {', '.join(found_markers)}")
            else:
                print(f"    No gameflow markers found")

            # Show strings in this object
            print(f"    Strings found:")
            i = 0
            str_count = 0
            while i < len(raw) - 4 and str_count < 20:
                slen = struct.unpack_from('<I', raw, i)[0]
                if 3 <= slen <= 2000 and i + 4 + slen <= len(raw):
                    try:
                        s = raw[i+4:i+4+slen].decode('utf-8')
                        if s.isprintable() and not all(c == '\x00' for c in s):
                            print(f"      @{i}: [{slen}] {s[:120]}")
                            str_count += 1
                            padding = (4 - (slen % 4)) % 4
                            i += 4 + slen + padding
                            continue
                    except:
                        pass
                i += 1
            break
    if not found:
        print(f"\n  PID {pid}: NOT FOUND in resources.assets")

# Cross-reference: missing from SKIP_PIDS
missing = gameflow_pids - CURRENT_SKIP
extra = CURRENT_SKIP - gameflow_pids

print(f"\n=== CROSS-REFERENCE ===")
print(f"  Current SKIP_PIDS count: {len(CURRENT_SKIP)}")
print(f"  Gameflow PIDs detected: {len(gameflow_pids)}")
print(f"\n  PIDs MISSING from SKIP_PIDS (should be added):")
for pid in sorted(missing):
    # Get size
    for obj in usf.objects:
        if obj['path_id'] == pid:
            raw = usf.get_object_data(pid)
            found_m = []
            for mb, mn in MARKERS:
                if mb in raw:
                    found_m.append(mn)
            print(f"    PID {pid:5d}  size={obj['size']:6d}  type_index={obj['type_index']}  markers: {', '.join(found_m)}")
            break

print(f"\n  PIDs in SKIP_PIDS but NO markers detected:")
for pid in sorted(extra):
    for obj in usf.objects:
        if obj['path_id'] == pid:
            print(f"    PID {pid:5d}  size={obj['size']:6d}  type_index={obj['type_index']}")
            break

# Also check: all type_indexes used by current SKIP_PIDS
print(f"\n=== Type indexes used by SKIP_PIDS ===")
skip_type_indexes = {}
for obj in usf.objects:
    if obj['path_id'] in CURRENT_SKIP:
        ti = obj['type_index']
        if ti not in skip_type_indexes:
            skip_type_indexes[ti] = []
        skip_type_indexes[ti].append(obj['path_id'])

for ti in sorted(skip_type_indexes.keys()):
    t = usf.types[ti]
    pids = skip_type_indexes[ti]
    print(f"  type_index={ti}: class_id={t['class_id']}, script_type_index={t['script_type_index']}, count={len(pids)}")
    print(f"    PIDs: {sorted(pids)}")
    # Find ALL objects with this type_index that are NOT in SKIP_PIDS
    all_with_ti = [o['path_id'] for o in usf.objects if o['type_index'] == ti]
    not_in_skip = [p for p in all_with_ti if p not in CURRENT_SKIP]
    if not_in_skip:
        print(f"    NOT in SKIP_PIDS with same type_index: {sorted(not_in_skip)}")

# Final summary
print(f"\n{'='*60}")
print(f"FINAL SUMMARY: Complete set of PIDs to add to SKIP_PIDS")
print(f"{'='*60}")
if missing:
    print(f"  Add these {len(missing)} PIDs:")
    for pid in sorted(missing):
        print(f"    {pid}")
    print(f"\n  Python set literal to add:")
    print(f"    {{{', '.join(str(p) for p in sorted(missing))}}}")
else:
    print(f"  No additional PIDs needed - SKIP_PIDS is complete!")

# Also list by type_index for completeness
print(f"\n=== All objects sharing type_index with SKIP_PIDS but not in SKIP_PIDS ===")
all_missing_by_type = set()
for ti in skip_type_indexes:
    for obj in usf.objects:
        if obj['type_index'] == ti and obj['path_id'] not in CURRENT_SKIP:
            all_missing_by_type.add(obj['path_id'])
            raw = usf.get_object_data(obj['path_id'])
            has_markers = any(mb in raw for mb, _ in MARKERS)
            marker_flag = "HAS MARKERS" if has_markers else "no markers"
            print(f"  PID {obj['path_id']:5d}  type_index={ti}  size={obj['size']:6d}  [{marker_flag}]")

if all_missing_by_type:
    print(f"\n  Complete recommended SKIP_PIDS addition (by type + markers):")
    print(f"    {{{', '.join(str(p) for p in sorted(all_missing_by_type))}}}")
