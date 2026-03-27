#!/usr/bin/env python3
"""
Analyze level4 RectTransform layout for aptitude test fail/rejection screen.
Reads ALL RectTransforms in target pid ranges and reports sizeDelta values.
Also searches for specific text objects by their content.
"""
import os, sys, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

LEVEL4 = r"C:\Projects\OrwellRU\backup\level4"

def parse_rect_transform(raw):
    """
    Parse RectTransform (class_id=224) binary data.
    RectTransform extends Transform.

    Unity RectTransform layout (approximate):
    The data starts with GameObject reference (file_index=4 bytes, path_id=8 bytes -> 12 bytes total)
    Then localRotation (4 floats = 16 bytes)
    Then localPosition (3 floats = 12 bytes)
    Then localScale (3 floats = 12 bytes)
    Then children array count (4 bytes) + entries (12 bytes each)
    Then father (file_index=4 + path_id=8 = 12 bytes)
    Then RootOrder (4 bytes)
    Then LocalEulerAnglesHint (3 floats = 12 bytes)
    Then anchorMin (2 floats = 8 bytes)
    Then anchorMax (2 floats = 8 bytes)
    Then anchoredPosition (2 floats = 8 bytes)
    Then sizeDelta (2 floats = 8 bytes)
    Then pivot (2 floats = 8 bytes)
    """
    try:
        pos = 0
        # GameObject ref: file_index (4) + path_id (8) = 12 bytes
        pos += 12
        # localRotation (quaternion): 4 floats = 16 bytes
        pos += 16
        # localPosition: 3 floats = 12 bytes
        pos += 12
        # localScale: 3 floats = 12 bytes
        pos += 12
        # children array: count (4) + count*12 bytes
        children_count = struct.unpack_from('<i', raw, pos)[0]
        pos += 4
        pos += children_count * 12
        # father ref: 12 bytes
        pos += 12
        # RootOrder: 4 bytes
        pos += 4
        # LocalEulerAnglesHint: 3 floats = 12 bytes
        pos += 12
        # anchorMin: 2 floats = 8 bytes
        anchor_min = struct.unpack_from('<ff', raw, pos)
        pos += 8
        # anchorMax: 2 floats = 8 bytes
        anchor_max = struct.unpack_from('<ff', raw, pos)
        pos += 8
        # anchoredPosition: 2 floats = 8 bytes
        anchored_pos = struct.unpack_from('<ff', raw, pos)
        pos += 8
        # sizeDelta: 2 floats = 8 bytes
        size_delta = struct.unpack_from('<ff', raw, pos)
        pos += 8
        # pivot: 2 floats = 8 bytes
        pivot = struct.unpack_from('<ff', raw, pos)

        return {
            'children_count': children_count,
            'anchor_min': anchor_min,
            'anchor_max': anchor_max,
            'anchored_position': anchored_pos,
            'size_delta': size_delta,
            'pivot': pivot,
            'parse_ok': True
        }
    except Exception as e:
        return {'parse_ok': False, 'error': str(e)}

def find_strings_in_raw(raw):
    """Find all length-prefixed UTF-8 strings in raw data."""
    strings = []
    i = 0
    while i < len(raw) - 4:
        slen = struct.unpack_from('<I', raw, i)[0]
        if 3 <= slen <= 5000 and i + 4 + slen <= len(raw):
            try:
                s = raw[i+4:i+4+slen].decode('utf-8')
                if len(s) >= 3 and (s.isprintable() or '\r' in s or '\n' in s):
                    # Check it's actually text-like
                    printable_ratio = sum(1 for c in s if c.isprintable() or c in '\r\n\t') / len(s)
                    if printable_ratio > 0.9:
                        strings.append((i, slen, s))
                        padding = (4 - (slen % 4)) % 4
                        i += 4 + slen + padding
                        continue
            except:
                pass
        i += 1
    return strings

def parse_game_object(raw):
    """Parse GameObject (class_id=1) to get component refs and name."""
    try:
        pos = 0
        # components array: count then entries
        comp_count = struct.unpack_from('<i', raw, pos)[0]
        pos += 4
        components = []
        for _ in range(comp_count):
            file_index = struct.unpack_from('<i', raw, pos)[0]
            path_id = struct.unpack_from('<q', raw, pos+4)[0]
            components.append((file_index, path_id))
            pos += 12
        # layer (4 bytes)
        layer = struct.unpack_from('<i', raw, pos)[0]
        pos += 4
        # name (length-prefixed string)
        name_len = struct.unpack_from('<i', raw, pos)[0]
        pos += 4
        name = raw[pos:pos+name_len].decode('utf-8', errors='replace')
        return {'components': components, 'layer': layer, 'name': name}
    except Exception as e:
        return {'error': str(e)}

def main():
    print(f"Loading {LEVEL4}...")
    usf = UnitySerializedFile(LEVEL4)
    print(f"Unity: {usf.unity_version}, Objects: {len(usf.objects)}")

    # Build lookup maps
    pid_to_obj = {obj['path_id']: obj for obj in usf.objects}

    def get_class(pid):
        obj = pid_to_obj.get(pid)
        if obj:
            return usf.types[obj['type_index']]['class_id']
        return None

    def get_raw(pid):
        return usf.get_object_data(pid)

    print("\n" + "="*70)
    print("STEP 1: Check specific PIDs for text content")
    print("="*70)

    target_pids = [950, 974, 984, 991, 1010, 1016]
    for pid in target_pids:
        raw = get_raw(pid)
        if raw is None:
            print(f"\npid={pid}: NOT FOUND")
            continue
        cls = get_class(pid)
        print(f"\npid={pid} class_id={cls} size={len(raw)}:")
        strings = find_strings_in_raw(raw)
        for offset, slen, s in strings[:10]:
            preview = s[:100].replace('\r', '\\r').replace('\n', '\\n')
            print(f"  @{offset}: [{slen}] {preview}")

    print("\n" + "="*70)
    print("STEP 2: Search ALL objects for target text strings")
    print("="*70)

    search_strings = [
        "INSUFFICIENT RESULTS",
        "You failed the Aptitude test",
        "You have been lying",
        "disqualified permanently",
    ]

    found_text_pids = {}
    for obj in usf.objects:
        pid = obj['path_id']
        cls = usf.types[obj['type_index']]['class_id']
        if cls not in (114, 1):  # MonoBehaviour or GameObject
            continue
        raw = get_raw(pid)
        if not raw:
            continue
        for search in search_strings:
            if search.encode('utf-8') in raw:
                if pid not in found_text_pids:
                    found_text_pids[pid] = {'class_id': cls, 'matches': []}
                found_text_pids[pid]['matches'].append(search)

    for pid, info in sorted(found_text_pids.items()):
        raw = get_raw(pid)
        cls = info['class_id']
        print(f"\npid={pid} class_id={cls}:")
        for m in info['matches']:
            print(f"  FOUND: '{m}'")
        strings = find_strings_in_raw(raw)
        for offset, slen, s in strings[:5]:
            preview = s[:120].replace('\r', '\\r').replace('\n', '\\n')
            print(f"  @{offset}: [{slen}] {preview}")

    print("\n" + "="*70)
    print("STEP 3: ALL RectTransforms in pid range 620-700 and 820-900")
    print("="*70)

    ranges = list(range(620, 701)) + list(range(820, 901))

    for pid in ranges:
        if pid not in pid_to_obj:
            continue
        cls = get_class(pid)
        if cls != 224:
            continue
        raw = get_raw(pid)
        if not raw:
            continue
        rt = parse_rect_transform(raw)
        if rt.get('parse_ok'):
            sd = rt['size_delta']
            ap = rt['anchored_position']
            am = rt['anchor_min']
            ax = rt['anchor_max']
            print(f"  pid={pid:4d}: sizeDelta=({sd[0]:8.2f}, {sd[1]:8.2f})  "
                  f"anchoredPos=({ap[0]:8.2f}, {ap[1]:8.2f})  "
                  f"anchor=({am[0]:.2f},{am[1]:.2f})-({ax[0]:.2f},{ax[1]:.2f})  "
                  f"children={rt['children_count']}")
        else:
            print(f"  pid={pid:4d}: PARSE ERROR: {rt.get('error')}")

    print("\n" + "="*70)
    print("STEP 4: RectTransform pid=633 (title area)")
    print("="*70)

    for pid in [633, 634, 635, 636, 637, 638]:
        raw = get_raw(pid)
        if raw is None:
            print(f"pid={pid}: NOT FOUND")
            continue
        cls = get_class(pid)
        print(f"\npid={pid} class_id={cls}:")
        if cls == 224:
            rt = parse_rect_transform(raw)
            if rt.get('parse_ok'):
                print(f"  sizeDelta={rt['size_delta']}")
                print(f"  anchoredPosition={rt['anchored_position']}")
                print(f"  anchorMin={rt['anchor_min']}, anchorMax={rt['anchor_max']}")
                print(f"  pivot={rt['pivot']}, children={rt['children_count']}")
        else:
            strings = find_strings_in_raw(raw)
            for offset, slen, s in strings[:5]:
                preview = s[:100].replace('\r', '\\r').replace('\n', '\\n')
                print(f"  @{offset}: [{slen}] {preview}")

    print("\n" + "="*70)
    print("STEP 5: GameObjects referencing our target text pids")
    print("="*70)

    all_target_pids = set(target_pids) | set(found_text_pids.keys())

    for obj in usf.objects:
        pid = obj['path_id']
        cls = usf.types[obj['type_index']]['class_id']
        if cls != 1:
            continue
        raw = get_raw(pid)
        if not raw:
            continue
        go = parse_game_object(raw)
        if 'error' in go:
            continue
        comp_pids = [cp for _, cp in go['components']]
        for target in all_target_pids:
            if target in comp_pids:
                print(f"\nGameObject pid={pid} name='{go['name']}':")
                print(f"  references target pid={target}")
                print(f"  all components: {comp_pids}")
                # Find the RectTransform in the same GameObject
                for _, cpid in go['components']:
                    ccls = get_class(cpid)
                    if ccls == 224:
                        raw_rt = get_raw(cpid)
                        if raw_rt:
                            rt = parse_rect_transform(raw_rt)
                            if rt.get('parse_ok'):
                                print(f"  RectTransform pid={cpid}: sizeDelta={rt['size_delta']} "
                                      f"anchoredPos={rt['anchored_position']}")
                break

    print("\n" + "="*70)
    print("STEP 6: All RectTransforms near pids 940-1020 (aptitude fail screen area)")
    print("="*70)

    for pid in range(930, 1025):
        if pid not in pid_to_obj:
            continue
        cls = get_class(pid)
        raw = get_raw(pid)
        if not raw:
            continue

        if cls == 224:
            rt = parse_rect_transform(raw)
            if rt.get('parse_ok'):
                sd = rt['size_delta']
                ap = rt['anchored_position']
                print(f"  pid={pid:4d} [RectTransform]: sizeDelta=({sd[0]:8.2f}, {sd[1]:8.2f})  "
                      f"anchoredPos=({ap[0]:8.2f}, {ap[1]:8.2f})  children={rt['children_count']}")
        elif cls == 1:
            go = parse_game_object(raw)
            if 'name' in go:
                print(f"  pid={pid:4d} [GameObject]: '{go['name']}'  "
                      f"components={[cp for _,cp in go['components']]}")
        elif cls == 114:
            strings = find_strings_in_raw(raw)
            if strings:
                first = strings[0]
                preview = first[2][:80].replace('\r', '\\r').replace('\n', '\\n')
                print(f"  pid={pid:4d} [MonoBehaviour]: first_str='{preview}'")

    print("\n" + "="*70)
    print("STEP 7: Full layout dump — all GameObjects with RectTransforms")
    print("  (searching for aptitude/fail/rejection related names)")
    print("="*70)

    keywords = ['aptitude', 'fail', 'reject', 'result', 'insufficient', 'disqualif',
                'title', 'subtitle', 'body', 'header', 'content', 'text', 'panel',
                'popup', 'overlay', 'screen', 'lie', 'detection']

    for obj in usf.objects:
        pid = obj['path_id']
        cls = usf.types[obj['type_index']]['class_id']
        if cls != 1:
            continue
        raw = get_raw(pid)
        if not raw:
            continue
        go = parse_game_object(raw)
        if 'name' not in go:
            continue
        name_lower = go['name'].lower()
        if any(kw in name_lower for kw in keywords):
            comp_pids = [cp for _, cp in go['components']]
            rt_info = ""
            for _, cpid in go['components']:
                ccls = get_class(cpid)
                if ccls == 224:
                    raw_rt = get_raw(cpid)
                    if raw_rt:
                        rt = parse_rect_transform(raw_rt)
                        if rt.get('parse_ok'):
                            sd = rt['size_delta']
                            rt_info = f"  RT pid={cpid} sizeDelta=({sd[0]:.1f}, {sd[1]:.1f})"
            print(f"pid={pid:4d} '{go['name']}': {rt_info}")

    print("\nDone.")

if __name__ == "__main__":
    main()
