#!/usr/bin/env python3
"""
Deep diagnostic v3: Correct RT parsing based on actual byte layout.
The RT with children_count=0 and 108 bytes tells us a lot.

RT=679 is 108 bytes, children_count (at byte 52) = 0.
Per original code: sizeDelta at offset 92 + 0*12 = 92 -> (758, 70) ✓
anchoredPosition at offset 84 -> (460.4, -554.4) ✓

So the layout IS correct per patch_level4.py:
  0-3:   m_GameObject.FileID
  4-11:  m_GameObject.PathID
  12-27: m_LocalRotation (4 floats)
  28-39: m_LocalPosition (3 floats)
  40-43: m_Father.FileID
  44-51: m_Father.PathID
  52-55: m_Children count
  56+:   m_Children array (12 bytes each)
  +0:    m_LocalScale (3 floats)
  +12:   m_AnchorMin (2 floats)
  +20:   m_AnchorMax (2 floats)
  +28:   m_AnchoredPosition (2 floats)
  +36:   m_SizeDelta (2 floats)
  +44:   m_Pivot (2 floats)

But bytes 40-51: 0000803f = float 1.0... that IS m_Father.FileID=1065353216
which as a float is 1.0. So Father.FileID is being read as 1065353216.

Wait, 0x3F800000 = 1.0 as float. So the m_Father field is 12 bytes that
read as three 1.0 floats. That's suspicious — maybe the field layout is
different for this Unity version.

Let me check: if children_count is at byte 52 = 0, and the RT is 108 bytes:
108 = 56 + 0*12 + 12 + 8 + 8 + 8 + 8 + 8 = 56 + 52 = 108 ✓

So the structure seems right. The parent IS an external reference.
BUT the "WHO HAS STRIPS AS CHILDREN" analysis FOUND RT=825 has them!

That means the children array in RT=825 DOES contain 679,863,901,710 —
the parent-child link works from PARENT→CHILD but the CHILD→PARENT
(m_Father) references might be cross-file in level files.

The key insight: RT=825 'profiler_top' is the COMMON PARENT of both strips
and labels. Let me focus on understanding the spatial layout.
"""
import sys, struct, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"C:\Projects\OrwellRU\tools")
from unity_serialized_patcher import UnitySerializedFile

LEVEL4_PATH = r"C:\Projects\OrwellRU\backup\level4"
usf = UnitySerializedFile(LEVEL4_PATH)

# Build lookup
obj_by_pid = {}
for obj in usf.objects:
    class_id = usf.types[obj['type_index']]['class_id']
    obj_by_pid[obj['path_id']] = class_id

def parse_rt(pid):
    raw = usf.get_object_data(pid)
    if not raw or len(raw) < 56:
        return None
    go_pid = struct.unpack_from('<q', raw, 4)[0]
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
        'children': children,
        'pos': struct.unpack_from('<ff', raw, base + 28),
        'size': struct.unpack_from('<ff', raw, base + 36),
        'pivot': struct.unpack_from('<ff', raw, base + 44),
        'anchor_min': struct.unpack_from('<ff', raw, base + 12),
        'anchor_max': struct.unpack_from('<ff', raw, base + 20),
        'scale': struct.unpack_from('<fff', raw, base),
    }

rt_data = {}
for pid, cid in obj_by_pid.items():
    if cid == 224:
        rt = parse_rt(pid)
        if rt:
            rt_data[pid] = rt

def parse_go_name(pid):
    raw = usf.get_object_data(pid)
    if not raw or len(raw) < 8:
        return "?"
    cc = struct.unpack_from('<I', raw, 0)[0]
    if cc > 50: return "?"
    for entry_size in [16, 12]:
        pos = 4 + cc * entry_size
        if pos + 8 <= len(raw):
            lyr = struct.unpack_from('<I', raw, pos)[0]
            nlen = struct.unpack_from('<I', raw, pos + 4)[0]
            if lyr < 100 and 0 < nlen < 200 and pos + 8 + nlen <= len(raw):
                try:
                    name = raw[pos+8:pos+8+nlen].decode('utf-8')
                    if name.isprintable(): return name
                except: pass
    return "?"

go_names = {}
for pid, cid in obj_by_pid.items():
    if cid == 1:
        go_names[pid] = parse_go_name(pid)

# ============================================================
# KEY FINDING: RT=825 'profiler_top' is the parent of EVERYTHING
# It has 16 children including all 4 strips and 4 labels
# ============================================================

profiler_top = 825
pt = rt_data[profiler_top]
pt_name = go_names.get(pt['go_pid'], '?')

print(f"PROFILER_TOP RT={profiler_top} '{pt_name}'")
print(f"  pos=({pt['pos'][0]:.1f},{pt['pos'][1]:.1f}) size=({pt['size'][0]:.1f},{pt['size'][1]:.1f})")
print(f"  pivot=({pt['pivot'][0]:.2f},{pt['pivot'][1]:.2f})")
print(f"  anchor=({pt['anchor_min'][0]:.2f},{pt['anchor_min'][1]:.2f})-({pt['anchor_max'][0]:.2f},{pt['anchor_max'][1]:.2f})")
print(f"  children ({len(pt['children'])}):")
print()

# Layout of profiler_top children with Y-sorted analysis
children_info = []
for ch in pt['children']:
    if ch in rt_data:
        crt = rt_data[ch]
        cname = go_names.get(crt['go_pid'], '?')
        children_info.append((ch, cname, crt['pos'], crt['size'], crt['pivot']))

# Sort by Y position (most negative = lowest on screen)
children_info.sort(key=lambda x: x[2][1])

STRIP_PIDS = {679, 863, 901, 710}
LABEL_PIDS = {903, 911, 630, 728}

print(f"  {'PID':>6} {'Name':<45} {'X':>8} {'Y':>10} {'W':>8} {'H':>8} {'PivX':>5} {'PivY':>5} Tag")
print("  " + "-" * 120)
for ch, name, pos, sz, piv in children_info:
    tag = ""
    if ch in STRIP_PIDS: tag = "STRIP"
    if ch in LABEL_PIDS: tag = "LABEL"
    print(f"  {ch:>6} {name:<45} {pos[0]:>8.1f} {pos[1]:>10.1f} {sz[0]:>8.1f} {sz[1]:>8.1f} {piv[0]:>5.2f} {piv[1]:>5.2f} {tag}")

# ============================================================
# Now look at the TASK screens that contain the answer TEXT
# RT=669 'website_aptitudetest_task1' is the parent of RT=900 (career text)
# ============================================================
print("\n" + "=" * 120)
print("APTITUDE TEST TASK SCREENS (parents of answer text containers)")
print("=" * 120)

# Find all task screen parents
task_container_rts = {900, 693, 650, 720, 754, 824, 870, 916}
task_screen_parents = {}

for rt_pid, rt in rt_data.items():
    overlap = set(rt['children']) & task_container_rts
    if overlap:
        name = go_names.get(rt['go_pid'], '?')
        task_screen_parents[rt_pid] = (name, overlap)

for tsp, (name, overlap) in sorted(task_screen_parents.items()):
    trt = rt_data[tsp]
    print(f"\n  TASK SCREEN: RT={tsp} '{name}'")
    print(f"    pos=({trt['pos'][0]:.1f},{trt['pos'][1]:.1f}) size=({trt['size'][0]:.1f},{trt['size'][1]:.1f})")
    print(f"    pivot=({trt['pivot'][0]:.2f},{trt['pivot'][1]:.2f})")
    print(f"    anchor=({trt['anchor_min'][0]:.2f},{trt['anchor_min'][1]:.2f})-({trt['anchor_max'][0]:.2f},{trt['anchor_max'][1]:.2f})")
    print(f"    Contains text containers: {overlap}")

    # Show all children sorted by Y
    ch_infos = []
    for ch in trt['children']:
        if ch in rt_data:
            crt = rt_data[ch]
            cname = go_names.get(crt['go_pid'], '?')
            ch_infos.append((ch, cname, crt['pos'], crt['size']))
    ch_infos.sort(key=lambda x: x[2][1])

    for ch, cname, cpos, csz in ch_infos:
        tag = ""
        if ch in task_container_rts: tag = " <<ANSWER_TEXT>>"
        # Check if this is a "chunk box" — the blue clickable item
        if "chunk" in cname.lower(): tag = " <<CHUNK_BOX>>"
        print(f"    child RT={ch} '{cname[:60]}' pos=({cpos[0]:.1f},{cpos[1]:.1f}) size=({csz[0]:.1f},{csz[1]:.1f}){tag}")

# ============================================================
# THE KEY QUESTION: Where are the chunk boxes relative to the strips?
# ============================================================
print("\n" + "=" * 120)
print("CHUNK BOXES vs STRIPS — POSITIONAL COMPARISON")
print("=" * 120)

# Task1 screen (career motivation)
task1 = 669
t1rt = rt_data[task1]
print(f"\nTASK 1 (career motivation): RT={task1} '{go_names.get(t1rt['go_pid'], '?')}'")
print(f"  Task screen pos=({t1rt['pos'][0]:.1f},{t1rt['pos'][1]:.1f})")

print("\n  Chunk boxes (blue strips with text inside task screen):")
for ch in t1rt['children']:
    if ch in rt_data:
        crt = rt_data[ch]
        cname = go_names.get(crt['go_pid'], '?')
        if "chunk" in cname.lower():
            print(f"    RT={ch} '{cname}' Y={crt['pos'][1]:.1f} size=({crt['size'][0]:.1f},{crt['size'][1]:.1f})")

print("\n  Answer text container:")
print(f"    RT=900 Y={rt_data[900]['pos'][1]:.1f} size=({rt_data[900]['size'][0]:.1f},{rt_data[900]['size'][1]:.1f})")

print("\n  Profiler strips (separate, under 'profiler_top'):")
for spid in sorted(STRIP_PIDS):
    srt = rt_data[spid]
    print(f"    RT={spid} Y={srt['pos'][1]:.1f} size=({srt['size'][0]:.1f},{srt['size'][1]:.1f})")

print("\n  Profiler labels (separate, under 'profiler_top'):")
for lpid in sorted(LABEL_PIDS):
    lrt = rt_data[lpid]
    lname = go_names.get(lrt['go_pid'], '?')
    print(f"    RT={lpid} '{lname}' Y={lrt['pos'][1]:.1f} size=({lrt['size'][0]:.1f},{lrt['size'][1]:.1f})")

# ============================================================
# Find PARENT of profiler_top and task screens
# ============================================================
print("\n" + "=" * 120)
print("PARENT OF PROFILER_TOP (RT=825)")
print("=" * 120)

for rt_pid, rt in rt_data.items():
    if 825 in rt['children']:
        name = go_names.get(rt['go_pid'], '?')
        print(f"  PARENT: RT={rt_pid} '{name}' pos=({rt['pos'][0]:.1f},{rt['pos'][1]:.1f}) size=({rt['size'][0]:.1f},{rt['size'][1]:.1f})")
        print(f"    children ({len(rt['children'])}): {rt['children']}")

        # Also show what's at the same level as profiler_top
        print(f"\n    Siblings of profiler_top:")
        for sib in rt['children']:
            if sib in rt_data:
                sibrt = rt_data[sib]
                sibname = go_names.get(sibrt['go_pid'], '?')
                print(f"      RT={sib} '{sibname}' pos=({sibrt['pos'][0]:.1f},{sibrt['pos'][1]:.1f}) size=({sibrt['size'][0]:.1f},{sibrt['size'][1]:.1f})")

# Find parent of task1 screen (669)
print("\n" + "=" * 120)
print("PARENT OF TASK1 SCREEN (RT=669)")
print("=" * 120)

for rt_pid, rt in rt_data.items():
    if 669 in rt['children']:
        name = go_names.get(rt['go_pid'], '?')
        print(f"  PARENT: RT={rt_pid} '{name}' pos=({rt['pos'][0]:.1f},{rt['pos'][1]:.1f}) size=({rt['size'][0]:.1f},{rt['size'][1]:.1f})")

# ============================================================
# Understand chunk boxes more deeply — they are the draggable answers
# ============================================================
print("\n" + "=" * 120)
print("CHUNK BOXES IN TASK1 (RT=669) — These are the draggable answer options")
print("=" * 120)

# Find MB data for chunk boxes
for ch in t1rt['children']:
    if ch in rt_data:
        crt = rt_data[ch]
        cname = go_names.get(crt['go_pid'], '?')
        if "chunk" in cname.lower():
            go_pid = crt['go_pid']
            print(f"\n  CHUNK RT={ch} GO={go_pid} '{cname}'")
            print(f"    pos=({crt['pos'][0]:.1f},{crt['pos'][1]:.1f}) size=({crt['size'][0]:.1f},{crt['size'][1]:.1f})")
            print(f"    pivot=({crt['pivot'][0]:.2f},{crt['pivot'][1]:.2f})")
            print(f"    children: {crt['children']}")

            # Find MonoBehaviours on this GO
            for obj in usf.objects:
                if usf.types[obj['type_index']]['class_id'] != 114:
                    continue
                raw = usf.get_object_data(obj['path_id'])
                if not raw or len(raw) < 12:
                    continue
                mb_go = struct.unpack_from('<q', raw, 4)[0]
                if mb_go == go_pid:
                    # Find strings
                    strs = []
                    i = 0
                    while i < len(raw) - 4:
                        slen = struct.unpack_from('<I', raw, i)[0]
                        if 3 <= slen <= 5000 and i + 4 + slen <= len(raw):
                            try:
                                s = raw[i+4:i+4+slen].decode('utf-8')
                                if any(c.isalpha() for c in s) and (s.isprintable() or '\r' in s or '\n' in s):
                                    strs.append(s[:100])
                                    padding = (4 - (slen % 4)) % 4
                                    i += 4 + slen + padding
                                    continue
                            except:
                                pass
                        i += 1
                    if strs:
                        print(f"    MB PID={obj['path_id']}: {strs[:3]}")

            # Show children of chunk box
            for sub in crt['children']:
                if sub in rt_data:
                    subrt = rt_data[sub]
                    subname = go_names.get(subrt['go_pid'], '?')
                    print(f"      CHILD RT={sub} '{subname}' pos=({subrt['pos'][0]:.1f},{subrt['pos'][1]:.1f}) size=({subrt['size'][0]:.1f},{subrt['size'][1]:.1f})")

# ============================================================
# SUMMARY: The real question
# ============================================================
print("\n" + "=" * 120)
print("SUMMARY & ANALYSIS")
print("=" * 120)

print("""
STRUCTURE DISCOVERED:

  profiler_top (RT=825) pos=(0,-123) size=(0,0)
    Contains as direct children:
    - 4 blue strips (bg_profiler_top 10-13): Y = -554.4, -639.0, -724.0, -809.0
    - 4 field labels (txt_birthday_date, etc.): Y = -574.0, -658.0, -740.0, -828.0
    - 4 field titles (txt_birthday_title, etc.)
    - bg_profiler_top bg (large background)
    - arrow_image_profiler
    - image_profiler_subject (photo)
    - Profile Image Manager

  website_aptitudetest_task1 (RT=669) pos=(0,0) size=(0,0)
    Contains as direct children:
    - 5 chunk boxes (draggable answer slots): Y = -636.9, -706.9, -776.9, -846.9, -916.9
    - 1 answer text container (RT=900): pos=(4.8, -646.9) size=(1451.8, 401.4)
    - title/subtitle text blocks

KEY INSIGHT:
  The profiler_top strips and labels are for the PROFILE CARD display
  (birthday, residence, occupation, relationship status) — NOT for the
  aptitude test answers!

  The aptitude test answers are in the CHUNK BOXES inside the task screen.
  The answer TEXT (RT=900) is a TextMeshPro that renders ALL 5 answers
  as a single text block with <link> tags for each answer.

  The chunk boxes are the blue draggable items positioned at:
    Y = -636.9, -706.9, -776.9, -846.9, -916.9 (spacing ~70px)

  Strip PIDs 679,863,901,710 are for the PROFILE CARD, not the test answers.
  Label PIDs 903,911,630,728 are also for the PROFILE CARD fields.

  The text-strip misalignment in the aptitude test is about:
  1. The single TextMeshPro block (RT=900) being one big text area
  2. The chunk boxes being separate small objects
  3. When Russian text is longer, the TMP text block's line heights change,
     pushing lower answers further down relative to their chunk boxes.
""")

# ============================================================
# Verify: what text does the chunk box contain?
# ============================================================
print("=" * 120)
print("TASK1 CHUNK BOX DETAILS WITH TEXT")
print("=" * 120)

chunk_rts = [753, 647, 703, 893, 902]
for ch in chunk_rts:
    if ch not in rt_data:
        continue
    crt = rt_data[ch]
    cname = go_names.get(crt['go_pid'], '?')
    go_pid = crt['go_pid']
    print(f"\n  CHUNK RT={ch} '{cname[:60]}'")
    print(f"    pos=({crt['pos'][0]:.1f},{crt['pos'][1]:.1f}) size=({crt['size'][0]:.1f},{crt['size'][1]:.1f})")

    # Find all MBs on this GO
    for obj in usf.objects:
        if usf.types[obj['type_index']]['class_id'] != 114:
            continue
        raw = usf.get_object_data(obj['path_id'])
        if not raw or len(raw) < 12:
            continue
        mb_go = struct.unpack_from('<q', raw, 4)[0]
        if mb_go != go_pid:
            continue
        strs = []
        i = 0
        while i < len(raw) - 4:
            slen = struct.unpack_from('<I', raw, i)[0]
            if 3 <= slen <= 5000 and i + 4 + slen <= len(raw):
                try:
                    s = raw[i+4:i+4+slen].decode('utf-8')
                    if any(c.isalpha() for c in s) and (s.isprintable() or '\r' in s or '\n' in s):
                        strs.append(s[:150])
                        padding = (4 - (slen % 4)) % 4
                        i += 4 + slen + padding
                        continue
                except:
                    pass
            i += 1
        if strs:
            print(f"    MB={obj['path_id']} size={obj['size']}: {strs[:5]}")

# ============================================================
# Look at the answer text MB more closely — line heights, etc.
# ============================================================
print("\n" + "=" * 120)
print("ANSWER TEXT MB=1018 (career motivation) DETAILED")
print("=" * 120)

raw = usf.get_object_data(1018)
if raw:
    # This is TextMeshProUGUI. Let's find the m_text field and other properties
    # After the PPtr to script, there's the m_Name, then component data
    # Let's just find all interesting fields
    print(f"  Size: {len(raw)} bytes")

    # Find all strings
    i = 0
    while i < len(raw) - 4:
        slen = struct.unpack_from('<I', raw, i)[0]
        if 3 <= slen <= 5000 and i + 4 + slen <= len(raw):
            try:
                s = raw[i+4:i+4+slen].decode('utf-8')
                if any(c.isalpha() for c in s):
                    txt = s[:200].replace('\r\n', '\\n').replace('\n', '\\n')
                    print(f"  @{i:4d} [{slen:4d}] {txt}")
                    padding = (4 - (slen % 4)) % 4
                    i += 4 + slen + padding
                    continue
            except:
                pass
        i += 1

    # Also look for float values that could be font size, line spacing
    # TextMeshProUGUI has m_fontSize, m_lineSpacing etc.
    # Let's look at bytes around the text
    print(f"\n  Looking for fontSize (likely a float around 18-48)...")
    for off in range(0, min(len(raw), 200), 4):
        v = struct.unpack_from('<f', raw, off)[0]
        if 10.0 < v < 100.0 and v == int(v):
            print(f"    @{off}: {v}")

print("\nDone.")
