#!/usr/bin/env python3
"""
Diagnostic script: dump all RectTransforms from level4.
Investigates answer box positioning for the aptitude test.
"""
import sys, struct
sys.path.insert(0, r"C:\Projects\OrwellRU\tools")
from unity_serialized_patcher import UnitySerializedFile

HIGHLIGHT_PIDS = {900, 676, 822}
LEVEL4_PATH = r"C:\Projects\OrwellRU\backup\level4"

usf = UnitySerializedFile(LEVEL4_PATH)

# Collect all RectTransforms (class_id == 224)
rts = []
for obj in usf.objects:
    class_id = usf.types[obj['type_index']]['class_id']
    if class_id != 224:
        continue
    pid = obj['path_id']
    raw = usf.get_object_data(pid)
    if raw is None or len(raw) < 100:
        rts.append((pid, None, None, None, None, None, len(raw) if raw else 0))
        continue

    children_count = struct.unpack_from('<I', raw, 52)[0]
    anchor_off = 84 + children_count * 12
    size_off = 92 + children_count * 12

    if size_off + 8 > len(raw):
        rts.append((pid, children_count, None, None, None, None, len(raw)))
        continue

    ax, ay = struct.unpack_from('<ff', raw, anchor_off)
    sw, sh = struct.unpack_from('<ff', raw, size_off)
    rts.append((pid, children_count, ax, ay, sw, sh, len(raw)))

# Sort by path_id
rts.sort(key=lambda x: x[0])

print(f"Parsed {LEVEL4_PATH}")
print(f"Total objects: {len(usf.objects)}, RectTransforms: {len(rts)}")
print()
print(f"{'PID':>6}  {'Kids':>4}  {'anchorX':>10}  {'anchorY':>10}  {'sizeW':>10}  {'sizeH':>10}  {'rawLen':>6}  Notes")
print("-" * 95)

wide_rts = []
for pid, cc, ax, ay, sw, sh, rawlen in rts:
    notes = []
    if pid in HIGHLIGHT_PIDS:
        notes.append("*** HIGHLIGHTED ***")
    if sw is not None and sw > 1000:
        notes.append("WIDE")
        wide_rts.append((pid, cc, ax, ay, sw, sh))
    if cc is not None and ax is not None:
        line = f"{pid:>6}  {cc:>4}  {ax:>10.2f}  {ay:>10.2f}  {sw:>10.2f}  {sh:>10.2f}  {rawlen:>6}  {' '.join(notes)}"
    elif cc is not None:
        line = f"{pid:>6}  {cc:>4}  {'N/A':>10}  {'N/A':>10}  {'N/A':>10}  {'N/A':>10}  {rawlen:>6}  TOO SHORT"
    else:
        line = f"{pid:>6}  {'?':>4}  {'?':>10}  {'?':>10}  {'?':>10}  {'?':>10}  {rawlen:>6}  RAW TOO SMALL"
    print(line)

print()
print("=" * 95)
print("HIGHLIGHTED path_ids (900, 676, 822):")
print("=" * 95)
for pid, cc, ax, ay, sw, sh, rawlen in rts:
    if pid in HIGHLIGHT_PIDS:
        print(f"  PID {pid}: children={cc}, anchoredPos=({ax}, {ay}), sizeDelta=({sw}, {sh}), rawLen={rawlen}")

print()
print("=" * 95)
print(f"WIDE RectTransforms (sizeDelta.width > 1000): {len(wide_rts)}")
print("=" * 95)
for pid, cc, ax, ay, sw, sh in wide_rts:
    print(f"  PID {pid}: children={cc}, anchoredPos=({ax}, {ay}), sizeDelta=({sw}, {sh})")

# Also dump nearby objects for context around highlighted PIDs
# Check what objects are adjacent to the highlighted ones
print()
print("=" * 95)
print("CONTEXT: Objects near highlighted PIDs (within +/-10)")
print("=" * 95)
for target_pid in sorted(HIGHLIGHT_PIDS):
    print(f"\n--- Near PID {target_pid} ---")
    for obj in usf.objects:
        pid = obj['path_id']
        if abs(pid - target_pid) <= 10:
            class_id = usf.types[obj['type_index']]['class_id']
            raw = usf.get_object_data(pid)
            info = f"  PID {pid}: class_id={class_id}, size={obj['size']}"
            # If it's a MonoBehaviour (114), try to find text strings
            if class_id == 114 and raw:
                strings_found = []
                i = 0
                while i < len(raw) - 4:
                    slen = struct.unpack_from('<I', raw, i)[0]
                    if 5 <= slen <= 2000 and i + 4 + slen <= len(raw):
                        try:
                            s = raw[i+4:i+4+slen].decode('utf-8')
                            if s.isprintable() and any(c.isalpha() for c in s):
                                strings_found.append(s[:80])
                                padding = (4 - (slen % 4)) % 4
                                i += 4 + slen + padding
                                continue
                        except:
                            pass
                    i += 1
                if strings_found:
                    info += f" strings={strings_found[:3]}"
            # If RectTransform, show position
            if class_id == 224 and raw and len(raw) >= 100:
                cc = struct.unpack_from('<I', raw, 52)[0]
                aoff = 84 + cc * 12
                soff = 92 + cc * 12
                if soff + 8 <= len(raw):
                    ax2, ay2 = struct.unpack_from('<ff', raw, aoff)
                    sw2, sh2 = struct.unpack_from('<ff', raw, soff)
                    info += f" anchored=({ax2:.1f},{ay2:.1f}) size=({sw2:.1f},{sh2:.1f})"
            print(info)
