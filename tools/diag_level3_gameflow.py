#!/usr/bin/env python3
"""
Diagnostic: find all MonoBehaviour objects in level3 that are gameflow/state
controllers (internal lookup keys that must NOT be translated).

Key distinction: objects with `website_` inside <link> tags or `CHAR_` inside
regular text content are TRANSLATABLE UI text. True gameflow controllers have
these as standalone identifiers, not inside HTML-like markup.
"""
import sys, os, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from unity_serialized_patcher import UnitySerializedFile

BACKUP = r"C:\Projects\OrwellRU\backup\level3"

def extract_strings(raw, min_len=3):
    """Extract length-prefixed UTF-8 strings from raw data."""
    strings = []
    i = 0
    while i < len(raw) - 4:
        length = int.from_bytes(raw[i:i+4], 'little')
        if 0 < length < 2000 and i + 4 + length <= len(raw):
            try:
                s = raw[i+4:i+4+length].decode('utf-8')
                if s.isprintable() and len(s) >= min_len:
                    strings.append((i, s))
                    i += 4 + length
                    continue
            except:
                pass
        i += 1
    return strings

def is_gameflow_controller(raw, strings):
    """
    Determine if this MonoBehaviour is a gameflow/state controller.
    These have:
    - Asset paths like Assets/Resources/Flows/...
    - Flow names like "Gameflow Day N", "Ignorance Is Strength - Day N"
    - State type names like IfElseState, WaitState, etc.
    - Character DB entries (CHAR_XXX as standalone keys, not in text)
    - Website page definitions (website_xxx as standalone keys)

    NOT gameflow:
    - TextMeshProUGUI with <link="website_..."> in m_text
    - Regular text containing character names
    - UI elements with CullStateChangedEvent
    """
    str_texts = [s for _, s in strings]

    # Check for flow asset paths
    has_flow_paths = any("Assets/Resources" in s and "Flows/" in s for s in str_texts)
    has_gameflow_names = any(s.startswith("Gameflow ") for s in str_texts)

    # Check for state machine types (these are class names, not UI text)
    state_types = ["IfElseState", "WaitState", "ChangeVariableState",
                   "DocumentViewedState", "NewBookmarkState", "NewChatMessageState",
                   "NewCommentaryState", "UpdateProfileState", "AtClockTimeState",
                   "NewDataChunkState", "FlowState", "GameFlowManager"]
    has_state_types = any(any(st in s for st in state_types) for s in str_texts)

    # Character database: many CHAR_ entries as standalone keys (not in <link> tags)
    char_count = sum(1 for s in str_texts if re.match(r'^CHAR_[A-Z]+$', s))
    is_char_db = char_count >= 5  # DB has many character IDs

    # Website page definitions: standalone website_ keys (not inside <link> markup)
    # In UI text, website_ appears as <link="website_xxx">
    # In controllers, it appears as standalone string
    standalone_website = sum(1 for s in str_texts
                           if s.startswith("website_") and "<" not in s and ">" not in s
                           and not s.endswith(".png"))
    # But also check if the object has <link> markup (TextMeshPro)
    has_link_markup = any("<link=" in s for s in str_texts)
    has_tmp_markup = any("<color=" in s or "<#" in s or "m_text" in s for s in str_texts)
    # Also check raw data for TMP signature
    has_tmp_raw = b"UnityEngine.UI.MaskableGraphic+CullStateChangedEvent" in raw

    # Decision logic
    if has_flow_paths or has_gameflow_names:
        return True, "gameflow_manager"
    if has_state_types:
        return True, "state_machine"
    if is_char_db:
        return True, "character_database"

    # Website page definitions (NOT TextMeshPro with links)
    if standalone_website >= 3 and not has_tmp_raw and not has_link_markup:
        return True, "website_page_controller"

    return False, None

def main():
    print(f"Parsing {BACKUP}...")
    usf = UnitySerializedFile(BACKUP)
    print(f"Total objects: {len(usf.objects)}")

    # Find MonoBehaviour type indices
    mono_type_indices = set()
    for i, t in enumerate(usf.types):
        if t['class_id'] == 114:
            mono_type_indices.add(i)

    mono_count = sum(1 for obj in usf.objects if obj['type_index'] in mono_type_indices)
    print(f"MonoBehaviour objects: {mono_count}")

    # Categorize
    results_by_category = {}
    all_skip_pids = set()

    for obj in usf.objects:
        if obj['type_index'] not in mono_type_indices:
            continue

        abs_offset = usf.data_offset + obj['offset']
        raw = bytes(usf.data[abs_offset:abs_offset + obj['size']])
        strings = extract_strings(raw)

        is_gf, category = is_gameflow_controller(raw, strings)
        if is_gf:
            pid = obj['path_id']
            all_skip_pids.add(pid)
            if category not in results_by_category:
                results_by_category[category] = []
            results_by_category[category].append({
                'pid': pid,
                'size': obj['size'],
                'type_index': obj['type_index'],
                'strings': strings,
            })

    # Print results by category
    for category, items in sorted(results_by_category.items()):
        print(f"\n{'='*70}")
        print(f"CATEGORY: {category} ({len(items)} objects)")
        print(f"{'='*70}")
        for item in items:
            pid = item['pid']
            print(f"\n  PID {pid} (size={item['size']}, type_idx={item['type_index']})")
            # Show first 15 strings
            for offset, s in item['strings'][:15]:
                print(f"    @{offset:5d}: {s[:120]}")
            if len(item['strings']) > 15:
                print(f"    ... and {len(item['strings'])-15} more strings")

    # Specifically examine PID 44155 and PID 44858
    for target_pid in [44155, 44858]:
        print(f"\n{'='*70}")
        print(f"=== DETAILED STRINGS IN PID {target_pid} ===")
        print(f"{'='*70}")
        for obj in usf.objects:
            if obj['path_id'] == target_pid:
                abs_offset = usf.data_offset + obj['offset']
                raw = bytes(usf.data[abs_offset:abs_offset + obj['size']])
                strings = extract_strings(raw)
                print(f"Size: {obj['size']} bytes, Type index: {obj['type_index']}")
                print(f"Total strings: {len(strings)}")
                # Show all strings but truncated
                for offset, s in strings[:80]:
                    print(f"  @{offset:5d}: {s[:150]}")
                if len(strings) > 80:
                    print(f"  ... and {len(strings)-80} more strings")
                break
        else:
            print(f"  PID {target_pid} NOT FOUND")

    # Also look for objects that have many website_ standalone keys but aren't TextMeshPro
    print(f"\n{'='*70}")
    print(f"=== WEBSITE PAGE CONTROLLERS (standalone website_ keys, no TMP markup) ===")
    print(f"{'='*70}")
    for obj in usf.objects:
        if obj['type_index'] not in mono_type_indices:
            continue
        abs_offset = usf.data_offset + obj['offset']
        raw = bytes(usf.data[abs_offset:abs_offset + obj['size']])
        strings = extract_strings(raw)
        str_texts = [s for _, s in strings]

        standalone_ws = [s for s in str_texts
                        if s.startswith("website_") and "<" not in s and ">" not in s
                        and not s.endswith(".png")]
        has_tmp = b"UnityEngine.UI.MaskableGraphic+CullStateChangedEvent" in raw
        has_link = any("<link=" in s for s in str_texts)

        if len(standalone_ws) >= 2 and not has_tmp and not has_link:
            pid = obj['path_id']
            print(f"\n  PID {pid} (size={obj['size']})")
            for s in standalone_ws[:10]:
                print(f"    {s}")
            # Also show non-website strings for context
            other = [s for s in str_texts if not s.startswith("website_") and len(s) > 3]
            if other:
                print(f"    Other strings: {other[:5]}")

    # Final summary
    print(f"\n{'='*70}")
    print(f"=== FINAL SUMMARY ===")
    print(f"{'='*70}")

    print(f"\nGameflow controller PIDs by category:")
    for category, items in sorted(results_by_category.items()):
        pids = sorted(item['pid'] for item in items)
        print(f"  {category}: {pids}")

    print(f"\nCOMPLETE SKIP_PIDS for level3 ({len(all_skip_pids)} total):")
    print(f"SKIP_PIDS = {sorted(all_skip_pids)}")

if __name__ == "__main__":
    main()
