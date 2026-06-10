#!/usr/bin/env python3
"""
Deep diagnostic v2: Focus on the parent hierarchy of strips, labels, and text containers.
Find their common ancestors and understand the layout.
"""
import sys, struct, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"C:\Projects\OrwellRU\tools")
from unity_serialized_patcher import UnitySerializedFile

LEVEL4_PATH = r"C:\Projects\OrwellRU\backup\level4"
usf = UnitySerializedFile(LEVEL4_PATH)
print(f"Parsed: {len(usf.objects)} objects")

# Build lookup
obj_by_pid = {}
for obj in usf.objects:
    class_id = usf.types[obj['type_index']]['class_id']
    obj_by_pid[obj['path_id']] = {
        'class_id': class_id,
        'size': obj['size'],
    }

# Parse ALL RTs
def parse_rt(pid):
    raw = usf.get_object_data(pid)
    if not raw or len(raw) < 56:
        return None
    go_pid = struct.unpack_from('<q', raw, 4)[0]
    father_fid = struct.unpack_from('<i', raw, 40)[0]
    father_pid = struct.unpack_from('<q', raw, 44)[0]
    cc = struct.unpack_from('<I', raw, 52)[0]
    children = []
    for ci in range(cc):
        cp = struct.unpack_from('<q', raw, 56 + ci*12 + 4)[0]
        children.append(cp)
    base = 56 + cc * 12
    if base + 52 > len(raw):
        return None
    return {
        'go_pid': go_pid,
        'father_fid': father_fid,
        'father_pid': father_pid,
        'children': children,
        'scale': struct.unpack_from('<fff', raw, base),
        'anchor_min': struct.unpack_from('<ff', raw, base + 12),
        'anchor_max': struct.unpack_from('<ff', raw, base + 20),
        'pos': struct.unpack_from('<ff', raw, base + 28),
        'size': struct.unpack_from('<ff', raw, base + 36),
        'pivot': struct.unpack_from('<ff', raw, base + 44),
    }

rt_data = {}
for pid, info in obj_by_pid.items():
    if info['class_id'] == 224:
        rt = parse_rt(pid)
        if rt:
            rt_data[pid] = rt

# Map GO -> RT
go_to_rt = {rt['go_pid']: pid for pid, rt in rt_data.items()}

# Parse GO names
def parse_go_name(pid):
    raw = usf.get_object_data(pid)
    if not raw or len(raw) < 8:
        return "?"
    cc = struct.unpack_from('<I', raw, 0)[0]
    if cc > 50:
        return "?"
    # Try different entry sizes
    for entry_size in [16, 12]:
        pos = 4 + cc * entry_size
        if pos + 8 <= len(raw):
            lyr = struct.unpack_from('<I', raw, pos)[0]
            nlen = struct.unpack_from('<I', raw, pos + 4)[0]
            if lyr < 100 and 0 < nlen < 200 and pos + 8 + nlen <= len(raw):
                try:
                    name = raw[pos+8:pos+8+nlen].decode('utf-8')
                    if name.isprintable():
                        return name
                except:
                    pass
    return "?"

go_names = {}
for pid, info in obj_by_pid.items():
    if info['class_id'] == 1:
        go_names[pid] = parse_go_name(pid)

def rt_name(pid):
    if pid not in rt_data:
        return f"RT={pid} [NOT FOUND]"
    go = rt_data[pid]['go_pid']
    name = go_names.get(go, '?')
    rt = rt_data[pid]
    return f"RT={pid} GO={go} '{name}' pos=({rt['pos'][0]:.1f},{rt['pos'][1]:.1f}) size=({rt['size'][0]:.1f},{rt['size'][1]:.1f})"

# ============================================================
# Trace parent chain for key PIDs
# ============================================================
KEY_PIDS = {
    # Strips
    679: "STRIP_1", 863: "STRIP_2", 901: "STRIP_3", 710: "STRIP_4",
    # Labels
    903: "LABEL_1", 911: "LABEL_2", 630: "LABEL_3", 728: "LABEL_4",
    # Career text container
    900: "CAREER_TEXT",
    # Other containers
    650: "CONTAINER_dickmove", 693: "CONTAINER_unjustlaw",
}

print("\n" + "=" * 120)
print("PARENT CHAINS FOR ALL KEY ELEMENTS")
print("=" * 120)

for pid in sorted(KEY_PIDS.keys()):
    label = KEY_PIDS[pid]
    print(f"\n{label}:")
    chain = []
    cur = pid
    depth = 0
    while cur in rt_data and depth < 15:
        rt = rt_data[cur]
        go_name = go_names.get(rt['go_pid'], '?')
        chain.append((cur, go_name, rt['pos'], rt['size'], rt['pivot'], rt['anchor_min'], rt['anchor_max'], rt['father_pid'], rt['father_fid']))
        # Check if father is in this file (father_fid should be 0 for local refs)
        if rt['father_fid'] != 0:
            break
        if rt['father_pid'] == 0:
            break
        cur = rt['father_pid']
        depth += 1

    for i, (cpid, name, pos, sz, piv, amin, amax, fpid, ffid) in enumerate(chain):
        indent = "  " * i
        parent_note = f"parent_rt={fpid}" if ffid == 0 else f"parent_rt={fpid} [EXTERNAL fid={ffid}]"
        print(f"  {indent}RT={cpid} '{name}' pos=({pos[0]:.1f},{pos[1]:.1f}) size=({sz[0]:.1f},{sz[1]:.1f}) "
              f"pivot=({piv[0]:.2f},{piv[1]:.2f}) anchor=({amin[0]:.2f},{amin[1]:.2f})-({amax[0]:.2f},{amax[1]:.2f}) {parent_note}")

# ============================================================
# Find common parents
# ============================================================
print("\n" + "=" * 120)
print("COMMON PARENT ANALYSIS")
print("=" * 120)

def get_ancestors(pid, max_depth=15):
    """Return list of ancestor RT pids."""
    ancestors = []
    cur = pid
    depth = 0
    while cur in rt_data and depth < max_depth:
        rt = rt_data[cur]
        if rt['father_fid'] != 0 or rt['father_pid'] == 0:
            break
        ancestors.append(rt['father_pid'])
        cur = rt['father_pid']
        depth += 1
    return ancestors

strip_ancestors = {pid: get_ancestors(pid) for pid in [679, 863, 901, 710]}
label_ancestors = {pid: get_ancestors(pid) for pid in [903, 911, 630, 728]}
text_ancestors = get_ancestors(900)

print(f"\nCareer text (RT=900) ancestors: {text_ancestors}")
for spid in [679, 863, 901, 710]:
    print(f"Strip RT={spid} ancestors: {strip_ancestors[spid]}")
for lpid in [903, 911, 630, 728]:
    print(f"Label RT={lpid} ancestors: {label_ancestors[lpid]}")

# ============================================================
# Detailed look at the immediate parent of strip 679
# ============================================================
print("\n" + "=" * 120)
print("STRIP PARENT DETAILS")
print("=" * 120)

for spid in [679, 863, 901, 710]:
    rt = rt_data[spid]
    fp = rt['father_pid']
    print(f"\n  Strip RT={spid} → father_pid={fp} (father_fid={rt['father_fid']})")
    if fp in rt_data:
        frt = rt_data[fp]
        fname = go_names.get(frt['go_pid'], '?')
        print(f"    PARENT: {rt_name(fp)}")
        print(f"    PARENT children: {frt['children']}")
    else:
        print(f"    Father NOT in rt_data! Checking if it exists as object...")
        if fp in obj_by_pid:
            print(f"    Object exists: class_id={obj_by_pid[fp]['class_id']}")
        else:
            print(f"    Object does NOT exist at all. Checking raw bytes...")
            raw = usf.get_object_data(spid)
            if raw:
                print(f"    Raw RT bytes 40-52: {raw[40:52].hex()}")
                print(f"    father_fid={struct.unpack_from('<i', raw, 40)[0]}")
                print(f"    father_pid={struct.unpack_from('<q', raw, 44)[0]}")

# ============================================================
# Now look at LABEL parents
# ============================================================
print("\n" + "=" * 120)
print("LABEL PARENT DETAILS")
print("=" * 120)

for lpid in [903, 911, 630, 728]:
    rt = rt_data[lpid]
    fp = rt['father_pid']
    print(f"\n  Label RT={lpid} → father_pid={fp} (father_fid={rt['father_fid']})")
    if fp in rt_data:
        frt = rt_data[fp]
        fname = go_names.get(frt['go_pid'], '?')
        print(f"    PARENT: {rt_name(fp)}")
        print(f"    PARENT children: {frt['children']}")
    else:
        print(f"    Father NOT in rt_data!")
        if fp in obj_by_pid:
            print(f"    Object exists: class_id={obj_by_pid[fp]['class_id']}")
        else:
            print(f"    Object does NOT exist. Raw bytes...")
            raw = usf.get_object_data(lpid)
            if raw:
                print(f"    Raw RT bytes 40-52: {raw[40:52].hex()}")

# ============================================================
# Career text container parent
# ============================================================
print("\n" + "=" * 120)
print("CAREER TEXT CONTAINER (RT=900) PARENT DETAILS")
print("=" * 120)

rt = rt_data[900]
fp = rt['father_pid']
print(f"  Career text RT=900 → father_pid={fp} (father_fid={rt['father_fid']})")
if fp in rt_data:
    print(f"    PARENT: {rt_name(fp)}")
    frt = rt_data[fp]
    print(f"    PARENT children ({len(frt['children'])}): {frt['children']}")

    # Show all siblings
    for sib in frt['children']:
        if sib in rt_data:
            sibrt = rt_data[sib]
            sibname = go_names.get(sibrt['go_pid'], '?')
            tag = ""
            if sib in KEY_PIDS:
                tag = KEY_PIDS[sib]
            print(f"      SIBLING: RT={sib} '{sibname}' pos=({sibrt['pos'][0]:.1f},{sibrt['pos'][1]:.1f}) size=({sibrt['size'][0]:.1f},{sibrt['size'][1]:.1f}) {tag}")

    # Grandparent
    gp = frt['father_pid']
    if gp in rt_data:
        print(f"\n    GRANDPARENT: {rt_name(gp)}")
        grt = rt_data[gp]
        print(f"    GP children ({len(grt['children'])}): {grt['children']}")
        for sib in grt['children']:
            if sib in rt_data:
                sibrt = rt_data[sib]
                sibname = go_names.get(sibrt['go_pid'], '?')
                tag = KEY_PIDS.get(sib, "")
                print(f"      GP_CHILD: RT={sib} '{sibname}' pos=({sibrt['pos'][0]:.1f},{sibrt['pos'][1]:.1f}) size=({sibrt['size'][0]:.1f},{sibrt['size'][1]:.1f}) {tag}")

# ============================================================
# Raw dump of strip RT bytes to verify parsing
# ============================================================
print("\n" + "=" * 120)
print("RAW BYTE ANALYSIS: Strip RT=679")
print("=" * 120)
raw = usf.get_object_data(679)
if raw:
    print(f"  Total size: {len(raw)} bytes")
    print(f"  Bytes 0-11 (m_GameObject): fid={struct.unpack_from('<i', raw, 0)[0]} pid={struct.unpack_from('<q', raw, 4)[0]}")
    print(f"  Bytes 12-27 (m_LocalRotation): {struct.unpack_from('<ffff', raw, 12)}")
    print(f"  Bytes 28-39 (m_LocalPosition): {struct.unpack_from('<fff', raw, 28)}")
    print(f"  Bytes 40-51 (m_Father): fid={struct.unpack_from('<i', raw, 40)[0]} pid={struct.unpack_from('<q', raw, 44)[0]}")
    cc = struct.unpack_from('<I', raw, 52)[0]
    print(f"  Bytes 52-55 (m_Children count): {cc}")
    base = 56 + cc * 12
    print(f"  base offset (after children): {base}")
    print(f"  Bytes {base}-{base+11} (m_LocalScale): {struct.unpack_from('<fff', raw, base)}")
    print(f"  Bytes {base+12}-{base+19} (m_AnchorMin): {struct.unpack_from('<ff', raw, base+12)}")
    print(f"  Bytes {base+20}-{base+27} (m_AnchorMax): {struct.unpack_from('<ff', raw, base+20)}")
    print(f"  Bytes {base+28}-{base+35} (m_AnchoredPosition): {struct.unpack_from('<ff', raw, base+28)}")
    print(f"  Bytes {base+36}-{base+43} (m_SizeDelta): {struct.unpack_from('<ff', raw, base+36)}")
    print(f"  Bytes {base+44}-{base+51} (m_Pivot): {struct.unpack_from('<ff', raw, base+44)}")

# Also dump raw for the text container RT=900
print("\n" + "=" * 120)
print("RAW BYTE ANALYSIS: Text Container RT=900")
print("=" * 120)
raw = usf.get_object_data(900)
if raw:
    print(f"  Total size: {len(raw)} bytes")
    print(f"  Bytes 0-11 (m_GameObject): fid={struct.unpack_from('<i', raw, 0)[0]} pid={struct.unpack_from('<q', raw, 4)[0]}")
    print(f"  Bytes 12-27 (m_LocalRotation): {struct.unpack_from('<ffff', raw, 12)}")
    print(f"  Bytes 28-39 (m_LocalPosition): {struct.unpack_from('<fff', raw, 28)}")
    print(f"  Bytes 40-51 (m_Father): fid={struct.unpack_from('<i', raw, 40)[0]} pid={struct.unpack_from('<q', raw, 44)[0]}")
    cc = struct.unpack_from('<I', raw, 52)[0]
    print(f"  Bytes 52-55 (m_Children count): {cc}")
    if cc > 0:
        for ci in range(min(cc, 10)):
            cfid = struct.unpack_from('<i', raw, 56+ci*12)[0]
            cpid = struct.unpack_from('<q', raw, 56+ci*12+4)[0]
            print(f"    Child[{ci}]: fid={cfid} pid={cpid}")
    base = 56 + cc * 12
    print(f"  base offset: {base}")
    print(f"  m_LocalScale: {struct.unpack_from('<fff', raw, base)}")
    print(f"  m_AnchorMin: {struct.unpack_from('<ff', raw, base+12)}")
    print(f"  m_AnchorMax: {struct.unpack_from('<ff', raw, base+20)}")
    print(f"  m_AnchoredPosition: {struct.unpack_from('<ff', raw, base+28)}")
    print(f"  m_SizeDelta: {struct.unpack_from('<ff', raw, base+36)}")
    print(f"  m_Pivot: {struct.unpack_from('<ff', raw, base+44)}")

# ============================================================
# Find the strip parent by checking who has strips as children
# ============================================================
print("\n" + "=" * 120)
print("WHO HAS STRIPS AS CHILDREN?")
print("=" * 120)
strip_set = {679, 863, 901, 710}
label_set = {903, 911, 630, 728}
for rt_pid, rt in rt_data.items():
    overlap_strips = set(rt['children']) & strip_set
    overlap_labels = set(rt['children']) & label_set
    if overlap_strips or overlap_labels:
        name = go_names.get(rt['go_pid'], '?')
        print(f"\n  RT={rt_pid} '{name}' pos=({rt['pos'][0]:.1f},{rt['pos'][1]:.1f}) size=({rt['size'][0]:.1f},{rt['size'][1]:.1f})")
        print(f"    Has strip children: {overlap_strips}")
        print(f"    Has label children: {overlap_labels}")
        print(f"    ALL children ({len(rt['children'])}): {rt['children']}")
        for ch in rt['children']:
            if ch in rt_data:
                crt = rt_data[ch]
                cname = go_names.get(crt['go_pid'], '?')
                tag = ""
                if ch in strip_set: tag = " <<STRIP>>"
                if ch in label_set: tag = " <<LABEL>>"
                if ch == 900: tag = " <<CAREER_TEXT>>"
                print(f"      child RT={ch} '{cname}' pos=({crt['pos'][0]:.1f},{crt['pos'][1]:.1f}) size=({crt['size'][0]:.1f},{crt['size'][1]:.1f}){tag}")

# Also check who has RT=900 as child
print("\n" + "=" * 120)
print("WHO HAS RT=900 (CAREER TEXT) AS CHILD?")
print("=" * 120)
for rt_pid, rt in rt_data.items():
    if 900 in rt['children']:
        name = go_names.get(rt['go_pid'], '?')
        print(f"  RT={rt_pid} '{name}' pos=({rt['pos'][0]:.1f},{rt['pos'][1]:.1f}) size=({rt['size'][0]:.1f},{rt['size'][1]:.1f})")
        print(f"    ALL children ({len(rt['children'])}): {rt['children']}")
        for ch in rt['children']:
            if ch in rt_data:
                crt = rt_data[ch]
                cname = go_names.get(crt['go_pid'], '?')
                print(f"      child RT={ch} '{cname}' pos=({crt['pos'][0]:.1f},{crt['pos'][1]:.1f}) size=({crt['size'][0]:.1f},{crt['size'][1]:.1f})")

print("\nDone.")
