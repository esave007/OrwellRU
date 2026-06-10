#!/usr/bin/env python3
"""
Diagnostic script: compare MonoBehaviour objects between backup and patched
resources.assets to find incorrectly translated identifier fields.

Extracts all length-prefixed UTF-8 strings from each MonoBehaviour object
and reports differences, grouped by type_index.
"""
import os, sys, struct
from collections import defaultdict

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

# Add tools/ to path for unity_serialized_patcher
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from unity_serialized_patcher import UnitySerializedFile

PROJECT = r"C:\Projects\OrwellRU"
BACKUP = os.path.join(PROJECT, "backup", "resources.assets")
PATCHED = os.path.join(PROJECT, "patches", "resources.assets")


def extract_strings(data: bytes) -> list:
    """Extract all length-prefixed UTF-8 strings from raw object data.

    Format: [4-byte LE uint32 length][UTF-8 bytes][0-3 padding to 4-byte align]
    Returns list of (offset, string_value).
    """
    strings = []
    pos = 0
    data_len = len(data)

    while pos + 4 <= data_len:
        str_len = struct.unpack_from('<I', data, pos)[0]

        # Sanity checks: reasonable string length, fits in data
        if str_len == 0 or str_len > 100000 or pos + 4 + str_len > data_len:
            pos += 4
            continue

        raw = data[pos + 4: pos + 4 + str_len]

        # Try to decode as UTF-8
        try:
            text = raw.decode('utf-8')
            # Filter: must contain at least one printable ASCII or Cyrillic char
            # and not be all null bytes or control chars
            if any(c.isprintable() and ord(c) >= 32 for c in text):
                strings.append((pos, text))
        except (UnicodeDecodeError, ValueError):
            pass

        # Move past: 4 (length) + str_len + padding
        padded_len = (str_len + 3) & ~3
        pos += 4 + padded_len

    return strings


def main():
    print("=" * 80)
    print("DIAGNOSTIC: MonoBehaviour string differences in resources.assets")
    print("=" * 80)

    print(f"\nParsing backup: {BACKUP}")
    backup = UnitySerializedFile(BACKUP)
    print(f"  Objects: {len(backup.objects)}, data_offset: {backup.data_offset}")

    print(f"\nParsing patched: {PATCHED}")
    patched = UnitySerializedFile(PATCHED)
    print(f"  Objects: {len(patched.objects)}, data_offset: {patched.data_offset}")

    # Build lookup by path_id for both files
    backup_objs = {}
    for obj in backup.objects:
        if backup.types[obj['type_index']]['class_id'] == 114:
            abs_off = backup.data_offset + obj['offset']
            backup_objs[obj['path_id']] = {
                'type_index': obj['type_index'],
                'data': bytes(backup.data[abs_off:abs_off + obj['size']]),
                'size': obj['size'],
            }

    patched_objs = {}
    for obj in patched.objects:
        if patched.types[obj['type_index']]['class_id'] == 114:
            abs_off = patched.data_offset + obj['offset']
            patched_objs[obj['path_id']] = {
                'type_index': obj['type_index'],
                'data': bytes(patched.data[abs_off:abs_off + obj['size']]),
                'size': obj['size'],
            }

    print(f"\nMonoBehaviour objects: backup={len(backup_objs)}, patched={len(patched_objs)}")

    # Compare
    # Group results by type_index
    changes_by_type = defaultdict(list)  # type_index -> list of changes
    short_string_changes = []  # specifically for short identifiers

    common_pids = set(backup_objs.keys()) & set(patched_objs.keys())
    print(f"Common path_ids to compare: {len(common_pids)}")

    modified_count = 0

    for pid in sorted(common_pids):
        b = backup_objs[pid]
        p = patched_objs[pid]

        # Quick check: if data is identical, skip
        if b['data'] == p['data']:
            continue

        modified_count += 1

        b_strings = extract_strings(b['data'])
        p_strings = extract_strings(p['data'])

        # Build offset->string maps, but also compare by position index
        # Since replacements change sizes, offsets will shift.
        # Better approach: compare string lists sequentially.
        # But actually the patcher replaces in-place without changing size structure...
        # Let's compare by matching original strings to find which ones changed.

        b_set = set(s for _, s in b_strings)
        p_set = set(s for _, s in p_strings)

        removed = b_set - p_set  # strings in backup not in patched
        added = p_set - b_set    # strings in patched not in backup

        if not removed and not added:
            continue

        type_idx = b['type_index']

        # For each removed string, try to find a plausible replacement
        # by looking at positional correspondence
        b_list = [(off, s) for off, s in b_strings]
        p_list = [(off, s) for off, s in p_strings]

        pairs = []
        # Match by index position (strings extracted in same order)
        for i in range(min(len(b_list), len(p_list))):
            b_off, b_s = b_list[i]
            p_off, p_s = p_list[i]
            if b_s != p_s:
                pairs.append((b_off, b_s, p_s))

        for b_off, orig, trans in pairs:
            entry = {
                'path_id': pid,
                'offset': b_off,
                'original': orig[:120],
                'translated': trans[:120],
                'orig_len': len(orig),
                'trans_len': len(trans),
            }
            changes_by_type[type_idx].append(entry)

            if len(orig) < 30:
                short_string_changes.append({
                    'type_index': type_idx,
                    **entry,
                })

    print(f"\nModified MonoBehaviour objects: {modified_count}")

    # Report by type_index
    print("\n" + "=" * 80)
    print("CHANGES GROUPED BY TYPE_INDEX")
    print("=" * 80)

    for type_idx in sorted(changes_by_type.keys()):
        changes = changes_by_type[type_idx]
        unique_pids = set(c['path_id'] for c in changes)
        print(f"\n--- TYPE_INDEX {type_idx} ({len(changes)} string changes in {len(unique_pids)} objects) ---")

        for c in changes[:50]:  # limit output per type
            flag = " *** SHORT ID? ***" if c['orig_len'] < 30 else ""
            print(f"  PID {c['path_id']:>6} @{c['offset']:>5}: "
                  f"[{c['orig_len']:>4}] \"{c['original'][:80]}\"")
            print(f"  {'':>6} {'':>6}  -> \"{c['translated'][:80]}\"{flag}")

        if len(changes) > 50:
            print(f"  ... and {len(changes) - 50} more changes")

    # Short string changes (potential identifiers)
    print("\n" + "=" * 80)
    print(f"SHORT STRING CHANGES (< 30 chars) — POTENTIAL IDENTIFIERS: {len(short_string_changes)}")
    print("=" * 80)

    for c in short_string_changes:
        print(f"  TYPE_IDX {c['type_index']:>3} | PID {c['path_id']:>6} | "
              f"\"{c['original']}\" -> \"{c['translated']}\"")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY: TYPE_INDEX MODIFICATION COUNTS")
    print("=" * 80)

    for type_idx in sorted(changes_by_type.keys()):
        changes = changes_by_type[type_idx]
        unique_pids = set(c['path_id'] for c in changes)
        short_count = sum(1 for c in changes if c['orig_len'] < 30)
        print(f"  type_index={type_idx:>3}: {len(changes):>5} changes in {len(unique_pids):>4} objects "
              f"({short_count} short strings)")

    print(f"\nTotal: {sum(len(v) for v in changes_by_type.values())} string changes "
          f"across {modified_count} modified objects")

    # Cross-reference with current SKIP_TYPE_INDICES
    print("\n" + "=" * 80)
    print("CURRENT SKIP_TYPE_INDICES CHECK")
    print("=" * 80)

    # Read from patch_resources_mono.py
    skip_file = os.path.join(PROJECT, "tools", "patch_resources_mono.py")
    if os.path.exists(skip_file):
        with open(skip_file, 'r', encoding='utf-8') as f:
            content = f.read()
        # Find SKIP_TYPE_INDICES
        import re
        m = re.search(r'SKIP_TYPE_INDICES\s*=\s*\{([^}]+)\}', content)
        if m:
            skip_indices = set()
            for num in re.findall(r'\d+', m.group(1)):
                skip_indices.add(int(num))
            print(f"  Current SKIP_TYPE_INDICES: {sorted(skip_indices)}")
            print(f"  Modified type_indices: {sorted(changes_by_type.keys())}")

            modified_but_not_skipped = set(changes_by_type.keys()) - skip_indices
            skipped_but_modified = set(changes_by_type.keys()) & skip_indices

            if modified_but_not_skipped:
                print(f"\n  MODIFIED but NOT in SKIP list: {sorted(modified_but_not_skipped)}")
                print("  (These are intentionally translated types)")
            if skipped_but_modified:
                print(f"\n  WARNING: In SKIP list but STILL modified: {sorted(skipped_but_modified)}")
                print("  (This should NOT happen!)")
        else:
            print("  Could not parse SKIP_TYPE_INDICES")

    print("\nDone.")


if __name__ == '__main__':
    main()
