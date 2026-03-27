#!/usr/bin/env python3
"""
Find the parent container panels for the aptitude test fail screen objects.
The RectTransform objects for our text elements don't have father pids set
(they returned 0 from parse), so we need to find parents by searching
GameObjects whose RectTransform has our text RT pids in its children list.
"""
import os, sys, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

LEVEL4 = r"C:\Projects\OrwellRU\backup\level4"

def get_rt_fields_from_last40(raw):
    """Extract RectTransform fields from last 40 bytes."""
    if len(raw) < 40:
        return None
    last40 = raw[-40:]
    f = struct.unpack_from('<ffffffffff', last40)
    return {
        'anchor_min': (f[0], f[1]),
        'anchor_max': (f[2], f[3]),
        'anchored_position': (f[4], f[5]),
        'size_delta': (f[6], f[7]),
        'size_delta_offset': len(raw) - 40 + 24,  # offset of sizeDelta in raw
        'pivot': (f[8], f[9]),
    }

def get_children_from_rt(raw):
    """Extract children path_ids from RectTransform."""
    # children array starts at offset 52 (after GO ref 12 + rotation 16 + pos 12 + scale 12)
    pos = 52
    if pos + 4 > len(raw):
        return []
    count = struct.unpack_from('<i', raw, pos)[0]
    if count < 0 or count > 100:
        return []
    children = []
    pos += 4
    for _ in range(count):
        if pos + 12 > len(raw):
            break
        fi = struct.unpack_from('<i', raw, pos)[0]
        pid = struct.unpack_from('<q', raw, pos+4)[0]
        children.append(pid)
        pos += 12
    return children

def get_father_from_rt(raw):
    """Get father path_id from RectTransform."""
    # father is after children array
    pos = 52
    if pos + 4 > len(raw):
        return 0
    count = struct.unpack_from('<i', raw, pos)[0]
    if count < 0 or count > 1000:
        return 0
    pos += 4 + count * 12
    if pos + 12 > len(raw):
        return 0
    father_pid = struct.unpack_from('<q', raw, pos+4)[0]
    return father_pid

def parse_game_object(raw):
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

def find_strings_in_raw(raw, max_results=5):
    strings = []
    i = 0
    while i < len(raw) - 4 and len(strings) < max_results:
        slen = struct.unpack_from('<I', raw, i)[0]
        if 3 <= slen <= 5000 and i + 4 + slen <= len(raw):
            try:
                s = raw[i+4:i+4+slen].decode('utf-8')
                if len(s) >= 3:
                    pr = sum(1 for c in s if c.isprintable() or c in '\r\n\t') / len(s)
                    if pr > 0.85:
                        strings.append((i, slen, s))
                        i += 4 + slen + (4 - (slen % 4)) % 4
                        continue
            except:
                pass
        i += 1
    return strings

def main():
    print(f"Loading {LEVEL4}...")
    usf = UnitySerializedFile(LEVEL4)
    pid_to_obj = {obj['path_id']: obj for obj in usf.objects}

    def get_class(pid):
        obj = pid_to_obj.get(pid)
        if obj:
            return usf.types[obj['type_index']]['class_id']
        return None

    def get_raw(pid):
        return usf.get_object_data(pid)

    # Build RT pid -> father RT pid map and RT pid -> children RT pids
    rt_father = {}
    rt_children = {}
    rt_go = {}  # RT pid -> GO pid

    print("Building RectTransform and GameObject maps...")

    # Map RT -> GO
    for obj in usf.objects:
        pid = obj['path_id']
        cls = usf.types[obj['type_index']]['class_id']
        if cls != 1:
            continue
        raw = get_raw(pid)
        if not raw:
            continue
        go = parse_game_object(raw)
        if 'components' not in go:
            continue
        for _, cpid in go['components']:
            if get_class(cpid) == 224:
                rt_go[cpid] = pid

    # Build parent/children relationships for RTs
    for obj in usf.objects:
        pid = obj['path_id']
        cls = usf.types[obj['type_index']]['class_id']
        if cls != 224:
            continue
        raw = get_raw(pid)
        if not raw:
            continue
        father = get_father_from_rt(raw)
        if father and father != 0:
            rt_father[pid] = father
        children = get_children_from_rt(raw)
        if children:
            rt_children[pid] = children

    print(f"RT father map: {len(rt_father)} entries")
    print(f"RT children map: {len(rt_children)} entries")

    # Our target RTs
    target_rt_pids = [633, 737, 764, 787, 870, 896]
    target_labels = {
        633: "INSUFFICIENT RESULTS (title)",
        737: "You failed... (subtitle fail)",
        764: "Lie detection body",
        787: "Rejection body",
        870: "Answer choices",
        896: "You have been lying! (subtitle lie)",
    }

    print("\n" + "="*70)
    print("CONFIRMED RectTransform Data (from last-40-bytes method)")
    print("="*70)

    for rt_pid in target_rt_pids:
        raw = get_raw(rt_pid)
        if not raw:
            print(f"\npid={rt_pid}: NOT FOUND")
            continue
        rt = get_rt_fields_from_last40(raw)
        print(f"\npid={rt_pid} [{target_labels[rt_pid]}]:")
        print(f"  raw size: {len(raw)} bytes")
        print(f"  sizeDelta: w={rt['size_delta'][0]:.2f}, h={rt['size_delta'][1]:.2f}")
        print(f"  anchoredPosition: x={rt['anchored_position'][0]:.2f}, y={rt['anchored_position'][1]:.2f}")
        print(f"  anchorMin: ({rt['anchor_min'][0]:.3f}, {rt['anchor_min'][1]:.3f})")
        print(f"  anchorMax: ({rt['anchor_max'][0]:.3f}, {rt['anchor_max'][1]:.3f})")
        print(f"  pivot: ({rt['pivot'][0]:.3f}, {rt['pivot'][1]:.3f})")
        print(f"  sizeDelta byte offset in raw: {rt['size_delta_offset']}")
        father = rt_father.get(rt_pid, 0)
        print(f"  father RT pid: {father}")
        children_list = rt_children.get(rt_pid, [])
        print(f"  children RT pids: {children_list}")
        go_pid = rt_go.get(rt_pid, None)
        print(f"  owned by GO pid: {go_pid}")

    print("\n" + "="*70)
    print("TRACING PARENT HIERARCHY via father field")
    print("="*70)

    for rt_pid in target_rt_pids:
        chain = []
        current = rt_pid
        visited = set()
        while current and current not in visited:
            visited.add(current)
            raw = get_raw(current)
            cls = get_class(current)
            if cls != 224 or not raw:
                break
            rt = get_rt_fields_from_last40(raw)
            go_pid = rt_go.get(current, None)
            go_name = "?"
            if go_pid:
                graw = get_raw(go_pid)
                if graw:
                    go = parse_game_object(graw)
                    go_name = go.get('name', '?')
            sd = rt['size_delta'] if rt else ('?', '?')
            ap = rt['anchored_position'] if rt else ('?', '?')
            chain.append({
                'rt_pid': current,
                'go_pid': go_pid,
                'go_name': go_name,
                'sizeDelta': sd,
                'anchoredPos': ap,
            })
            father = rt_father.get(current, 0)
            if not father or father == current:
                break
            current = father

        print(f"\nChain for RT pid={rt_pid} ({target_labels[rt_pid]}):")
        for depth, entry in enumerate(chain):
            indent = "  " + "  " * depth
            sd = entry['sizeDelta']
            ap = entry['anchoredPos']
            print(f"{indent}RT={entry['rt_pid']} GO={entry['go_pid']} '{entry['go_name']}' "
                  f"sizeDelta=({sd[0]:.1f},{sd[1]:.1f}) anchoredPos=({ap[0]:.1f},{ap[1]:.1f})")

    print("\n" + "="*70)
    print("SEARCHING for container panels: who has our target RTs as children")
    print("="*70)

    target_set = set(target_rt_pids)
    for rt_pid, children in rt_children.items():
        for child in children:
            if child in target_set:
                raw = get_raw(rt_pid)
                rt = get_rt_fields_from_last40(raw) if raw else None
                go_pid = rt_go.get(rt_pid, None)
                go_name = "?"
                if go_pid:
                    graw = get_raw(go_pid)
                    if graw:
                        go = parse_game_object(graw)
                        go_name = go.get('name', '?')
                sd = rt['size_delta'] if rt else ('?', '?')
                ap = rt['anchored_position'] if rt else ('?', '?')
                print(f"\nParent RT pid={rt_pid} GO='{go_name}' (pid={go_pid}) "
                      f"sizeDelta=({sd[0]:.2f},{sd[1]:.2f}) anchoredPos=({ap[0]:.2f},{ap[1]:.2f})")
                print(f"  contains child RT={child} ({target_labels.get(child, '?')})")
                print(f"  all children: {children}")

    print("\n" + "="*70)
    print("FULL TEXT of pid=984 (lie detection body)")
    print("="*70)
    raw = get_raw(984)
    if raw:
        strs = find_strings_in_raw(raw, 20)
        for off, slen, s in strs:
            if 'UnityEngine' not in s and len(s) > 5:
                print(f"  @{off} [{slen}]: {s[:300]}")

    print("\n" + "="*70)
    print("FULL TEXT of pid=991 (rejection body)")
    print("="*70)
    raw = get_raw(991)
    if raw:
        strs = find_strings_in_raw(raw, 20)
        for off, slen, s in strs:
            if 'UnityEngine' not in s and len(s) > 5:
                print(f"  @{off} [{slen}]: {s[:300]}")

    print("\n" + "="*70)
    print("FULL TEXT of pid=1010 (answer choices)")
    print("="*70)
    raw = get_raw(1010)
    if raw:
        strs = find_strings_in_raw(raw, 20)
        for off, slen, s in strs:
            if 'UnityEngine' not in s and len(s) > 5:
                print(f"  @{off} [{slen}]: {s[:300]}")

    print("\n" + "="*70)
    print("PANEL CONTAINERS: Search for 'aptitude_fail' or similar GOs")
    print("="*70)

    # Look for GameObjects that are parents/containers for the fail screen
    # Based on naming: website_aptitudetest_task7insufficient (pid=83)
    container_pids = [83, 84]
    for go_pid in container_pids:
        raw = get_raw(go_pid)
        if not raw:
            continue
        cls = get_class(go_pid)
        if cls != 1:
            continue
        go = parse_game_object(raw)
        if 'name' not in go:
            continue
        print(f"\nGO pid={go_pid} '{go['name']}' components: {[cp for _, cp in go['components']]}")
        for _, cpid in go['components']:
            ccls = get_class(cpid)
            craw = get_raw(cpid)
            if not craw:
                continue
            if ccls == 224:
                rt = get_rt_fields_from_last40(craw)
                if rt:
                    sd = rt['size_delta']
                    ap = rt['anchored_position']
                    children_list = get_children_from_rt(craw)
                    print(f"  RT pid={cpid}: sizeDelta=({sd[0]:.2f},{sd[1]:.2f}) "
                          f"anchoredPos=({ap[0]:.2f},{ap[1]:.2f}) children={children_list}")
                    # Show children RTs
                    for child_rt_pid in children_list:
                        crt_raw = get_raw(child_rt_pid)
                        if crt_raw:
                            crt = get_rt_fields_from_last40(crt_raw)
                            child_go = rt_go.get(child_rt_pid)
                            child_name = "?"
                            if child_go:
                                cgraw = get_raw(child_go)
                                if cgraw:
                                    cgo = parse_game_object(cgraw)
                                    child_name = cgo.get('name', '?')
                            if crt:
                                csd = crt['size_delta']
                                cap = crt['anchored_position']
                                print(f"    child RT={child_rt_pid} GO='{child_name}' "
                                      f"sizeDelta=({csd[0]:.2f},{csd[1]:.2f}) "
                                      f"anchoredPos=({cap[0]:.2f},{cap[1]:.2f})")
            elif ccls == 114:
                cstrs = find_strings_in_raw(craw, 5)
                for off, slen, s in cstrs:
                    if 'UnityEngine' not in s and len(s) > 3:
                        print(f"  MB pid={cpid} @{off}: '{s[:100]}'")

    print("\nDone.")

if __name__ == "__main__":
    main()
