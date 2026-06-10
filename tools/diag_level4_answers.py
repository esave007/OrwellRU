#!/usr/bin/env python3
"""
Deep diagnostic: map MonoBehaviour text → RectTransform → parent hierarchy in level4.
Goal: understand why answer text doesn't align with blue strips after translation.
"""
import sys, struct, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"C:\Projects\OrwellRU\tools")
from unity_serialized_patcher import UnitySerializedFile

LEVEL4_PATH = r"C:\Projects\OrwellRU\backup\level4"

# Known PIDs from patch_level4.py
STRIP_PIDS = {679, 863, 901, 710}  # blue strip RTs
LABEL_PIDS = {903, 911, 630, 728}  # answer label RTs
CONTAINER_PIDS = {900, 693, 870, 754, 650, 720, 824, 916}  # answer container RTs

# Career motivation keywords (English) - the 5 answers for "why do you want to join Orwell?"
CAREER_KEYWORDS = ["pioneer", "safer", "spying", "protect", "money"]

usf = UnitySerializedFile(LEVEL4_PATH)
print(f"Parsed {LEVEL4_PATH}: {len(usf.objects)} objects")

# ============================================================
# STEP 1: Build complete object index with class_ids
# ============================================================
obj_index = {}  # path_id -> {class_id, raw_data, ...}
for obj in usf.objects:
    class_id = usf.types[obj['type_index']]['class_id']
    raw = usf.get_object_data(obj['path_id'])
    obj_index[obj['path_id']] = {
        'class_id': class_id,
        'raw': raw,
        'size': obj['size'],
    }

# ============================================================
# STEP 2: Parse ALL RectTransforms — extract m_GameObject ref + parent + position
# ============================================================
# RectTransform (class_id=224) raw layout:
# Bytes 0-3:   m_GameObject.m_FileID (int32)
# Bytes 4-11:  m_GameObject.m_PathID (int64)
# Bytes 12-15: m_LocalRotation.x (float)
# Bytes 16-19: m_LocalRotation.y (float)
# Bytes 20-23: m_LocalRotation.z (float)
# Bytes 24-27: m_LocalRotation.w (float)
# Bytes 28-31: m_LocalPosition.x (float)
# Bytes 32-35: m_LocalPosition.y (float)
# Bytes 36-39: m_LocalPosition.z (float)
# Bytes 40-43: m_Father.m_FileID (int32)
# Bytes 44-51: m_Father.m_PathID (int64)
# Bytes 52-55: m_Children count
# Bytes 56+:   m_Children array (each 12 bytes: FileID(4) + PathID(8))
# After children:
#   m_LocalScale.x,y,z (3 floats = 12 bytes) — offset = 56 + children_count*12
#   m_AnchorMin.x,y (2 floats = 8 bytes) — offset = 68 + cc*12
#   m_AnchorMax.x,y (2 floats = 8 bytes) — offset = 76 + cc*12
#   m_AnchoredPosition.x,y (2 floats = 8 bytes) — offset = 84 + cc*12
#   m_SizeDelta.x,y (2 floats = 8 bytes) — offset = 92 + cc*12
#   m_Pivot.x,y (2 floats = 8 bytes) — offset = 100 + cc*12

rt_data = {}  # path_id -> parsed RT info
for pid, info in obj_index.items():
    if info['class_id'] != 224:
        continue
    raw = info['raw']
    if not raw or len(raw) < 56:
        continue

    go_file_id = struct.unpack_from('<i', raw, 0)[0]
    go_path_id = struct.unpack_from('<q', raw, 4)[0]

    father_file_id = struct.unpack_from('<i', raw, 40)[0]
    father_path_id = struct.unpack_from('<q', raw, 44)[0]

    children_count = struct.unpack_from('<I', raw, 52)[0]
    children = []
    for ci in range(children_count):
        cf = struct.unpack_from('<i', raw, 56 + ci*12)[0]
        cp = struct.unpack_from('<q', raw, 56 + ci*12 + 4)[0]
        children.append(cp)

    base = 56 + children_count * 12
    if base + 52 > len(raw):
        continue

    scale_x, scale_y, scale_z = struct.unpack_from('<fff', raw, base)
    anchor_min_x, anchor_min_y = struct.unpack_from('<ff', raw, base + 12)
    anchor_max_x, anchor_max_y = struct.unpack_from('<ff', raw, base + 20)
    anchored_x, anchored_y = struct.unpack_from('<ff', raw, base + 28)
    size_w, size_h = struct.unpack_from('<ff', raw, base + 36)
    pivot_x, pivot_y = struct.unpack_from('<ff', raw, base + 44)

    rt_data[pid] = {
        'go_path_id': go_path_id,
        'father_pid': father_path_id,
        'children': children,
        'children_count': children_count,
        'scale': (scale_x, scale_y, scale_z),
        'anchor_min': (anchor_min_x, anchor_min_y),
        'anchor_max': (anchor_max_x, anchor_max_y),
        'anchored_pos': (anchored_x, anchored_y),
        'size_delta': (size_w, size_h),
        'pivot': (pivot_x, pivot_y),
    }

print(f"RectTransforms parsed: {len(rt_data)}")

# Build reverse map: go_path_id -> RT path_id
go_to_rt = {}
for rt_pid, rtinfo in rt_data.items():
    go_to_rt[rtinfo['go_path_id']] = rt_pid

# ============================================================
# STEP 3: Parse ALL MonoBehaviours — extract m_GameObject ref + find text
# ============================================================
# MonoBehaviour raw layout (class_id=114):
# Bytes 0-3:   m_GameObject.m_FileID (int32)
# Bytes 4-11:  m_GameObject.m_PathID (int64)
# Bytes 12:    m_Enabled (uint8)
# Bytes 13-15: padding to align
# Bytes 16-19: m_Script.m_FileID (int32)
# Bytes 20-27: m_Script.m_PathID (int64)
# Bytes 28+:   m_Name (length-prefixed string) then component-specific data

mb_data = {}  # path_id -> parsed info
for pid, info in obj_index.items():
    if info['class_id'] != 114:
        continue
    raw = info['raw']
    if not raw or len(raw) < 28:
        continue

    go_file_id = struct.unpack_from('<i', raw, 0)[0]
    go_path_id = struct.unpack_from('<q', raw, 4)[0]
    enabled = raw[12] if len(raw) > 12 else 0
    script_file_id = struct.unpack_from('<i', raw, 16)[0] if len(raw) > 19 else 0
    script_path_id = struct.unpack_from('<q', raw, 20)[0] if len(raw) > 27 else 0

    # Find all strings in the raw data
    strings_found = []
    i = 0
    while i < len(raw) - 4:
        slen = struct.unpack_from('<I', raw, i)[0]
        if 3 <= slen <= 10000 and i + 4 + slen <= len(raw):
            try:
                s = raw[i+4:i+4+slen].decode('utf-8')
                if s.isprintable() or '\r' in s or '\n' in s:
                    if any(c.isalpha() for c in s):
                        strings_found.append((i, s))
                        padding = (4 - (slen % 4)) % 4
                        i += 4 + slen + padding
                        continue
            except:
                pass
        i += 1

    mb_data[pid] = {
        'go_path_id': go_path_id,
        'script_file_id': script_file_id,
        'script_path_id': script_path_id,
        'strings': strings_found,
        'size': len(raw),
    }

print(f"MonoBehaviours parsed: {len(mb_data)}")

# ============================================================
# STEP 4: Parse GameObjects (class_id=1) to get names and component lists
# ============================================================
# GameObject raw layout (class_id=1):
# Bytes 0-3:   m_Component count (uint32)
# Then for each component:
#   m_Component.first (int32) — class_id of component  (4 bytes)
#   ... wait, actually in Unity 5.x the format is:
#   pair.first = int32 (component class_id)  -- actually this might be PPtr
# Let me just look at the raw bytes

go_data = {}  # path_id -> info
for pid, info in obj_index.items():
    if info['class_id'] != 1:
        continue
    raw = info['raw']
    if not raw or len(raw) < 8:
        continue

    comp_count = struct.unpack_from('<I', raw, 0)[0]
    components = []
    pos = 4
    # Try to figure out entry size: could be 12 (FileID:4 + PathID:8) or 16 (pair first + PPtr)
    # Let's try 12 first (just PPtr per component)
    entry_size = 12
    # But actually Unity 5.x uses pair<int, PPtr> = 4+4+8=16... let's check
    # If comp_count * 16 + 4 + 4 + name fits in raw, use 16; else try 12
    if comp_count > 0 and comp_count < 50:
        # Try 16-byte entries
        test_pos_16 = 4 + comp_count * 16
        test_pos_12 = 4 + comp_count * 12
        # Check which one leads to a valid name string
        for try_size in [16, 12]:
            tp = 4 + comp_count * try_size
            if tp + 8 <= len(raw):
                lyr = struct.unpack_from('<I', raw, tp)[0]
                nlen = struct.unpack_from('<I', raw, tp + 4)[0]
                if lyr < 100 and nlen < 200 and tp + 8 + nlen <= len(raw):
                    try:
                        tname = raw[tp+8:tp+8+nlen].decode('utf-8')
                        if tname.isprintable():
                            entry_size = try_size
                            break
                    except:
                        pass

    for ci in range(comp_count):
        if pos + entry_size > len(raw):
            break
        if entry_size == 16:
            pair_first = struct.unpack_from('<i', raw, pos)[0]
            comp_fid = struct.unpack_from('<i', raw, pos + 4)[0]
            comp_ppid = struct.unpack_from('<q', raw, pos + 8)[0]
        else:
            pair_first = 0
            comp_fid = struct.unpack_from('<i', raw, pos)[0]
            comp_ppid = struct.unpack_from('<q', raw, pos + 4)[0]
        components.append({'type_hint': pair_first, 'file_id': comp_fid, 'path_id': comp_ppid})
        pos += entry_size

    # After components: m_Layer (uint32), m_Name (string)
    layer = struct.unpack_from('<I', raw, pos)[0] if pos + 4 <= len(raw) else 0
    pos += 4

    name = ""
    if pos + 4 <= len(raw):
        name_len = struct.unpack_from('<I', raw, pos)[0]
        if name_len < 500 and pos + 4 + name_len <= len(raw):
            try:
                name = raw[pos+4:pos+4+name_len].decode('utf-8')
            except:
                pass

    go_data[pid] = {
        'name': name,
        'layer': layer,
        'components': components,
    }

print(f"GameObjects parsed: {len(go_data)}")

# ============================================================
# STEP 5: Find career motivation answers specifically
# ============================================================
print("\n" + "=" * 100)
print("CAREER MOTIVATION ANSWERS (pioneer/safer/spying/protect/money)")
print("=" * 100)

career_mb_pids = []
for mb_pid, mbinfo in mb_data.items():
    for offset, s in mbinfo['strings']:
        if any(kw in s.lower() for kw in CAREER_KEYWORDS):
            career_mb_pids.append(mb_pid)
            go_pid = mbinfo['go_path_id']
            rt_pid = go_to_rt.get(go_pid, None)

            print(f"\n  MonoBehaviour PID={mb_pid} (size={mbinfo['size']})")
            print(f"    → GameObject PID={go_pid}", end="")
            if go_pid in go_data:
                print(f" name='{go_data[go_pid]['name']}'")
            else:
                print()

            if rt_pid:
                rt = rt_data[rt_pid]
                print(f"    → RectTransform PID={rt_pid}")
                print(f"      anchoredPos=({rt['anchored_pos'][0]:.1f}, {rt['anchored_pos'][1]:.1f})")
                print(f"      sizeDelta=({rt['size_delta'][0]:.1f}, {rt['size_delta'][1]:.1f})")
                print(f"      pivot=({rt['pivot'][0]:.2f}, {rt['pivot'][1]:.2f})")
                print(f"      anchorMin=({rt['anchor_min'][0]:.2f}, {rt['anchor_min'][1]:.2f})")
                print(f"      anchorMax=({rt['anchor_max'][0]:.2f}, {rt['anchor_max'][1]:.2f})")
                print(f"      children={rt['children']}")

                # Parent chain
                parent_pid = rt['father_pid']
                depth = 0
                while parent_pid and parent_pid in rt_data and depth < 10:
                    prt = rt_data[parent_pid]
                    pgo_pid = prt['go_path_id']
                    pname = go_data.get(pgo_pid, {}).get('name', '?')
                    print(f"      PARENT[{depth}]: RT PID={parent_pid} GO='{pname}' "
                          f"pos=({prt['anchored_pos'][0]:.1f},{prt['anchored_pos'][1]:.1f}) "
                          f"size=({prt['size_delta'][0]:.1f},{prt['size_delta'][1]:.1f}) "
                          f"pivot=({prt['pivot'][0]:.2f},{prt['pivot'][1]:.2f}) "
                          f"anchorMin=({prt['anchor_min'][0]:.2f},{prt['anchor_min'][1]:.2f}) "
                          f"anchorMax=({prt['anchor_max'][0]:.2f},{prt['anchor_max'][1]:.2f})")
                    parent_pid = prt['father_pid']
                    depth += 1
            else:
                print(f"    → NO RectTransform found for GO PID={go_pid}!")

            # Show text snippet
            txt = s[:200].replace('\r\n', '\\n').replace('\n', '\\n')
            print(f"    TEXT @{offset}: {txt}...")
            break

# ============================================================
# STEP 6: Analyze the known STRIP and LABEL PIDs
# ============================================================
print("\n" + "=" * 100)
print("KNOWN STRIP RectTransforms (blue background strips)")
print("=" * 100)
for spid in sorted(STRIP_PIDS):
    if spid in rt_data:
        rt = rt_data[spid]
        go_pid = rt['go_path_id']
        name = go_data.get(go_pid, {}).get('name', '?')
        print(f"\n  STRIP RT PID={spid} → GO PID={go_pid} name='{name}'")
        print(f"    anchoredPos=({rt['anchored_pos'][0]:.1f}, {rt['anchored_pos'][1]:.1f})")
        print(f"    sizeDelta=({rt['size_delta'][0]:.1f}, {rt['size_delta'][1]:.1f})")
        print(f"    pivot=({rt['pivot'][0]:.2f}, {rt['pivot'][1]:.2f})")
        print(f"    anchorMin=({rt['anchor_min'][0]:.2f}, {rt['anchor_min'][1]:.2f})")
        print(f"    anchorMax=({rt['anchor_max'][0]:.2f}, {rt['anchor_max'][1]:.2f})")
        print(f"    children={rt['children']}")

        # What are the children?
        for child_pid in rt['children']:
            if child_pid in rt_data:
                crt = rt_data[child_pid]
                cgo = crt['go_path_id']
                cname = go_data.get(cgo, {}).get('name', '?')
                print(f"      CHILD RT={child_pid} GO='{cname}' pos=({crt['anchored_pos'][0]:.1f},{crt['anchored_pos'][1]:.1f}) size=({crt['size_delta'][0]:.1f},{crt['size_delta'][1]:.1f})")

                # Does this child GO have a MonoBehaviour with text?
                for mb_pid2, mb2 in mb_data.items():
                    if mb2['go_path_id'] == cgo and mb2['strings']:
                        strs = [s[:80] for _, s in mb2['strings'][:3]]
                        print(f"        TEXT MB={mb_pid2}: {strs}")

        # Parent
        parent_pid = rt['father_pid']
        if parent_pid in rt_data:
            prt = rt_data[parent_pid]
            pgo = prt['go_path_id']
            pname = go_data.get(pgo, {}).get('name', '?')
            print(f"    PARENT: RT={parent_pid} GO='{pname}' pos=({prt['anchored_pos'][0]:.1f},{prt['anchored_pos'][1]:.1f}) size=({prt['size_delta'][0]:.1f},{prt['size_delta'][1]:.1f})")

print("\n" + "=" * 100)
print("KNOWN LABEL RectTransforms (answer text labels)")
print("=" * 100)
for lpid in sorted(LABEL_PIDS):
    if lpid in rt_data:
        rt = rt_data[lpid]
        go_pid = rt['go_path_id']
        name = go_data.get(go_pid, {}).get('name', '?')
        print(f"\n  LABEL RT PID={lpid} → GO PID={go_pid} name='{name}'")
        print(f"    anchoredPos=({rt['anchored_pos'][0]:.1f}, {rt['anchored_pos'][1]:.1f})")
        print(f"    sizeDelta=({rt['size_delta'][0]:.1f}, {rt['size_delta'][1]:.1f})")
        print(f"    pivot=({rt['pivot'][0]:.2f}, {rt['pivot'][1]:.2f})")
        print(f"    anchorMin=({rt['anchor_min'][0]:.2f}, {rt['anchor_min'][1]:.2f})")
        print(f"    anchorMax=({rt['anchor_max'][0]:.2f}, {rt['anchor_max'][1]:.2f})")

        # Does the GO have text MonoBehaviour?
        for mb_pid2, mb2 in mb_data.items():
            if mb2['go_path_id'] == go_pid and mb2['strings']:
                strs = [s[:120] for _, s in mb2['strings'][:5]]
                print(f"    TEXT MB={mb_pid2}: {strs}")

        # Parent
        parent_pid = rt['father_pid']
        if parent_pid in rt_data:
            prt = rt_data[parent_pid]
            pgo = prt['go_path_id']
            pname = go_data.get(pgo, {}).get('name', '?')
            print(f"    PARENT: RT={parent_pid} GO='{pname}' pos=({prt['anchored_pos'][0]:.1f},{prt['anchored_pos'][1]:.1f}) size=({prt['size_delta'][0]:.1f},{prt['size_delta'][1]:.1f})")

            # Grandparent
            gp = prt['father_pid']
            if gp in rt_data:
                grt = rt_data[gp]
                ggo = grt['go_path_id']
                gname = go_data.get(ggo, {}).get('name', '?')
                print(f"    GRANDPARENT: RT={gp} GO='{gname}' pos=({grt['anchored_pos'][0]:.1f},{grt['anchored_pos'][1]:.1f}) size=({grt['size_delta'][0]:.1f},{grt['size_delta'][1]:.1f})")

# ============================================================
# STEP 7: Analyze container PIDs
# ============================================================
print("\n" + "=" * 100)
print("KNOWN CONTAINER RectTransforms")
print("=" * 100)
for cpid in sorted(CONTAINER_PIDS):
    if cpid in rt_data:
        rt = rt_data[cpid]
        go_pid = rt['go_path_id']
        name = go_data.get(go_pid, {}).get('name', '?')
        print(f"\n  CONTAINER RT PID={cpid} → GO='{name}'")
        print(f"    pos=({rt['anchored_pos'][0]:.1f},{rt['anchored_pos'][1]:.1f}) size=({rt['size_delta'][0]:.1f},{rt['size_delta'][1]:.1f})")
        print(f"    pivot=({rt['pivot'][0]:.2f},{rt['pivot'][1]:.2f}) anchorMin=({rt['anchor_min'][0]:.2f},{rt['anchor_min'][1]:.2f}) anchorMax=({rt['anchor_max'][0]:.2f},{rt['anchor_max'][1]:.2f})")
        print(f"    children ({len(rt['children'])}): {rt['children']}")

        # Show all children details
        for child_pid in rt['children']:
            if child_pid in rt_data:
                crt = rt_data[child_pid]
                cgo = crt['go_path_id']
                cname = go_data.get(cgo, {}).get('name', '?')
                print(f"      CHILD RT={child_pid} GO='{cname}' pos=({crt['anchored_pos'][0]:.1f},{crt['anchored_pos'][1]:.1f}) size=({crt['size_delta'][0]:.1f},{crt['size_delta'][1]:.1f}) pivot=({crt['pivot'][0]:.2f},{crt['pivot'][1]:.2f})")

                # Sub-children?
                for sc in crt['children']:
                    if sc in rt_data:
                        scrt = rt_data[sc]
                        scgo = scrt['go_path_id']
                        scname = go_data.get(scgo, {}).get('name', '?')
                        print(f"          SUB-CHILD RT={sc} GO='{scname}' pos=({scrt['anchored_pos'][0]:.1f},{scrt['anchored_pos'][1]:.1f}) size=({scrt['size_delta'][0]:.1f},{scrt['size_delta'][1]:.1f})")

# ============================================================
# STEP 8: Find ALL MonoBehaviours that contain the career text
# and trace their full hierarchy
# ============================================================
print("\n" + "=" * 100)
print("FULL TEXT SEARCH: All MonoBehaviours with 'pioneer' or 'spying' or 'money'")
print("=" * 100)
for mb_pid, mbinfo in sorted(mb_data.items()):
    for offset, s in mbinfo['strings']:
        if any(kw in s.lower() for kw in ['pioneer', 'spying', 'money', 'safer place', 'protect people']):
            go_pid = mbinfo['go_path_id']
            name = go_data.get(go_pid, {}).get('name', '?')
            rt_pid = go_to_rt.get(go_pid)
            print(f"\n  MB PID={mb_pid} → GO PID={go_pid} name='{name}' script=({mbinfo['script_file_id']},{mbinfo['script_path_id']})")
            txt = s[:300].replace('\r\n', '\\n').replace('\n', '\\n')
            print(f"    TEXT @{offset}: {txt}")

            if rt_pid and rt_pid in rt_data:
                rt = rt_data[rt_pid]
                print(f"    RT PID={rt_pid}: pos=({rt['anchored_pos'][0]:.1f},{rt['anchored_pos'][1]:.1f}) size=({rt['size_delta'][0]:.1f},{rt['size_delta'][1]:.1f}) pivot=({rt['pivot'][0]:.2f},{rt['pivot'][1]:.2f})")

                # Full parent chain
                pp = rt['father_pid']
                d = 0
                while pp and pp in rt_data and d < 8:
                    prt = rt_data[pp]
                    pn = go_data.get(prt['go_path_id'], {}).get('name', '?')
                    print(f"    PARENT[{d}] RT={pp} GO='{pn}' pos=({prt['anchored_pos'][0]:.1f},{prt['anchored_pos'][1]:.1f}) size=({prt['size_delta'][0]:.1f},{prt['size_delta'][1]:.1f}) pivot=({prt['pivot'][0]:.2f},{prt['pivot'][1]:.2f})")
                    pp = prt['father_pid']
                    d += 1

# ============================================================
# STEP 9: Are strips CHILDREN or SIBLINGS of the text items?
# ============================================================
print("\n" + "=" * 100)
print("RELATIONSHIP ANALYSIS: Strips vs Labels")
print("=" * 100)

# For each strip, find its parent and siblings
for spid in sorted(STRIP_PIDS):
    if spid not in rt_data:
        continue
    srt = rt_data[spid]
    parent = srt['father_pid']
    sname = go_data.get(srt['go_path_id'], {}).get('name', '?')

    print(f"\n  STRIP RT={spid} GO='{sname}' parent_rt={parent}")

    if parent in rt_data:
        prt = rt_data[parent]
        pname = go_data.get(prt['go_path_id'], {}).get('name', '?')
        print(f"    PARENT: RT={parent} GO='{pname}' children={prt['children']}")

        # Show all siblings
        for sib in prt['children']:
            if sib in rt_data:
                sibrt = rt_data[sib]
                sibgo = sibrt['go_path_id']
                sibname = go_data.get(sibgo, {}).get('name', '?')
                is_strip = "STRIP" if sib in STRIP_PIDS else ""
                is_label = "LABEL" if sib in LABEL_PIDS else ""
                tag = is_strip or is_label or ""
                print(f"      SIBLING RT={sib} GO='{sibname}' pos=({sibrt['anchored_pos'][0]:.1f},{sibrt['anchored_pos'][1]:.1f}) size=({sibrt['size_delta'][0]:.1f},{sibrt['size_delta'][1]:.1f}) {tag}")

                # Also check children of this sibling (the label might be INSIDE the strip)
                for sc in sibrt['children']:
                    if sc in rt_data:
                        scrt = rt_data[sc]
                        scgo = scrt['go_path_id']
                        scname = go_data.get(scgo, {}).get('name', '?')
                        is_l = "LABEL" if sc in LABEL_PIDS else ""
                        print(f"          CHILD RT={sc} GO='{scname}' pos=({scrt['anchored_pos'][0]:.1f},{scrt['anchored_pos'][1]:.1f}) size=({scrt['size_delta'][0]:.1f},{scrt['size_delta'][1]:.1f}) {is_l}")

# ============================================================
# STEP 10: Check if strips have Layout components (VerticalLayoutGroup, etc)
# ============================================================
print("\n" + "=" * 100)
print("LAYOUT COMPONENTS CHECK: Do containers have LayoutGroup MonoBehaviours?")
print("=" * 100)

# For all containers, check if their GO has multiple MonoBehaviours
for cpid in sorted(CONTAINER_PIDS):
    if cpid not in rt_data:
        continue
    go_pid = rt_data[cpid]['go_path_id']
    name = go_data.get(go_pid, {}).get('name', '?')

    # Find all MonoBehaviours on this GO
    go_mbs = [(mp, mi) for mp, mi in mb_data.items() if mi['go_path_id'] == go_pid]
    if go_mbs:
        print(f"\n  CONTAINER GO='{name}' (RT={cpid}):")
        for mp, mi in go_mbs:
            strs = [s[:60] for _, s in mi['strings'][:3]]
            print(f"    MB PID={mp} script=({mi['script_file_id']},{mi['script_path_id']}) size={mi['size']} strings={strs}")

# Also check strip GOs
for spid in sorted(STRIP_PIDS):
    if spid not in rt_data:
        continue
    go_pid = rt_data[spid]['go_path_id']
    name = go_data.get(go_pid, {}).get('name', '?')
    go_mbs = [(mp, mi) for mp, mi in mb_data.items() if mi['go_path_id'] == go_pid]
    if go_mbs:
        print(f"\n  STRIP GO='{name}' (RT={spid}):")
        for mp, mi in go_mbs:
            strs = [s[:60] for _, s in mi['strings'][:3]]
            print(f"    MB PID={mp} script=({mi['script_file_id']},{mi['script_path_id']}) size={mi['size']} strings={strs}")

# Check label GOs
for lpid in sorted(LABEL_PIDS):
    if lpid not in rt_data:
        continue
    go_pid = rt_data[lpid]['go_path_id']
    name = go_data.get(go_pid, {}).get('name', '?')
    go_mbs = [(mp, mi) for mp, mi in mb_data.items() if mi['go_path_id'] == go_pid]
    if go_mbs:
        print(f"\n  LABEL GO='{name}' (RT={lpid}):")
        for mp, mi in go_mbs:
            strs = [s[:120] for _, s in mi['strings'][:3]]
            print(f"    MB PID={mp} script=({mi['script_file_id']},{mi['script_path_id']}) size={mi['size']} strings={strs}")

# ============================================================
# STEP 11: Find the 5th strip/item (there are 5 career answers but only 4 strips listed)
# ============================================================
print("\n" + "=" * 100)
print("SEARCHING FOR 5TH ANSWER ITEM (5 answers but only 4 strips known)")
print("=" * 100)
# Look for RTs near Y=-894 (next one in the ~85px spacing pattern)
for rt_pid, rt in sorted(rt_data.items()):
    y = rt['anchored_pos'][1]
    x = rt['anchored_pos'][0]
    w = rt['size_delta'][0]
    if -920 < y < -870 and 300 < x < 900 and w > 400:
        name = go_data.get(rt['go_path_id'], {}).get('name', '?')
        print(f"  Candidate RT={rt_pid} GO='{name}' pos=({x:.1f},{y:.1f}) size=({w:.1f},{rt['size_delta'][1]:.1f})")

print("\nDone.")
