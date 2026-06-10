#!/usr/bin/env python3
"""
Final diagnostic: Understand exactly how TMP text lines map to chunk boxes.
The text container (RT=900) contains all 5 answers as \r\n-separated lines.
The chunk boxes are positioned at fixed Y coordinates.
We need to understand what controls the line-to-box alignment.
"""
import sys, struct, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"C:\Projects\OrwellRU\tools")
from unity_serialized_patcher import UnitySerializedFile

LEVEL4_PATH = r"C:\Projects\OrwellRU\backup\level4"
usf = UnitySerializedFile(LEVEL4_PATH)

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
        'go_pid': go_pid, 'children': children,
        'pos': struct.unpack_from('<ff', raw, base + 28),
        'size': struct.unpack_from('<ff', raw, base + 36),
        'pivot': struct.unpack_from('<ff', raw, base + 44),
    }

# ============================================================
# DEEP DIVE: TextMeshProUGUI binary for RT=900 (MB=1018)
# ============================================================
print("=" * 120)
print("TextMeshProUGUI BINARY ANALYSIS (MB=1018)")
print("=" * 120)

raw = usf.get_object_data(1018)
print(f"Size: {len(raw)} bytes")

# Dump ALL 4-byte aligned float values that look meaningful
print("\nAll potentially meaningful float values:")
for off in range(0, len(raw) - 4, 4):
    v = struct.unpack_from('<f', raw, off)[0]
    iv = struct.unpack_from('<I', raw, off)[0]
    sv = struct.unpack_from('<i', raw, off)[0]

    # Skip obvious non-floats (NaN, infinity, very large, very small)
    if v != 0 and abs(v) < 10000 and abs(v) > 0.001:
        # But also check if it's more likely an int
        is_likely_float = True
        if iv < 1000000 and iv > 0:
            is_likely_float = False  # Probably an int
        if is_likely_float or (5 < abs(v) < 200):
            print(f"  @{off:4d}: float={v:12.4f}  int={sv:12d}  hex={iv:08x}")

# Find the m_text field explicitly
print("\n\nStrings found:")
i = 0
while i < len(raw) - 4:
    slen = struct.unpack_from('<I', raw, i)[0]
    if 3 <= slen <= 5000 and i + 4 + slen <= len(raw):
        try:
            s = raw[i+4:i+4+slen].decode('utf-8')
            if any(c.isalpha() for c in s):
                print(f"  @{i}: [{slen}] {s[:120]}")
                padding = (4 - (slen % 4)) % 4
                i += 4 + slen + padding
                continue
        except:
            pass
    i += 1

# Look at bytes right around the text for font settings
print("\n\nBytes AFTER the m_text string:")
# m_text starts at offset 196 with length 511
text_start = 196
text_len = struct.unpack_from('<I', raw, text_start)[0]
text_pad = (4 - (text_len % 4)) % 4
after_text = text_start + 4 + text_len + text_pad
print(f"  Text ends at byte {after_text}")
print(f"  Next 200 bytes (possible font size, line spacing, etc.):")

# Dump as mixed int/float
for off in range(after_text, min(after_text + 200, len(raw)), 4):
    v = struct.unpack_from('<f', raw, off)[0]
    iv = struct.unpack_from('<I', raw, off)[0]
    sv = struct.unpack_from('<i', raw, off)[0]
    desc = ""
    if abs(v) < 10000 and abs(v) > 0.1:
        desc = f"  <- likely float"
    elif 0 < iv < 100:
        desc = f"  <- small int"
    elif iv == 0:
        desc = f"  <- zero"
    elif 0x3F000000 <= iv <= 0x40000000:
        desc = f"  <- float in [0.5, 2.0] range"
    print(f"  @{off:4d}: float={v:12.4f}  uint={iv:10d}  int={sv:10d}  hex={iv:08x}{desc}")

# ============================================================
# Look at ANOTHER task's text for comparison
# Task 3 (unjustlaw) has RT=693, MB=964
# ============================================================
print("\n\n" + "=" * 120)
print("COMPARISON: Task 3 TextMeshProUGUI (MB=964, RT=693)")
print("=" * 120)

raw3 = usf.get_object_data(964)
print(f"Size: {len(raw3)} bytes")

# Find m_text
i = 0
while i < len(raw3) - 4:
    slen = struct.unpack_from('<I', raw3, i)[0]
    if 100 < slen < 5000 and i + 4 + slen <= len(raw3):
        try:
            s = raw3[i+4:i+4+slen].decode('utf-8')
            if 'link' in s.lower():
                print(f"  m_text @{i}: [{slen}] {s[:200]}")
                # Look at what comes after
                pad = (4 - (slen % 4)) % 4
                after = i + 4 + slen + pad
                print(f"  Text ends at {after}")

                # Compare offset pattern with task1
                print(f"\n  Bytes after text (same region as task1):")
                for off in range(after, min(after + 100, len(raw3)), 4):
                    v = struct.unpack_from('<f', raw3, off)[0]
                    iv = struct.unpack_from('<I', raw3, off)[0]
                    print(f"    @{off:4d}: float={v:12.4f}  uint={iv:10d}  hex={iv:08x}")
                break
        except:
            pass
    i += 1

# ============================================================
# CRITICAL: How are the chunk boxes matched to text lines?
# ============================================================
print("\n\n" + "=" * 120)
print("CHUNK BOX ↔ TEXT LINE MAPPING ANALYSIS")
print("=" * 120)

# Task 1 layout:
# Text container RT=900: Y=-646.9, pivot=(0,1) = top-left
# Chunk boxes:
#   RT=753: Y=-636.9 (top box)
#   RT=647: Y=-706.9
#   RT=703: Y=-776.9
#   RT=893: Y=-846.9
#   RT=902: Y=-916.9 (bottom box)

# The text container starts at Y=-646.9 (with pivot top-left)
# The first chunk box is at Y=-636.9 (10px ABOVE the text start!)
# This means the text is positioned 10px LOWER than the first chunk box

# With TMP, each line has a specific height based on:
# - font size
# - line height multiplier
# - line spacing

# The chunk boxes are spaced exactly 70px apart:
# -636.9, -706.9, -776.9, -846.9, -916.9
chunk_ys = [-636.9, -706.9, -776.9, -846.9, -916.9]
for i in range(1, len(chunk_ys)):
    print(f"  Chunk box spacing [{i-1}→{i}]: {chunk_ys[i] - chunk_ys[i-1]:.1f} px")

text_y = -646.9
print(f"\n  Text container Y: {text_y}")
print(f"  First chunk Y: {chunk_ys[0]}")
print(f"  Offset (text - chunk1): {text_y - chunk_ys[0]:.1f} px")

# The text has 5 lines. Each line needs to be ~70px.
# Original English text:
# Line 1: "· I want to be a pioneer..."
# Line 2: "· I want to make The Nation..."
# Line 3: "· I like spying on people."
# Line 4: "· I want to protect people..."
# Line 5: "· I am in for the money."

# Each chunk box is 52.9px tall, spaced 70px apart
print(f"\n  Chunk box height: 52.9 px")
print(f"  Chunk box spacing: 70 px")
print(f"  Gap between boxes: {70 - 52.9:.1f} px")

print(f"\n  Text container height: {401.4:.1f} px")
print(f"  5 lines in {401.4:.1f}px = {401.4/5:.1f} px per line")
print(f"  4 spacings of 70px = {4*70:.0f}px + some top/bottom padding")

# Now the SIZES of chunk boxes (width tells us the text width for that answer):
chunk_widths = {
    753: 1082.8,  # "pioneer" answer
    647: 711.6,   # "safer" answer
    703: 417.6,   # "spying" answer
    893: 639.6,   # "protect" answer
    902: 394.4,   # "money" answer
}

print("\n\nOriginal English answer text and chunk box widths:")
answers_en = [
    "· I want to be a pioneer in the most advanced security program.",
    "· I want to make The Nation a safer place.",
    "· I like spying on people.",
    "· I want to protect people from harm.",
    "· I am in for the money.",
]
answers_ru = [
    "· Хочу быть первопроходцем в программе безопасности.",
    "· Я хочу сделать Нацию безопаснее.",
    "· Мне нравится следить за людьми.",
    "· Хочу защищать людей от опасности.",
    "· Я здесь ради денег.",
]
for i, (en, ru) in enumerate(zip(answers_en, answers_ru)):
    print(f"  [{i+1}] EN: {en}")
    print(f"      RU: {ru}")
    print(f"      EN chars: {len(en)}, RU chars: {len(ru)}, ratio: {len(ru)/len(en):.2f}")
    print()

print("\n" + "=" * 120)
print("ROOT CAUSE ANALYSIS")
print("=" * 120)
print("""
ARCHITECTURE:
  The aptitude test uses TWO overlapping systems:

  1. CHUNK BOXES (blue clickable strips) — 5 separate GameObjects
     - Positioned at fixed Y coordinates: -636.9, -706.9, -776.9, -846.9, -916.9
     - Spacing: exactly 70px between each
     - Width varies per answer (matches the English text width)
     - These are the CLICKABLE/DRAGGABLE elements
     - They DON'T contain the text themselves!

  2. TEXT CONTAINER (RT=900) — ONE single TextMeshPro object
     - Contains ALL 5 answers as one text block
     - Each answer is a <link>...</link> block separated by \\r\\n
     - TMP renders this as 5 lines with its internal line spacing
     - Positioned at Y=-646.9 (10px below first chunk box)
     - Size: 1451.8 x 401.4

  The TEXT is overlaid ON TOP of the chunk boxes. The <link> tags make
  each line clickable and map to the data_task_* identifiers.

WHY TEXT DOESN'T ALIGN WITH STRIPS AFTER TRANSLATION:

  The chunk boxes have FIXED positions (Y = -636.9, -706.9, etc.).
  But the TMP text lines are rendered with INTERNAL line spacing.

  When Russian text is longer, some lines may WRAP to 2 lines in TMP,
  which pushes all subsequent lines DOWN. But the chunk boxes stay at
  their fixed positions.

  Even if lines don't wrap, the TMP line height calculation depends on
  the font metrics. If the Russian font/glyphs have different ascender/
  descender values, the effective line height changes.

WHAT NEEDS TO CHANGE:

  Option A: Adjust the chunk box Y-positions to match where TMP puts the lines
    - This requires knowing the exact TMP line height (which depends on
      font size, line spacing setting, and font metrics)
    - Chunk box PIDs for task1: 753, 647, 703, 893, 902

  Option B: Adjust the chunk box WIDTHS to be wider (so Russian text doesn't wrap)
    AND keep the same line count

  Option C: Both — wider boxes AND adjusted Y positions

  The chunk box WIDTH is critical because if Russian text on ANY line
  is wider than the chunk box, TMP will wrap it, adding extra lines
  and pushing everything below it down.

KEY NUMBERS FOR TASK1:
  Text container width: 1451.8 px (plenty of room — text won't wrap here)
  Chunk box widths: 1082.8, 711.6, 417.6, 639.6, 394.4
  Chunk box Y spacing: 70px
  Chunk box height: 52.9px

  The chunk boxes DON'T control text rendering — they're just clickable
  overlays. The text is rendered entirely by TMP in the text container.

  So if TMP renders lines at different Y offsets than 70px apart,
  the text lines will be offset from the chunk boxes.

CRITICAL REALIZATION:
  The chunk box widths (which differ per answer) suggest they were sized
  to match the rendered English text width. For Russian translation,
  these widths MUST be updated to match the Russian text widths.
  Otherwise the blue strip won't cover the full text.

  BUT the Y-position misalignment is about TMP line spacing, not box width.
  We need to check if the TMP font size and line spacing produce exactly
  70px line height. If not, we need to either:
  1. Adjust the TMP line spacing to produce 70px
  2. Or adjust the chunk box Y positions

  Let me check the TMP font size...
""")

# ============================================================
# TMP properties analysis
# ============================================================
print("=" * 120)
print("TMP FONT SIZE AND LINE SPACING (MB=1018)")
print("=" * 120)

raw = usf.get_object_data(1018)

# TextMeshProUGUI structure (approximate):
# After m_GameObject PPtr (12 bytes):
# m_Enabled (1 byte) + align
# m_Script PPtr (12 bytes)
# m_Name (string)
# Then MaskableGraphic fields
# Then TMP fields: m_text, m_fontAsset, m_fontSize, etc.

# Let's look at bytes 0-16 for standard header
print(f"Bytes 0-3 (GO FileID): {struct.unpack_from('<i', raw, 0)[0]}")
print(f"Bytes 4-11 (GO PathID): {struct.unpack_from('<q', raw, 4)[0]}")
print(f"Byte 12 (m_Enabled): {raw[12]}")
print(f"Bytes 16-19 (Script FileID): {struct.unpack_from('<i', raw, 16)[0]}")
print(f"Bytes 20-27 (Script PathID): {struct.unpack_from('<q', raw, 20)[0]}")
print(f"Bytes 28-31 (m_Name len): {struct.unpack_from('<I', raw, 28)[0]}")

name_len = struct.unpack_from('<I', raw, 28)[0]
name_pad = (4 - (name_len % 4)) % 4
after_name = 32 + name_len + name_pad
print(f"After m_Name: offset {after_name}")

# Dump the region between name and the m_text string (offset 196)
print(f"\nBytes between m_Name end ({after_name}) and m_text start (196):")
for off in range(after_name, 200, 4):
    v = struct.unpack_from('<f', raw, off)[0]
    iv = struct.unpack_from('<I', raw, off)[0]
    print(f"  @{off:4d}: float={v:12.6f}  uint={iv:10d}  hex={iv:08x}")

# Also check after the m_text string
text_len = struct.unpack_from('<I', raw, 196)[0]
text_pad = (4 - (text_len % 4)) % 4
after_text = 200 + text_len + text_pad
print(f"\nBytes after m_text (offset {after_text}):")
print(f"Looking for fontSize (common TMP sizes: 24, 30, 36, 42, 48)...")
for off in range(after_text, min(after_text + 300, len(raw)), 4):
    v = struct.unpack_from('<f', raw, off)[0]
    iv = struct.unpack_from('<I', raw, off)[0]
    # Flag values that look like font size or spacing
    desc = ""
    if 10 < v < 200 and v == round(v, 1):
        desc = " *** POSSIBLE FONT SIZE OR SPACING ***"
    elif 0.5 < v < 5.0:
        desc = " (possible multiplier)"
    elif iv == 1:
        desc = " (bool/enum = 1)"
    elif iv == 0:
        desc = ""
    print(f"  @{off:4d}: float={v:12.6f}  uint={iv:10d}  hex={iv:08x}{desc}")

# ============================================================
# Compare: look at how ALL task screens' text + chunk boxes align
# ============================================================
print("\n\n" + "=" * 120)
print("ALL TASKS: Text container position vs Chunk box positions")
print("=" * 120)

tasks = {
    669: ("Task 1 career", 900, [753, 647, 703, 893, 902]),
    712: ("Task 3 unjust", 693, [864, 895, 745, 845, 786]),
    853: ("Task 5 dating", 824, [696, 673, 859, 681, 689]),
    925: ("Task 5 medical", 916, [890, 755, 746, 844, 765]),
    899: ("Task 6 friend", 650, [905, 921, 852, 880, 920, 731, 835]),
    707: ("Task 4 medical/dating", 720, [762, 821]),
    645: ("Task 7 lie", 754, [843, 670]),
    705: ("Task 7 insuff", 870, [782, 831, 885]),
}

for task_rt, (name, text_rt, chunk_rts) in sorted(tasks.items()):
    text = parse_rt(text_rt)
    if not text:
        continue
    print(f"\n  {name} (task RT={task_rt}):")
    print(f"    Text container RT={text_rt}: Y={text['pos'][1]:.1f} H={text['size'][1]:.1f}")

    # Sort chunk boxes by Y
    chunks = []
    for crt in chunk_rts:
        c = parse_rt(crt)
        if c:
            chunks.append((crt, c['pos'][1], c['size'][0], c['size'][1]))
    chunks.sort(key=lambda x: x[1], reverse=True)  # Most positive Y first (top of screen)

    for i, (cpid, cy, cw, ch) in enumerate(chunks):
        offset_from_text = cy - text['pos'][1]
        print(f"    Chunk RT={cpid}: Y={cy:.1f} W={cw:.1f} H={ch:.1f}  (Y offset from text: {offset_from_text:+.1f})")
        if i > 0:
            spacing = chunks[i-1][1] - cy
            print(f"      Spacing from prev: {spacing:.1f}px")

print("\nDone.")
