#!/usr/bin/env python3
"""Get remaining data: full children of task7lie container and all sibling RTs."""
import os, sys, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

LEVEL4 = r"C:\Projects\OrwellRU\backup\level4"

def get_rt_fields(raw):
    if len(raw) < 40:
        return None
    last40 = raw[-40:]
    f = struct.unpack_from('<ffffffffff', last40)
    return {
        'anchor_min': (f[0], f[1]),
        'anchor_max': (f[2], f[3]),
        'anchored_position': (f[4], f[5]),
        'size_delta': (f[6], f[7]),
        'size_delta_offset': len(raw) - 40 + 24,
        'pivot': (f[8], f[9]),
    }

def get_children_from_rt(raw):
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
        children.append(struct.unpack_from('<q', raw, pos+4)[0])
        pos += 12
    return children

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
    except:
        return {}

def find_strings(raw, max_results=3):
    strings = []
    i = 0
    while i < len(raw) - 4 and len(strings) < max_results:
        slen = struct.unpack_from('<I', raw, i)[0]
        if 3 <= slen <= 5000 and i + 4 + slen <= len(raw):
            try:
                s = raw[i+4:i+4+slen].decode('utf-8')
                if len(s) >= 3:
                    pr = sum(1 for c in s if c.isprintable() or c in '\r\n\t') / len(s)
                    if pr > 0.85 and 'UnityEngine' not in s:
                        strings.append((i, slen, s))
                        i += 4 + slen + (4 - (slen % 4)) % 4
                        continue
            except:
                pass
        i += 1
    return strings

def main():
    usf = UnitySerializedFile(LEVEL4)
    pid_to_obj = {obj['path_id']: obj for obj in usf.objects}

    def get_class(pid):
        obj = pid_to_obj.get(pid)
        return usf.types[obj['type_index']]['class_id'] if obj else None

    def get_raw(pid):
        return usf.get_object_data(pid)

    # RT->GO map
    rt_go = {}
    for obj in usf.objects:
        pid = obj['path_id']
        if usf.types[obj['type_index']]['class_id'] != 1:
            continue
        raw = get_raw(pid)
        if not raw:
            continue
        go = parse_game_object(raw)
        for _, cpid in go.get('components', []):
            if get_class(cpid) == 224:
                rt_go[cpid] = pid

    def describe_rt(rt_pid):
        raw = get_raw(rt_pid)
        if not raw:
            return f"RT={rt_pid}: NOT FOUND"
        rt = get_rt_fields(raw)
        go_pid = rt_go.get(rt_pid)
        name = "?"
        text = ""
        if go_pid:
            graw = get_raw(go_pid)
            if graw:
                go = parse_game_object(graw)
                name = go.get('name', '?')
                # Get text from MonoBehaviour components
                for _, cpid in go.get('components', []):
                    if get_class(cpid) == 114:
                        craw = get_raw(cpid)
                        if craw:
                            strs = find_strings(craw)
                            for off, slen, s in strs:
                                if len(s) > 5:
                                    text = f" TEXT='{s[:80]}'"
                                    break
        sd = rt['size_delta'] if rt else ('?','?')
        ap = rt['anchored_position'] if rt else ('?','?')
        return (f"RT={rt_pid} GO={go_pid} '{name}' "
                f"sizeDelta=({sd[0]:.1f},{sd[1]:.1f}) "
                f"anchoredPos=({ap[0]:.1f},{ap[1]:.1f}){text}")

    print("="*70)
    print("website_aptitudetest_task7lie (pid=16, RT=645) ALL CHILDREN:")
    print("="*70)
    raw = get_raw(645)
    children = get_children_from_rt(raw)
    print(f"Children RTs: {children}")
    for c in children:
        print(f"  {describe_rt(c)}")

    print()
    print("="*70)
    print("website_aptitudetest_task7insufficient (pid=83, RT=705) ALL CHILDREN:")
    print("="*70)
    raw = get_raw(705)
    children = get_children_from_rt(raw)
    print(f"Children RTs: {children}")
    for c in children:
        print(f"  {describe_rt(c)}")

    # Also check the siblings 782, 831, 885 (chunk boxes)
    print()
    print("="*70)
    print("SIBLING 'chunk box' RTs in task7insufficient (pids 782, 831, 885):")
    print("Details to understand if they overlap with text blocks")
    print("="*70)
    for rt_pid in [782, 831, 885]:
        raw = get_raw(rt_pid)
        if not raw:
            continue
        rt = get_rt_fields(raw)
        sd = rt['size_delta']
        ap = rt['anchored_position']
        # Compute bounding box: top = ap.y (from top), bottom = ap.y - sd.y
        print(f"\nRT={rt_pid}: sizeDelta=({sd[0]:.1f},{sd[1]:.1f}) anchoredPos=({ap[0]:.1f},{ap[1]:.1f})")
        print(f"  Vertical span: y_top={ap[1]:.1f}, y_bottom={ap[1]-sd[1]:.1f}")

    # Text blocks layout
    print()
    print("="*70)
    print("LAYOUT SUMMARY for task7insufficient screen:")
    print("anchor=(0,1) pivot=(0,1) => position is offset from TOP-LEFT of parent")
    print("anchoredPos.y is negative = below top edge")
    print("="*70)
    blocks = [
        (633, "TITLE: INSUFFICIENT RESULTS"),
        (737, "SUBTITLE: You failed..."),
        (787, "BODY: Rejection text"),
        (870, "ANSWERS: data_task_wrongfully/accept"),
    ]
    for rt_pid, label in blocks:
        raw = get_raw(rt_pid)
        if not raw:
            continue
        rt = get_rt_fields(raw)
        sd = rt['size_delta']
        ap = rt['anchored_position']
        y_top = ap[1]
        y_bottom = ap[1] - sd[1]
        print(f"\n  {label}")
        print(f"  RT={rt_pid}: w={sd[0]:.0f} h={sd[1]:.0f}")
        print(f"  anchoredPos=({ap[0]:.1f},{ap[1]:.1f})")
        print(f"  Vertical span: {y_top:.1f} to {y_bottom:.1f}")

    print()
    print("="*70)
    print("LAYOUT SUMMARY for task7lie screen:")
    print("="*70)
    blocks_lie = [
        (896, "SUBTITLE: You have been lying!"),
        (764, "BODY: Lie detection text"),
    ]
    # First, get all children of 645
    raw645 = get_raw(645)
    lie_children = get_children_from_rt(raw645)
    print(f"All children of RT=645: {lie_children}")
    for rt_pid in lie_children:
        raw = get_raw(rt_pid)
        if not raw:
            continue
        rt = get_rt_fields(raw)
        sd = rt['size_delta']
        ap = rt['anchored_position']
        y_top = ap[1]
        y_bottom = ap[1] - sd[1]
        go_pid = rt_go.get(rt_pid)
        name = "?"
        text_preview = ""
        if go_pid:
            graw = get_raw(go_pid)
            if graw:
                go = parse_game_object(graw)
                name = go.get('name', '?')
                for _, cpid in go.get('components', []):
                    if get_class(cpid) == 114:
                        craw = get_raw(cpid)
                        if craw:
                            strs = find_strings(craw)
                            for _, _, s in strs:
                                if len(s) > 5:
                                    text_preview = f" | TEXT: {s[:60]}"
                                    break
        print(f"\n  RT={rt_pid} '{name}': w={sd[0]:.0f} h={sd[1]:.0f} "
              f"anchoredPos=({ap[0]:.1f},{ap[1]:.1f}) span={y_top:.1f}->{y_bottom:.1f}{text_preview}")

    print("\nDone.")

if __name__ == "__main__":
    main()
