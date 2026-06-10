#!/usr/bin/env python3
"""
Diagnostic script: find welcome/registration screen text MonoBehaviours
and their associated RectTransforms in level1.

Strategy:
1. Find MonoBehaviours containing target text strings
2. Extract the GameObject reference from each MonoBehaviour (first 12 bytes)
3. Parse the GameObject to find its RectTransform component
4. Dump the RectTransform's anchoredPosition and sizeDelta
"""
import sys, struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile


def parse_rect_transform(raw):
    """Parse RectTransform: anchoredPosition and sizeDelta."""
    if len(raw) < 100:
        return None
    children_count = struct.unpack_from('<I', raw, 52)[0]
    anchor_off = 84 + children_count * 12
    size_off = 92 + children_count * 12
    if size_off + 8 > len(raw):
        return None
    ax, ay = struct.unpack_from('<ff', raw, anchor_off)
    sw, sh = struct.unpack_from('<ff', raw, size_off)
    return children_count, ax, ay, sw, sh


def extract_gameobject_pid_from_monobehaviour(raw):
    """
    MonoBehaviour raw data starts with:
      [4 bytes file_index (int32)] [8 bytes path_id (int64)] = reference to GameObject
      [4 bytes enabled (uint32)]
      [4 bytes file_index] [8 bytes path_id] = reference to Script
    """
    if len(raw) < 12:
        return None
    file_idx = struct.unpack_from('<i', raw, 0)[0]
    go_pid = struct.unpack_from('<q', raw, 4)[0]
    return go_pid


def extract_components_from_gameobject(raw):
    """
    GameObject raw data:
      [4 bytes component_count (uint32)]
      [component_count * (4+8) bytes] = pairs of (file_index, path_id) for each component
      [4 bytes layer]
      [4 bytes name_length] [name bytes] [padding]
    Returns list of (file_idx, component_pid) and the name.
    """
    if len(raw) < 4:
        return [], ""
    comp_count = struct.unpack_from('<I', raw, 0)[0]
    if comp_count > 100:  # sanity check
        return [], ""
    components = []
    pos = 4
    for _ in range(comp_count):
        if pos + 12 > len(raw):
            break
        file_idx = struct.unpack_from('<i', raw, pos)[0]
        comp_pid = struct.unpack_from('<q', raw, pos + 4)[0]
        components.append((file_idx, comp_pid))
        pos += 12
    # layer
    if pos + 4 <= len(raw):
        layer = struct.unpack_from('<I', raw, pos)[0]
        pos += 4
    # name
    name = ""
    if pos + 4 <= len(raw):
        name_len = struct.unpack_from('<I', raw, pos)[0]
        pos += 4
        if name_len < 500 and pos + name_len <= len(raw):
            try:
                name = raw[pos:pos+name_len].decode('utf-8', errors='replace')
            except:
                pass
    return components, name


def find_text_in_monobehaviour(raw):
    """Extract readable text strings from MonoBehaviour raw data."""
    strings = []
    i = 0
    while i < len(raw) - 4:
        slen = struct.unpack_from('<I', raw, i)[0]
        if 3 <= slen <= 3000 and i + 4 + slen <= len(raw):
            try:
                s = raw[i+4:i+4+slen].decode('utf-8')
                if s.isprintable() or '\r' in s or '\n' in s:
                    if any(c.isalpha() for c in s):
                        strings.append(s[:200])
                        padding = (4 - (slen % 4)) % 4
                        i += 4 + slen + padding
                        continue
            except:
                pass
        i += 1
    return strings


def search_file(filepath, search_strings, label):
    print(f"\n{'='*80}")
    print(f"  {label}: {filepath}")
    print(f"{'='*80}")

    usf = UnitySerializedFile(filepath)

    # Build lookup by path_id with class_id
    obj_map = {}
    for obj in usf.objects:
        class_id = usf.types[obj['type_index']]['class_id']
        obj_map[obj['path_id']] = {
            'class_id': class_id,
            'size': obj['size'],
        }

    # Count by type
    type_counts = {}
    for pid, info in obj_map.items():
        cid = info['class_id']
        type_counts[cid] = type_counts.get(cid, 0) + 1
    print(f"\nObject types: {dict(sorted(type_counts.items()))}")

    # Collect all MonoBehaviours
    monobehaviours = {}
    for pid, info in obj_map.items():
        if info['class_id'] == 114:
            raw = usf.get_object_data(pid)
            monobehaviours[pid] = raw

    # Search MonoBehaviours for text
    found_pids = []
    print(f"\n--- Searching {len(monobehaviours)} MonoBehaviours ---")

    for pid in sorted(monobehaviours.keys()):
        raw = monobehaviours[pid]
        if not raw:
            continue
        try:
            text = raw.decode('utf-8', errors='replace')
        except:
            continue
        for s in search_strings:
            if s.lower() in text.lower():
                idx = text.lower().find(s.lower())
                start = max(0, idx - 10)
                end = min(len(text), idx + len(s) + 40)
                context = repr(text[start:end])
                print(f"\n  FOUND: path_id={pid}, size={len(raw)}")
                print(f"    Match: '{s}'")
                print(f"    Context: {context}")
                if pid not in found_pids:
                    found_pids.append(pid)

    if not found_pids:
        print("  No matches found!")
        return

    # For each found MonoBehaviour, trace to its RectTransform
    print(f"\n{'='*80}")
    print(f"  TRACING: MonoBehaviour -> GameObject -> RectTransform")
    print(f"{'='*80}")

    for pid in found_pids:
        raw = usf.get_object_data(pid)
        if not raw:
            continue

        # Extract text
        strings = find_text_in_monobehaviour(raw)
        text_str = strings[0] if strings else "?"
        for s in strings:
            for search in search_strings:
                if search.lower() in s.lower():
                    text_str = s
                    break

        print(f"\n  MonoBehaviour PID={pid} (size={len(raw)})")
        print(f"    Text: {repr(text_str[:100])}")

        # Get GameObject PID
        go_pid = extract_gameobject_pid_from_monobehaviour(raw)
        if go_pid is None:
            print(f"    ERROR: Cannot extract GameObject reference")
            continue
        print(f"    -> GameObject PID={go_pid}", end="")

        if go_pid not in obj_map:
            print(f" NOT FOUND in objects!")
            continue

        go_info = obj_map[go_pid]
        if go_info['class_id'] != 1:
            print(f" class_id={go_info['class_id']} (NOT GameObject!)")
            continue
        print()

        # Parse GameObject
        go_raw = usf.get_object_data(go_pid)
        if not go_raw:
            print(f"    ERROR: Cannot read GameObject data")
            continue

        components, go_name = extract_components_from_gameobject(go_raw)
        print(f"    GameObject name: '{go_name}', {len(components)} components")

        # Find RectTransform among components
        rt_found = False
        for file_idx, comp_pid in components:
            if comp_pid not in obj_map:
                continue
            comp_info = obj_map[comp_pid]
            if comp_info['class_id'] == 224:  # RectTransform
                rt_raw = usf.get_object_data(comp_pid)
                if rt_raw:
                    result = parse_rect_transform(rt_raw)
                    if result:
                        cc, ax, ay, sw, sh = result
                        print(f"    -> RectTransform PID={comp_pid}: "
                              f"children={cc}, anchor=({ax:.2f}, {ay:.2f}), "
                              f"sizeDelta=({sw:.2f}, {sh:.2f})")
                        rt_found = True
                    else:
                        print(f"    -> RectTransform PID={comp_pid}: PARSE FAILED (raw size={len(rt_raw)})")
                        rt_found = True

        if not rt_found:
            print(f"    WARNING: No RectTransform found among components!")
            print(f"    Components: {[(fid, cpid, obj_map.get(cpid, {}).get('class_id', '?')) for fid, cpid in components]}")

    # Also look for the PARENT RectTransform (the container)
    print(f"\n{'='*80}")
    print(f"  PARENT CONTAINERS: checking parent GameObjects")
    print(f"{'='*80}")

    for pid in found_pids:
        raw = usf.get_object_data(pid)
        if not raw:
            continue
        go_pid = extract_gameobject_pid_from_monobehaviour(raw)
        if go_pid is None or go_pid not in obj_map:
            continue

        go_raw = usf.get_object_data(go_pid)
        if not go_raw:
            continue
        components, go_name = extract_components_from_gameobject(go_raw)

        # Find this GO's RectTransform
        for file_idx, comp_pid in components:
            if comp_pid not in obj_map:
                continue
            if obj_map[comp_pid]['class_id'] == 224:
                rt_raw = usf.get_object_data(comp_pid)
                if not rt_raw or len(rt_raw) < 60:
                    continue
                # RectTransform starts with:
                # [4 file_idx][8 go_pid] = reference to its own GameObject
                # Then [4 file_idx][8 parent_pid] = reference to parent RectTransform (if any, at offset 12)
                # Actually: first is GO ref, then child count, then child list,
                # then father ref at offset 12
                # Let me check: RectTransform structure:
                # 0: [4+8] m_GameObject ref
                # 12: [4] m_ChildCount  ... wait no
                # Actually the structure at offset 12 is:
                # [4+8] m_Father (parent Transform reference)
                # Let me read it:
                parent_file = struct.unpack_from('<i', rt_raw, 12)[0]
                parent_pid = struct.unpack_from('<q', rt_raw, 16)[0]

                if parent_pid > 0 and parent_pid in obj_map:
                    parent_info = obj_map[parent_pid]
                    if parent_info['class_id'] == 224:
                        parent_rt_raw = usf.get_object_data(parent_pid)
                        if parent_rt_raw:
                            presult = parse_rect_transform(parent_rt_raw)
                            if presult:
                                pcc, pax, pay, psw, psh = presult
                                # Also find parent's GO name
                                pgo_pid_ref = struct.unpack_from('<q', parent_rt_raw, 4)[0]
                                pgo_name = "?"
                                if pgo_pid_ref in obj_map:
                                    pgo_raw = usf.get_object_data(pgo_pid_ref)
                                    if pgo_raw:
                                        _, pgo_name = extract_components_from_gameobject(pgo_raw)
                                print(f"\n  Text '{go_name}' (MonoBehaviour PID={pid})")
                                print(f"    Own RT PID={comp_pid}")
                                print(f"    Parent RT PID={parent_pid}: GO='{pgo_name}', "
                                      f"children={pcc}, anchor=({pax:.2f}, {pay:.2f}), "
                                      f"sizeDelta=({psw:.2f}, {psh:.2f})")


# Search strings for backup (English)
en_strings = [
    "WELCOME, AGENT",
    "Thank you for heeding",
    "call of The Office",
    "AGENT INVESTIGATOR PAIRING",
    "REGISTRATION",
    "PLEASE ENTER YOUR NAME",
    "WELCOME,",
]

# Search strings for patched (Russian)
ru_strings = [
    "ДОБРО ПОЖАЛОВАТЬ",
    "Благодарим за отклик",
    "НАЗНАЧЕНИЕ СЛЕДОВАТЕЛЯ",
    "РЕГИСТРАЦИЯ",
    "ВВЕДИТЕ",
    "АГЕНТ",
]

search_file("C:/Projects/OrwellRU/backup/level1", en_strings, "BACKUP level1 (English)")
search_file("C:/Projects/OrwellRU/patches/level1", ru_strings, "PATCHED level1 (Russian)")
