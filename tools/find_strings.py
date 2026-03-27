#!/usr/bin/env python3
"""
Search for specific strings in Unity binary files (level4, resources.assets, resources.assets.resS)
Reports byte offsets and attempts to map to path_id objects using UnitySerializedFile parser.
"""
import os, sys, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

BACKUP = Path(r"C:\Projects\OrwellRU\backup")

STRINGS = [
    "Drag and drop",
    "I want to make",
    "I would rather",
    "Person #1",
    "TASK",
    "CANCEL",
    "NEXT STEP",
    "APPLICANT",
    "E-Mail",
    "Paired with",
    "Occupation",
    "Operating System",
]

def find_all(data: bytes, needle: bytes):
    """Return list of all byte offsets where needle occurs."""
    offsets = []
    pos = 0
    while True:
        idx = data.find(needle, pos)
        if idx == -1:
            break
        offsets.append(idx)
        pos = idx + 1
    return offsets

def get_full_unity_string(data: bytes, offset: int, max_len=500):
    """
    Given offset of UTF-8 needle inside data, try to read the full length-prefixed
    Unity string: 4-byte LE length prefix immediately before the text, then text bytes.
    Returns (prefix_offset, full_string) or None.
    """
    # Try to find the length prefix 4 bytes before the match position
    # But the match might be INSIDE the string, not at its start.
    # We look back for a valid 4-byte LE length that would encompass this position.
    # Also try exact prefix 4 bytes before.
    for back in range(0, min(offset, max_len) + 1):
        candidate = offset - back
        if candidate < 4:
            break
        slen = struct.unpack_from('<I', data, candidate - 4)[0]
        if slen < 1 or slen > 10000:
            continue
        if candidate + slen > len(data):
            continue
        # Check if this length would include our match
        if back <= slen:
            try:
                s = data[candidate:candidate + slen].decode('utf-8')
                return (candidate - 4, s)
            except:
                pass
    return None

def map_offset_to_object(usf: UnitySerializedFile, abs_offset: int):
    """Map an absolute file offset to the path_id that contains it."""
    data_offset = usf.data_offset
    rel = abs_offset - data_offset
    if rel < 0:
        return None
    # Objects have relative offsets
    for obj in sorted(usf.objects, key=lambda o: o['offset']):
        obj_start = obj['offset']
        obj_end = obj_start + obj['size']
        if obj_start <= rel < obj_end:
            class_id = usf.types[obj['type_index']]['class_id']
            return obj['path_id'], class_id, obj_start, obj_end
    return None

def search_file(filepath: Path, usf=None, label=""):
    print(f"\n{'='*70}")
    print(f"FILE: {filepath.name}  ({filepath.stat().st_size:,} bytes)  {label}")
    print(f"{'='*70}")

    with open(filepath, 'rb') as f:
        data = f.read()

    total_found = 0
    for needle_str in STRINGS:
        needle = needle_str.encode('utf-8')
        offsets = find_all(data, needle)
        if not offsets:
            print(f"\n  [NOT FOUND] \"{needle_str}\"")
            continue

        print(f"\n  [{len(offsets)} hit(s)] \"{needle_str}\"")
        for abs_off in offsets:
            total_found += 1
            # Try to read the full Unity length-prefixed string
            full = get_full_unity_string(data, abs_off, max_len=min(abs_off, 500))
            if full:
                prefix_off, full_str = full
                display = repr(full_str) if len(full_str) < 200 else repr(full_str[:200]) + "..."
                print(f"    offset=0x{abs_off:08X} ({abs_off:,})  full_string_prefix@0x{prefix_off:08X}")
                print(f"      Full text: {display}")
            else:
                # Show raw context
                ctx_start = max(0, abs_off - 8)
                ctx_end = min(len(data), abs_off + len(needle) + 80)
                ctx = data[ctx_start:ctx_end]
                print(f"    offset=0x{abs_off:08X} ({abs_off:,})  [no valid length prefix found]")
                # Try to show readable text around it
                try:
                    snippet = ctx.decode('utf-8', errors='replace')
                    print(f"      Context: {repr(snippet[:100])}")
                except:
                    pass

            # Map to object if we have the parser
            if usf:
                result = map_offset_to_object(usf, abs_off)
                if result:
                    path_id, class_id, obj_start, obj_end = result
                    CLASS_NAMES = {1: 'GameObject', 4: 'Transform', 23: 'Renderer',
                                   33: 'MeshFilter', 48: 'Shader', 49: 'TextAsset',
                                   64: 'MeshCollider', 65: 'BoxCollider',
                                   114: 'MonoBehaviour', 115: 'MonoScript',
                                   200: 'LineRenderer', 212: 'TextMeshProUGUI',
                                   213: 'TextMeshPro', 221: 'RectTransform',
                                   225: 'CanvasRenderer'}
                    cname = CLASS_NAMES.get(class_id, f'class_{class_id}')
                    obj_rel = abs_off - usf.data_offset - obj_start
                    print(f"      -> path_id={path_id}, class={class_id}({cname}), "
                          f"obj_range=[{obj_start}..{obj_end}], offset_in_obj={obj_rel}")
                else:
                    print(f"      -> offset not within any object data section (may be in metadata)")

    print(f"\n  TOTAL: {total_found} hits across all search strings")

def main():
    # --- level4 ---
    level4_path = BACKUP / "level4"
    if level4_path.exists():
        try:
            usf4 = UnitySerializedFile(str(level4_path))
            print(f"\nParsed level4: Unity={usf4.unity_version}, "
                  f"Objects={len(usf4.objects)}, data_offset=0x{usf4.data_offset:X}")
        except Exception as e:
            print(f"[WARN] Could not parse level4 as UnitySerializedFile: {e}")
            usf4 = None
        search_file(level4_path, usf4, "level4")
    else:
        print(f"[ERROR] level4 not found at {level4_path}")

    # --- resources.assets ---
    res_path = BACKUP / "resources.assets"
    if res_path.exists():
        try:
            usf_res = UnitySerializedFile(str(res_path))
            print(f"\nParsed resources.assets: Unity={usf_res.unity_version}, "
                  f"Objects={len(usf_res.objects)}, data_offset=0x{usf_res.data_offset:X}")
        except Exception as e:
            print(f"[WARN] Could not parse resources.assets as UnitySerializedFile: {e}")
            usf_res = None
        search_file(res_path, usf_res, "resources.assets")
    else:
        print(f"[ERROR] resources.assets not found at {res_path}")

    # --- resources.assets.resS (companion streaming data - no Unity header) ---
    ress_path = BACKUP / "resources.assets.resS"
    if ress_path.exists():
        search_file(ress_path, None, "resources.assets.resS (streaming, no header)")
    else:
        print(f"[INFO] resources.assets.resS not found (may not exist)")

    # --- Also search sharedassets0-4 for completeness ---
    for i in range(5):
        sa_path = BACKUP / f"sharedassets{i}.assets"
        if sa_path.exists():
            try:
                usf_sa = UnitySerializedFile(str(sa_path))
            except Exception as e:
                usf_sa = None
            search_file(sa_path, usf_sa, f"sharedassets{i}.assets")

if __name__ == "__main__":
    main()
