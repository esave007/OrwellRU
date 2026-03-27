#!/usr/bin/env python3
"""
Precisely parse RectTransform objects for the aptitude test fail screen.
Focuses on pids found in Step 5: 633, 737, 764, 787, 870, 896
and their parent GameObjects.

Also does a hex dump to reverse-engineer the correct RectTransform layout
for Unity 5.6.3f1.
"""
import os, sys, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

LEVEL4 = r"C:\Projects\OrwellRU\backup\level4"

def hexdump(data, max_bytes=256):
    """Print a hex dump of data."""
    lines = []
    for i in range(0, min(len(data), max_bytes), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f'  {i:04x}: {hex_part:<48}  {ascii_part}')
    return '\n'.join(lines)

def parse_rect_transform_v2(raw, verbose=False):
    """
    Carefully parse RectTransform from Unity 5.6.3f1.

    The actual layout based on Unity 5.6.x source:

    Transform (base):
      m_GameObject: PPtr (file_index=int32, path_id=int64) = 12 bytes
      m_LocalRotation: Quaternion (4 floats) = 16 bytes
      m_LocalPosition: Vector3 (3 floats) = 12 bytes
      m_LocalScale: Vector3 (3 floats) = 12 bytes
      m_Children: Array<PPtr<Transform>> = 4 + N*12 bytes
      m_Father: PPtr<Transform> = 12 bytes
      m_RootOrder: int = 4 bytes
      m_LocalEulerAnglesHint: Vector3 = 12 bytes

    RectTransform (extends Transform):
      m_AnchorMin: Vector2 = 8 bytes
      m_AnchorMax: Vector2 = 8 bytes
      m_AnchoredPosition: Vector2 = 8 bytes
      m_SizeDelta: Vector2 = 8 bytes
      m_Pivot: Vector2 = 8 bytes

    Total without children: 12+16+12+12+4+0*12+12+4+12 = 84 bytes base
    Then 5 Vector2s = 40 bytes
    Total minimum: 124 bytes
    """
    pos = 0
    result = {}

    if verbose:
        print(f"  raw size: {len(raw)}")

    # m_GameObject: file_index (4) + path_id (8) = 12 bytes
    if pos + 12 > len(raw):
        return None
    file_index = struct.unpack_from('<i', raw, pos)[0]
    path_id = struct.unpack_from('<q', raw, pos+4)[0]
    result['go_file_index'] = file_index
    result['go_path_id'] = path_id
    pos += 12

    # m_LocalRotation: 4 floats = 16 bytes
    if pos + 16 > len(raw):
        return None
    rot = struct.unpack_from('<ffff', raw, pos)
    result['local_rotation'] = rot
    pos += 16

    # m_LocalPosition: 3 floats = 12 bytes
    if pos + 12 > len(raw):
        return None
    lpos = struct.unpack_from('<fff', raw, pos)
    result['local_position'] = lpos
    pos += 12

    # m_LocalScale: 3 floats = 12 bytes
    if pos + 12 > len(raw):
        return None
    scale = struct.unpack_from('<fff', raw, pos)
    result['local_scale'] = scale
    pos += 12

    # m_Children array: count (4) + count*12 bytes
    if pos + 4 > len(raw):
        return None
    children_count = struct.unpack_from('<i', raw, pos)[0]
    result['children_count'] = children_count
    pos += 4

    if verbose:
        print(f"  children_count={children_count}, pos after children_count={pos}")

    children = []
    for i in range(children_count):
        if pos + 12 > len(raw):
            return None
        ci = struct.unpack_from('<i', raw, pos)[0]
        cp = struct.unpack_from('<q', raw, pos+4)[0]
        children.append((ci, cp))
        pos += 12
    result['children'] = children

    # m_Father: file_index (4) + path_id (8) = 12 bytes
    if pos + 12 > len(raw):
        return None
    father_fi = struct.unpack_from('<i', raw, pos)[0]
    father_pid = struct.unpack_from('<q', raw, pos+4)[0]
    result['father'] = (father_fi, father_pid)
    pos += 12

    # m_RootOrder: int (4 bytes)
    if pos + 4 > len(raw):
        return None
    root_order = struct.unpack_from('<i', raw, pos)[0]
    result['root_order'] = root_order
    pos += 4

    # m_LocalEulerAnglesHint: 3 floats = 12 bytes
    if pos + 12 > len(raw):
        return None
    euler = struct.unpack_from('<fff', raw, pos)
    result['local_euler'] = euler
    pos += 12

    if verbose:
        print(f"  pos before RectTransform fields: {pos}")

    # === RectTransform fields ===
    # m_AnchorMin: 2 floats = 8 bytes
    if pos + 8 > len(raw):
        if verbose:
            print(f"  ERROR: need anchorMin at {pos}, only {len(raw)} bytes")
        return None
    anchor_min = struct.unpack_from('<ff', raw, pos)
    result['anchor_min'] = anchor_min
    pos += 8

    # m_AnchorMax: 2 floats = 8 bytes
    if pos + 8 > len(raw):
        return None
    anchor_max = struct.unpack_from('<ff', raw, pos)
    result['anchor_max'] = anchor_max
    pos += 8

    # m_AnchoredPosition: 2 floats = 8 bytes
    if pos + 8 > len(raw):
        return None
    anchored_pos = struct.unpack_from('<ff', raw, pos)
    result['anchored_position'] = anchored_pos
    pos += 8

    # m_SizeDelta: 2 floats = 8 bytes
    if pos + 8 > len(raw):
        return None
    size_delta = struct.unpack_from('<ff', raw, pos)
    result['size_delta'] = size_delta
    result['size_delta_offset'] = pos  # IMPORTANT: offset for patching
    pos += 8

    # m_Pivot: 2 floats = 8 bytes
    if pos + 8 > len(raw):
        return None
    pivot = struct.unpack_from('<ff', raw, pos)
    result['pivot'] = pivot
    pos += 8

    result['parsed_bytes'] = pos
    result['total_bytes'] = len(raw)
    return result

def parse_game_object(raw):
    """Parse GameObject to get components and name."""
    try:
        pos = 0
        comp_count = struct.unpack_from('<i', raw, pos)[0]
        pos += 4
        components = []
        for _ in range(comp_count):
            fi = struct.unpack_from('<i', raw, pos)[0]
            pid = struct.unpack_from('<q', raw, pos+4)[0]
            components.append((fi, pid))
            pos += 12
        layer = struct.unpack_from('<i', raw, pos)[0]
        pos += 4
        name_len = struct.unpack_from('<i', raw, pos)[0]
        pos += 4
        name = raw[pos:pos+name_len].decode('utf-8', errors='replace')
        return {'components': components, 'layer': layer, 'name': name}
    except Exception as e:
        return {'error': str(e)}

def find_strings_in_raw(raw):
    """Find length-prefixed UTF-8 strings."""
    strings = []
    i = 0
    while i < len(raw) - 4:
        slen = struct.unpack_from('<I', raw, i)[0]
        if 3 <= slen <= 5000 and i + 4 + slen <= len(raw):
            try:
                s = raw[i+4:i+4+slen].decode('utf-8')
                if len(s) >= 3:
                    printable = sum(1 for c in s if c.isprintable() or c in '\r\n\t') / len(s)
                    if printable > 0.85:
                        strings.append((i, slen, s))
                        padding = (4 - (slen % 4)) % 4
                        i += 4 + slen + padding
                        continue
            except:
                pass
        i += 1
    return strings

def main():
    print(f"Loading {LEVEL4}...")
    usf = UnitySerializedFile(LEVEL4)
    print(f"Unity: {usf.unity_version}, Objects: {len(usf.objects)}")

    pid_to_obj = {obj['path_id']: obj for obj in usf.objects}

    def get_class(pid):
        obj = pid_to_obj.get(pid)
        if obj:
            return usf.types[obj['type_index']]['class_id']
        return None

    def get_raw(pid):
        return usf.get_object_data(pid)

    print("\n" + "="*70)
    print("TARGET TEXT OBJECTS AND THEIR RECTTRANSFORMS")
    print("="*70)

    # From Step 5 results:
    # pid=4   GameObject 'txt_'           -> components [633, 361, 950]   text=pid950 "INSUFFICIENT RESULTS"
    # pid=119 GameObject 'txt_'           -> components [737, 441, 974]   text=pid974 "You failed..."
    # pid=148 GameObject 'txt_'           -> components [764, 466, 984]   text=pid984 lie detection body
    # pid=173 GameObject 'txt_'           -> components [787, 487, 991]   text=pid991 rejection body
    # pid=265 GameObject 'txt_ (chunks)'  -> components [870, 550, 1010, ...] text=pid1010 answer choices
    # pid=292 GameObject 'txt_'           -> components [896, 568, 1016]  text=pid1016 "You have been lying!"

    targets = [
        (4,   633, 950,  "INSUFFICIENT RESULTS (title)"),
        (119, 737, 974,  "You failed... (subtitle fail)"),
        (148, 764, 984,  "Lie detection body text"),
        (173, 787, 991,  "Rejection body text"),
        (265, 870, 1010, "Answer choices"),
        (292, 896, 1016, "You have been lying! (subtitle lie)"),
    ]

    for go_pid, rt_pid, txt_pid, label in targets:
        print(f"\n--- {label} ---")
        print(f"  GameObject pid={go_pid}, RectTransform pid={rt_pid}, Text pid={txt_pid}")

        # Show full text content
        raw_txt = get_raw(txt_pid)
        if raw_txt:
            strs = find_strings_in_raw(raw_txt)
            for offset, slen, s in strs:
                preview = s[:200].replace('\r', '\\r').replace('\n', '\\n')
                if len(preview) > 20 and 'UnityEngine' not in preview:
                    print(f"  TEXT @{offset}: [{slen}] {preview}")

        # Parse RectTransform
        raw_rt = get_raw(rt_pid)
        if raw_rt is None:
            print(f"  RectTransform pid={rt_pid}: NOT FOUND")
            continue

        rt = parse_rect_transform_v2(raw_rt, verbose=True)
        if rt:
            print(f"  RT: size={len(raw_rt)} bytes, parsed={rt['parsed_bytes']}")
            print(f"  sizeDelta: {rt['size_delta']} (offset in raw: {rt['size_delta_offset']})")
            print(f"  anchoredPosition: {rt['anchored_position']}")
            print(f"  anchorMin: {rt['anchor_min']}, anchorMax: {rt['anchor_max']}")
            print(f"  pivot: {rt['pivot']}")
            print(f"  local_position: {rt['local_position']}")
            print(f"  children_count: {rt['children_count']}")
            print(f"  father pid: {rt['father'][1]}")
            print(f"  root_order: {rt['root_order']}")
        else:
            print(f"  RectTransform pid={rt_pid}: PARSE FAILED")
            print(f"  Raw size: {len(raw_rt)}")
            print(f"  Hex dump:")
            print(hexdump(raw_rt))

    print("\n" + "="*70)
    print("HEX DUMPS of RectTransforms (first 160 bytes each)")
    print("="*70)

    rt_pids = [633, 737, 764, 787, 870, 896]
    for pid in rt_pids:
        raw = get_raw(pid)
        if raw is None:
            print(f"\npid={pid}: NOT FOUND")
            continue
        cls = get_class(pid)
        print(f"\npid={pid} class_id={cls} size={len(raw)}:")
        print(hexdump(raw, 200))

        # Try interpreting last 40 bytes as 10 floats (the 5 Vector2 fields)
        if len(raw) >= 40:
            last40 = raw[-40:]
            floats = struct.unpack_from('<ffffffffff', last40)
            print(f"  Last 40 bytes as 10 floats: {[f'{f:.4f}' for f in floats]}")
            print(f"  Interpreted: anchorMin=({floats[0]:.3f},{floats[1]:.3f}) "
                  f"anchorMax=({floats[2]:.3f},{floats[3]:.3f}) "
                  f"anchoredPos=({floats[4]:.2f},{floats[5]:.2f}) "
                  f"sizeDelta=({floats[6]:.2f},{floats[7]:.2f}) "
                  f"pivot=({floats[8]:.3f},{floats[9]:.3f})")

    print("\n" + "="*70)
    print("PARENT HIERARCHY SEARCH")
    print("="*70)

    # Find parent GameObjects/RectTransforms for our targets
    # by searching for GameObjects that contain our target RectTransforms as children

    # First, build a map of RectTransform -> parent via father field
    rt_parent_map = {}
    for obj in usf.objects:
        pid = obj['path_id']
        cls = usf.types[obj['type_index']]['class_id']
        if cls != 224:
            continue
        raw = get_raw(pid)
        if not raw:
            continue
        rt = parse_rect_transform_v2(raw)
        if rt and rt.get('father'):
            father_pid = rt['father'][1]
            rt_parent_map[pid] = father_pid

    # Trace parent chain for our RectTransforms
    for rt_pid in [633, 737, 764, 787, 870, 896]:
        chain = [rt_pid]
        current = rt_pid
        for _ in range(10):  # max depth
            parent = rt_parent_map.get(current)
            if parent is None or parent == 0 or parent in chain:
                break
            chain.append(parent)
            current = parent

        print(f"\nRT pid={rt_pid} parent chain:")
        for p in chain:
            raw = get_raw(p)
            cls = get_class(p)
            info = f"class={cls}"
            if cls == 224 and raw:
                rt = parse_rect_transform_v2(raw)
                if rt:
                    sd = rt.get('size_delta', ('?','?'))
                    ap = rt.get('anchored_position', ('?','?'))
                    info += f" sizeDelta=({sd[0]:.1f},{sd[1]:.1f}) anchoredPos=({ap[0]:.1f},{ap[1]:.1f})"
            # find GO for this RT
            for obj in usf.objects:
                gpid = obj['path_id']
                gcls = usf.types[obj['type_index']]['class_id']
                if gcls != 1:
                    continue
                graw = get_raw(gpid)
                if not graw:
                    continue
                go = parse_game_object(graw)
                if 'components' in go and any(cp == p for _,cp in go['components']):
                    info += f" | GO pid={gpid} name='{go['name']}'"
                    break
            print(f"  pid={p}: {info}")

    print("\n" + "="*70)
    print("FIND: website_aptitudetest_task7insufficient GameObject and its RT")
    print("="*70)

    # From Step 7: pid=83 'website_aptitudetest_task7insufficient'
    for go_pid in [83, 84, 108, 273, 275, 272, 302]:
        raw = get_raw(go_pid)
        if not raw:
            continue
        cls = get_class(go_pid)
        if cls == 1:
            go = parse_game_object(raw)
            if 'name' in go:
                print(f"\nGO pid={go_pid} '{go['name']}':")
                for _, cpid in go['components']:
                    ccls = get_class(cpid)
                    craw = get_raw(cpid)
                    if ccls == 224 and craw:
                        rt = parse_rect_transform_v2(craw)
                        if rt:
                            sd = rt.get('size_delta', ('?','?'))
                            ap = rt.get('anchored_position', ('?','?'))
                            am = rt.get('anchor_min', ('?','?'))
                            ax = rt.get('anchor_max', ('?','?'))
                            print(f"  RT pid={cpid}: sizeDelta=({sd[0]:.2f},{sd[1]:.2f}) "
                                  f"anchoredPos=({ap[0]:.2f},{ap[1]:.2f}) "
                                  f"anchor=({am[0]:.2f},{am[1]:.2f})-({ax[0]:.2f},{ax[1]:.2f})")
                    elif ccls == 114 and craw:
                        strs = find_strings_in_raw(craw)
                        for off, slen, s in strs[:3]:
                            if 'UnityEngine' not in s:
                                print(f"  MB pid={cpid} @{off}: '{s[:80]}'")

    print("\nDone.")

if __name__ == "__main__":
    main()
