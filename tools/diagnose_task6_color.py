#!/usr/bin/env python3
"""
Diagnostic script: Investigate white text bug in Task 6 (level4 aptitude test).

Task 6 chunk boxes PIDs: 905, 921, 852, 880 (valid), 920, 731, 835 (extras)
Bug: answers 3-4 show WHITE text instead of black.

This script:
1. Finds ALL MonoBehaviour objects containing answer text (link tags)
2. Extracts color fields from TextMeshProUGUI MonoBehaviours
3. Compares Task 6 answer MB with other tasks' answer MBs
4. Dumps raw hex around color fields for analysis
"""
import os, sys, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

PROJECT = Path(r"C:\Projects\OrwellRU")
BACKUP = PROJECT / "backup" / "level4"
PATCHED = PROJECT / "patches" / "level4"


def find_strings_in_object(raw_data, min_len=10):
    """Extract all length-prefixed UTF-8 strings from raw MonoBehaviour data."""
    strings = []
    i = 0
    while i < len(raw_data) - 4:
        slen = struct.unpack_from('<I', raw_data, i)[0]
        if min_len <= slen <= 10000 and i + 4 + slen <= len(raw_data):
            try:
                s = raw_data[i+4:i+4+slen].decode('utf-8')
                if s.isprintable() or '\r' in s or '\n' in s:
                    padding = (4 - (slen % 4)) % 4
                    strings.append((i, slen, s))
                    i += 4 + slen + padding
                    continue
            except (UnicodeDecodeError, ValueError):
                pass
        i += 1
    return strings


def extract_floats_at(data, offset, count=4):
    """Extract `count` float32 values at given offset."""
    vals = []
    for j in range(count):
        if offset + j*4 + 4 <= len(data):
            vals.append(struct.unpack_from('<f', data, offset + j*4)[0])
    return vals


def find_color_patterns(data):
    """Find potential RGBA color patterns (4 consecutive floats in 0.0-1.0 range)."""
    results = []
    for i in range(0, len(data) - 15, 4):
        floats = extract_floats_at(data, i, 4)
        if len(floats) == 4:
            # Check if all 4 floats are in [0.0, 1.0] range
            if all(0.0 <= f <= 1.0 for f in floats):
                # Skip trivial all-zeros (common padding)
                if any(f != 0.0 for f in floats):
                    results.append((i, floats))
    return results


def find_color32_patterns(data):
    """Find Color32 patterns (4 bytes RGBA, commonly used in TMP)."""
    results = []
    for i in range(0, len(data) - 3):
        r, g, b, a = data[i], data[i+1], data[i+2], data[i+3]
        # Look for white (255,255,255,255) or black (0,0,0,255) or similar
        if a == 255 and (r == g == b == 255 or r == g == b == 0):
            results.append((i, r, g, b, a))
    return results


def hex_dump(data, offset, length=64):
    """Return hex dump of bytes around offset."""
    start = max(0, offset - 16)
    end = min(len(data), offset + length)
    chunk = data[start:end]
    lines = []
    for row_start in range(0, len(chunk), 16):
        row = chunk[row_start:row_start+16]
        hex_part = ' '.join(f'{b:02x}' for b in row)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        addr = start + row_start
        marker = " <<" if start + row_start <= offset < start + row_start + 16 else ""
        lines.append(f"  {addr:6d}: {hex_part:<48s} |{ascii_part}|{marker}")
    return '\n'.join(lines)


def analyze_monobehaviour(usf, pid, label=""):
    """Analyze a MonoBehaviour for text content and color fields."""
    raw = usf.get_object_data(pid)
    if raw is None:
        print(f"  PID {pid}: NOT FOUND")
        return None

    info = {
        'pid': pid,
        'size': len(raw),
        'label': label,
        'strings': [],
        'has_link_tags': False,
        'color_floats': [],
        'color32s': [],
    }

    # Extract strings
    strings = find_strings_in_object(raw, min_len=5)
    for offset, slen, s in strings:
        info['strings'].append((offset, s[:200]))
        if '<link' in s:
            info['has_link_tags'] = True

    # Find float color patterns
    info['color_floats'] = find_color_patterns(raw)

    # Find Color32 patterns
    info['color32s'] = find_color32_patterns(raw)

    return info, raw


def main():
    print("=" * 70)
    print("TASK 6 WHITE TEXT BUG — DIAGNOSTIC ANALYSIS")
    print("=" * 70)

    # =========================================================================
    # PHASE 1: Parse backup file and find all answer MonoBehaviours
    # =========================================================================
    print(f"\n--- PHASE 1: Scanning BACKUP level4 ---")
    print(f"File: {BACKUP}")
    usf = UnitySerializedFile(str(BACKUP))
    print(f"Objects: {len(usf.objects)}, Types: {len(usf.types)}")

    # Find all MonoBehaviours with <link> tags (= answer text objects)
    answer_mbs = []
    all_mb_pids = []

    for obj in usf.objects:
        if obj['type_index'] >= len(usf.types):
            continue
        class_id = usf.types[obj['type_index']]['class_id']
        if class_id != 114:
            continue
        pid = obj['path_id']
        all_mb_pids.append(pid)
        raw = usf.get_object_data(pid)
        if not raw or len(raw) < 20:
            continue
        # Quick check for <link in the raw bytes
        if b'<link' in raw:
            strings = find_strings_in_object(raw, min_len=10)
            link_strings = [(o, s) for o, s in [(ss[0], ss[2]) for ss in strings] if '<link' in s]
            if link_strings:
                answer_mbs.append((pid, len(raw), link_strings))

    print(f"\nTotal MonoBehaviours: {len(all_mb_pids)}")
    print(f"MonoBehaviours with <link> tags (answer text): {len(answer_mbs)}")

    # =========================================================================
    # PHASE 2: Identify which MB belongs to which task
    # =========================================================================
    print(f"\n--- PHASE 2: Answer MonoBehaviour identification ---")

    # Known task keywords to identify which task each MB belongs to
    task_identifiers = {
        'Task 1 (motivation)': ['securitypioneer', 'safernation', 'spyingpeople'],
        'Task 2 (statements)': ['unjustlaw', 'lying', 'understandpov'],
        'Task 3 (profile choice)': ['medicalprofile', 'datingprofile'],
        'Task 4 (dating profile)': ['registration', 'durationrelationship', 'sexual'],
        'Task 5 (medical profile)': ['size', 'fitness', 'prescriptions', 'conditions'],
        'Task 6 (friend scenario)': ['dickmove', 'warnfriend', 'ignorance', 'nothingtodo'],
        'Lie screen': ['favorable', 'truthfully'],
        'Fail screen': ['wrongfully', 'accept'],
    }

    task_mb_map = {}  # task_name -> (pid, raw_data)

    for pid, size, link_strings in answer_mbs:
        full_text = ' '.join(s for _, s in link_strings)
        identified = False
        for task_name, keywords in task_identifiers.items():
            if any(kw in full_text for kw in keywords):
                task_mb_map[task_name] = pid
                print(f"\n  PID {pid} ({size} bytes) = {task_name}")
                # Show first 100 chars of first link string
                first_str = link_strings[0][1]
                print(f"    Text preview: {first_str[:120]}...")
                identified = True
                break
        if not identified:
            print(f"\n  PID {pid} ({size} bytes) = UNKNOWN")
            for _, s in link_strings:
                print(f"    Text: {s[:100]}...")

    # =========================================================================
    # PHASE 3: Deep comparison of color fields
    # =========================================================================
    print(f"\n--- PHASE 3: Color field comparison ---")

    # Compare Task 1 (known good, black text) vs Task 6 (bugged, white text)
    compare_tasks = ['Task 1 (motivation)', 'Task 2 (statements)', 'Task 3 (profile choice)',
                     'Task 4 (dating profile)', 'Task 5 (medical profile)',
                     'Task 6 (friend scenario)', 'Lie screen', 'Fail screen']

    for task_name in compare_tasks:
        if task_name not in task_mb_map:
            print(f"\n  {task_name}: NOT FOUND in level4")
            continue

        pid = task_mb_map[task_name]
        raw = usf.get_object_data(pid)
        print(f"\n  === {task_name} (PID={pid}, {len(raw)} bytes) ===")

        # Find all float color candidates
        colors = find_color_patterns(raw)
        # Filter to likely color fields (at least one component > 0)
        notable_colors = [(off, vals) for off, vals in colors
                         if not all(0.99 < v < 1.01 for v in vals)]  # skip all-1.0
        notable_colors = [(off, vals) for off, vals in notable_colors
                         if not (vals[0] == vals[1] == vals[2] == 0.0 and vals[3] == 0.0)]  # skip 0,0,0,0

        print(f"    Float color candidates ({len(colors)} total, {len(notable_colors)} notable):")
        for off, vals in colors[:30]:  # Show first 30
            label = ""
            r, g, b, a = vals
            if r == g == b == 0.0 and a == 1.0:
                label = " << BLACK (0,0,0,1)"
            elif r == g == b == 1.0 and a == 1.0:
                label = " << WHITE (1,1,1,1)"
            elif r == g == b == 1.0 and 0.0 < a < 1.0:
                label = f" << WHITE alpha={a:.3f}"
            elif 0.0 < r < 1.0 or 0.0 < g < 1.0 or 0.0 < b < 1.0:
                label = f" << COLORED"
            print(f"      @{off:5d}: R={r:.4f} G={g:.4f} B={b:.4f} A={a:.4f}{label}")

    # =========================================================================
    # PHASE 4: Byte-level diff between Task 1 MB and Task 6 MB
    # =========================================================================
    print(f"\n--- PHASE 4: Structural comparison Task 1 vs Task 6 ---")

    task1_pid = task_mb_map.get('Task 1 (motivation)')
    task6_pid = task_mb_map.get('Task 6 (friend scenario)')

    if task1_pid and task6_pid:
        raw1 = usf.get_object_data(task1_pid)
        raw6 = usf.get_object_data(task6_pid)

        print(f"  Task 1 PID={task1_pid}: {len(raw1)} bytes")
        print(f"  Task 6 PID={task6_pid}: {len(raw6)} bytes")

        # The MonoBehaviour header structure before the m_text field:
        # Bytes 0-3: m_GameObject (PPtr file_index)
        # Bytes 4-11: m_GameObject (PPtr path_id)
        # Byte 12: m_Enabled
        # Bytes 13-15: padding
        # Bytes 16-19: m_Script (PPtr file_index)
        # Bytes 20-27: m_Script (PPtr path_id)
        # Bytes 28-31: m_Name (length), then m_Name string...
        # Then the TextMeshProUGUI specific fields...

        # Dump first 200 bytes of each (before text starts) for comparison
        print(f"\n  Task 1 header (first 200 bytes):")
        print(hex_dump(raw1, 0, 200))

        print(f"\n  Task 6 header (first 200 bytes):")
        print(hex_dump(raw6, 0, 200))

        # Find where m_text starts (look for the link text)
        for label, raw, pid in [("Task 1", raw1, task1_pid), ("Task 6", raw6, task6_pid)]:
            text_pos = raw.find(b'<link')
            if text_pos > 0:
                # The 4 bytes before <link is part of the length-prefix
                str_len_pos = text_pos - 4
                str_len = struct.unpack_from('<I', raw, str_len_pos)[0]
                print(f"\n  {label} m_text starts at offset {str_len_pos} (len={str_len})")
                print(f"    Bytes BEFORE m_text (offsets {max(0,str_len_pos-80)} to {str_len_pos}):")
                print(hex_dump(raw, max(0, str_len_pos - 80), 80))

                # After the text string + padding, there are more fields (colors etc.)
                text_end = text_pos + str_len
                text_padding = (4 - (str_len % 4)) % 4
                after_text = text_end + text_padding
                remaining = len(raw) - after_text
                print(f"\n    Bytes AFTER m_text (offset {after_text}, {remaining} bytes remaining):")
                print(hex_dump(raw, after_text, min(remaining, 400)))

    # =========================================================================
    # PHASE 5: Check the PATCHED file too (if exists)
    # =========================================================================
    if PATCHED.exists():
        print(f"\n--- PHASE 5: Checking PATCHED level4 ---")
        usf_p = UnitySerializedFile(str(PATCHED))

        for task_name in ['Task 1 (motivation)', 'Task 6 (friend scenario)']:
            if task_name not in task_mb_map:
                continue
            pid = task_mb_map[task_name]
            raw_b = usf.get_object_data(pid)
            raw_p = usf_p.get_object_data(pid)

            if raw_b and raw_p:
                print(f"\n  {task_name} PID={pid}:")
                print(f"    Backup size:  {len(raw_b)} bytes")
                print(f"    Patched size: {len(raw_p)} bytes")

                if raw_b == raw_p:
                    print(f"    IDENTICAL (no changes)")
                else:
                    # Find differences
                    diffs = []
                    min_len = min(len(raw_b), len(raw_p))
                    for i in range(min_len):
                        if raw_b[i] != raw_p[i]:
                            diffs.append(i)
                    if len(raw_b) != len(raw_p):
                        diffs.append(min_len)
                    print(f"    Differences at {len(diffs)} byte positions")
                    if diffs:
                        first_diff = diffs[0]
                        last_diff = diffs[-1]
                        print(f"    First diff at offset {first_diff}, last at {last_diff}")

                        # Check if differences are only in the text area
                        text_pos_b = raw_b.find(b'<link')
                        text_pos_p = raw_p.find(b'<link')
                        if text_pos_b > 0:
                            print(f"    Text starts: backup={text_pos_b-4}, patched={text_pos_p-4 if text_pos_p > 0 else 'N/A'}")
                            if first_diff >= text_pos_b - 4:
                                print(f"    -> Diffs are WITHIN text area (translation only)")
                            else:
                                print(f"    -> WARNING: Diffs BEFORE text area (structural change!)")
                                print(f"    Backup bytes around first diff:")
                                print(hex_dump(raw_b, first_diff, 32))
                                print(f"    Patched bytes around first diff:")
                                print(hex_dump(raw_p, first_diff, 32))

                # Check post-text colors in patched version
                raw = raw_p
                text_pos = raw.find(b'<link')
                if text_pos > 0:
                    str_len_pos = text_pos - 4
                    str_len = struct.unpack_from('<I', raw, str_len_pos)[0]
                    text_end = text_pos + str_len
                    text_padding = (4 - (str_len % 4)) % 4
                    after_text = text_end + text_padding
                    remaining = len(raw) - after_text

                    # Look for color fields after text
                    post_text = raw[after_text:]
                    post_colors = find_color_patterns(post_text)
                    if post_colors:
                        print(f"\n    PATCHED post-text color floats:")
                        for off, vals in post_colors[:20]:
                            r, g, b, a = vals
                            label = ""
                            if r == g == b == 0.0 and a == 1.0:
                                label = " << BLACK"
                            elif r == g == b == 1.0 and a == 1.0:
                                label = " << WHITE"
                            print(f"      @{after_text + off}: R={r:.4f} G={g:.4f} B={b:.4f} A={a:.4f}{label}")

    # =========================================================================
    # PHASE 6: Check chunk box RectTransform PIDs for references
    # =========================================================================
    print(f"\n--- PHASE 6: Chunk box RectTransform analysis ---")

    task6_chunk_pids = {
        'valid': [905, 921, 852, 880],
        'extras': [920, 731, 835],
    }

    for group, pids in task6_chunk_pids.items():
        print(f"\n  Task 6 {group} chunk boxes:")
        for pid in pids:
            raw = usf.get_object_data(pid)
            if raw is None:
                print(f"    PID {pid}: NOT FOUND")
                continue
            class_id = usf.get_class_id(pid)
            print(f"    PID {pid}: class={class_id}, {len(raw)} bytes")

            if class_id == 224:  # RectTransform
                children_count = struct.unpack_from('<I', raw, 52)[0]
                size_offset = 92 + children_count * 12
                anchor_y_offset = 88 + children_count * 12
                anchor_x_offset = 84 + children_count * 12
                if size_offset + 8 <= len(raw):
                    w, h = struct.unpack_from('<ff', raw, size_offset)
                    ax, ay = struct.unpack_from('<ff', raw, anchor_x_offset)
                    print(f"      children={children_count}, size=({w:.2f}, {h:.2f}), anchor=({ax:.2f}, {ay:.2f})")

    # =========================================================================
    # PHASE 7: Look for m_fontColor / m_Color fields via known TMP offsets
    # =========================================================================
    print(f"\n--- PHASE 7: TMP color field analysis (byte-level) ---")

    # TextMeshProUGUI inherits from TMP_Text which has:
    # - m_fontColor (Color: 4 floats, RGBA)
    # - m_fontColor32 (Color32: 4 bytes, RGBA)
    # - m_color (from Graphic base: Color, 4 floats)
    # These are after the m_text field in the serialized data.

    # Let's find these by looking for specific float patterns after the text
    for task_name in compare_tasks:
        if task_name not in task_mb_map:
            continue
        pid = task_mb_map[task_name]
        raw = usf.get_object_data(pid)

        text_pos = raw.find(b'<link')
        if text_pos <= 0:
            continue

        str_len_pos = text_pos - 4
        str_len = struct.unpack_from('<I', raw, str_len_pos)[0]
        text_end = text_pos + str_len
        text_padding = (4 - (str_len % 4)) % 4
        after_text = text_end + text_padding

        post_data = raw[after_text:]
        print(f"\n  {task_name} (PID={pid}): post-text data = {len(post_data)} bytes")

        # Look for float-based colors
        colors = find_color_patterns(post_data)
        if colors:
            print(f"    Float RGBA candidates:")
            for off, vals in colors[:25]:
                r, g, b, a = vals
                abs_off = after_text + off
                label = ""
                if abs(r) < 0.001 and abs(g) < 0.001 and abs(b) < 0.001 and abs(a - 1.0) < 0.001:
                    label = " << BLACK"
                elif abs(r - 1.0) < 0.001 and abs(g - 1.0) < 0.001 and abs(b - 1.0) < 0.001 and abs(a - 1.0) < 0.001:
                    label = " << WHITE"
                elif abs(r - 0.1961) < 0.01 and abs(g - 0.1961) < 0.01 and abs(b - 0.1961) < 0.01:
                    label = " << DARK GRAY (0.196)"
                print(f"      @{abs_off:5d} (post+{off:3d}): R={r:.6f} G={g:.6f} B={b:.6f} A={a:.6f}{label}")

        # Also dump Color32 candidates
        c32 = find_color32_patterns(post_data)
        if c32:
            print(f"    Color32 candidates (first 10):")
            for off, r, g, b, a in c32[:10]:
                abs_off = after_text + off
                label = "WHITE" if r == 255 else "BLACK"
                print(f"      @{abs_off:5d} (post+{off:3d}): R={r} G={g} B={b} A={a} = {label}")

    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
