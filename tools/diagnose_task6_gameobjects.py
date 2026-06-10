#!/usr/bin/env python3
"""
Diagnostic script: investigate Task 6 white text bug in level4.

Goal: Find all components on the same GameObjects as RectTransform PIDs 852, 880
(problematic chunk boxes) and compare with PID 753 (working chunk box).

Unity 5.x GameObject (class_id=1) format:
  [uint32 component_count]
  [component_count * (int32 classID_pair_first, int32 file_index, int64 path_id)]
  ... then name and other fields ...
"""
import os, sys, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

BACKUP_LEVEL4 = r"C:\Projects\OrwellRU\backup\level4"

# PIDs we're investigating
TARGET_RT_PIDS = [753, 852, 880]
# Also check some known working chunk boxes for comparison
EXTRA_RT_PIDS = [776, 800, 824]  # Tasks 2,3,4 row 0 chunk boxes (likely working)

ALL_INTEREST_PIDS = TARGET_RT_PIDS + EXTRA_RT_PIDS


def parse_gameobject_components(raw_data):
    """
    Parse a GameObject's component list from raw object data.

    Unity 5.x GameObject serialized format (version 17):
      uint32 component_count
      For each component: PPtr<Component> = int32 file_index + int64 path_id = 12 bytes
      uint32 layer
      length-prefixed string: name (uint32 len + bytes + alignment)
      uint16 tag
      bool isActive
    """
    pos = 0

    comp_count = struct.unpack_from('<I', raw_data, pos)[0]
    pos += 4

    if comp_count > 50:  # sanity check
        return None, "comp_count too large: {}".format(comp_count)

    components = []
    for i in range(comp_count):
        # PPtr: int32 file_index + int64 path_id = 12 bytes
        file_index = struct.unpack_from('<i', raw_data, pos)[0]
        path_id = struct.unpack_from('<q', raw_data, pos + 4)[0]
        components.append({
            'file_index': file_index,
            'path_id': path_id,
        })
        pos += 12

    # After components: layer (uint32)
    layer = struct.unpack_from('<I', raw_data, pos)[0]
    pos += 4

    # Name: length-prefixed string
    name_len = struct.unpack_from('<I', raw_data, pos)[0]
    pos += 4
    name = ""
    if 0 < name_len < 1000:
        try:
            name = raw_data[pos:pos+name_len].decode('utf-8')
        except:
            name = f"<binary {name_len} bytes>"

    return components, name


def dump_hex(data, max_bytes=256):
    """Hex dump with ASCII sidebar."""
    lines = []
    for i in range(0, min(len(data), max_bytes), 16):
        chunk = data[i:i+16]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        lines.append(f"  {i:04x}: {hex_part:<48s} {ascii_part}")
    if len(data) > max_bytes:
        lines.append(f"  ... ({len(data)} bytes total, showing first {max_bytes})")
    return '\n'.join(lines)


def find_floats_in_range(data, label=""):
    """Find sequences of 4 consecutive floats that look like RGBA color values (0.0-1.0)."""
    colors = []
    for i in range(0, len(data) - 15, 4):
        vals = struct.unpack_from('<4f', data, i)
        if all(0.0 <= v <= 1.0 for v in vals):
            # Could be RGBA
            r, g, b, a = vals
            # Filter: at least one channel > 0 and alpha > 0
            if a > 0.0 and (r > 0.0 or g > 0.0 or b > 0.0):
                colors.append((i, r, g, b, a))
    return colors


def main():
    print(f"Loading: {BACKUP_LEVEL4}")
    usf = UnitySerializedFile(BACKUP_LEVEL4)
    print(f"  Objects: {len(usf.objects)}, Types: {len(usf.types)}")

    # Build class_id lookup
    print("\nType table:")
    for i, t in enumerate(usf.types):
        print(f"  type_index={i}: class_id={t['class_id']}")

    # Build path_id -> (class_id, type_index) mapping
    pid_to_info = {}
    for obj in usf.objects:
        class_id = usf.types[obj['type_index']]['class_id']
        pid_to_info[obj['path_id']] = {
            'class_id': class_id,
            'type_index': obj['type_index'],
            'offset': obj['offset'],
            'size': obj['size'],
        }

    # Count objects by class_id
    class_counts = {}
    for pid, info in pid_to_info.items():
        cid = info['class_id']
        class_counts[cid] = class_counts.get(cid, 0) + 1
    print("\nObject counts by class_id:")
    for cid, cnt in sorted(class_counts.items()):
        print(f"  class_id={cid}: {cnt} objects")

    # Find all GameObjects (class_id=1) and parse their components
    print("\n" + "="*80)
    print("PARSING ALL GAMEOBJECTS TO FIND OWNERS OF TARGET RECTTRANSFORMS")
    print("="*80)

    # Map: component_path_id -> (gameobject_pid, gameobject_name, all_components)
    component_to_gameobject = {}
    gameobject_data = {}  # go_pid -> (name, components)

    for obj in usf.objects:
        class_id = usf.types[obj['type_index']]['class_id']
        if class_id != 1:  # Not a GameObject
            continue

        go_pid = obj['path_id']
        raw = usf.get_object_data(go_pid)
        components, name = parse_gameobject_components(raw)

        if components is None:
            continue

        gameobject_data[go_pid] = (name, components)

        for comp in components:
            if comp['file_index'] == 0:  # Same file
                component_to_gameobject[comp['path_id']] = go_pid

    print(f"\nParsed {len(gameobject_data)} GameObjects")

    # Find GameObjects that own our target RectTransforms
    print("\n" + "="*80)
    print("GAMEOBJECTS OWNING TARGET RECTTRANSFORMS")
    print("="*80)

    for rt_pid in ALL_INTEREST_PIDS:
        print(f"\n--- RectTransform PID {rt_pid} ---")

        if rt_pid not in component_to_gameobject:
            print(f"  WARNING: No GameObject found owning RectTransform PID {rt_pid}")
            # Try alternate parse format
            continue

        go_pid = component_to_gameobject[rt_pid]
        name, components = gameobject_data[go_pid]
        print(f"  GameObject PID={go_pid}, Name=\"{name}\"")
        print(f"  Components ({len(components)}):")

        for comp in components:
            cpid = comp['path_id']
            cinfo = pid_to_info.get(cpid, None)
            if cinfo:
                cclass = cinfo['class_id']
                csize = cinfo['size']
                print(f"    PID={cpid}, class_id={cclass}, size={csize} bytes")
            else:
                print(f"    PID={cpid}, file_index={comp['file_index']} (external or unknown)")

    # Now dump component data for the interesting GameObjects
    print("\n" + "="*80)
    print("DETAILED COMPONENT ANALYSIS")
    print("="*80)

    for rt_pid in ALL_INTEREST_PIDS:
        if rt_pid not in component_to_gameobject:
            continue

        go_pid = component_to_gameobject[rt_pid]
        name, components = gameobject_data[go_pid]

        print(f"\n{'='*60}")
        print(f"RT PID {rt_pid} -> GameObject \"{name}\" (PID {go_pid})")
        print(f"{'='*60}")

        for comp in components:
            cpid = comp['path_id']
            cinfo = pid_to_info.get(cpid, None)
            if not cinfo:
                continue

            cclass = cinfo['class_id']
            raw = usf.get_object_data(cpid)

            # Skip RectTransform itself (we know about those)
            if cclass == 224:
                print(f"\n  [RectTransform PID={cpid}] size={len(raw)} bytes (skipping detail)")
                continue

            # Skip CanvasRenderer (class_id=222) - usually empty
            if cclass == 222:
                print(f"\n  [CanvasRenderer PID={cpid}] size={len(raw)} bytes")
                if len(raw) > 0:
                    print(dump_hex(raw, 64))
                continue

            class_name = {
                1: "GameObject",
                4: "Transform",
                114: "MonoBehaviour",
                222: "CanvasRenderer",
                224: "RectTransform",
                225: "CanvasGroup",
            }.get(cclass, f"Unknown({cclass})")

            print(f"\n  [{class_name} PID={cpid}] size={len(raw)} bytes")
            print(dump_hex(raw, 320))

            # Look for RGBA color values
            if cclass == 114 and len(raw) > 16:
                colors = find_floats_in_range(raw)
                if colors:
                    print(f"\n  Potential RGBA colors found:")
                    for offset, r, g, b, a in colors:
                        # Highlight likely Image colors
                        desc = ""
                        if r > 0.9 and g > 0.9 and b > 0.9:
                            desc = " *** WHITE ***"
                        elif b > 0.5 and r < 0.3 and g < 0.5:
                            desc = " (blue-ish)"
                        elif r < 0.1 and g < 0.1 and b < 0.1:
                            desc = " (near-black)"
                        print(f"    @{offset}: R={r:.4f} G={g:.4f} B={b:.4f} A={a:.4f}{desc}")

    # BONUS: Try to identify which MonoBehaviours are Image components
    # by looking at their script reference in the type table
    print("\n" + "="*80)
    print("MONOBEHAVIOUR SCRIPT HASHES (to identify Image vs other)")
    print("="*80)

    # Collect unique MonoBehaviour type indices used by our target components
    target_mono_types = set()
    for rt_pid in ALL_INTEREST_PIDS:
        if rt_pid not in component_to_gameobject:
            continue
        go_pid = component_to_gameobject[rt_pid]
        _, components = gameobject_data[go_pid]
        for comp in components:
            cpid = comp['path_id']
            cinfo = pid_to_info.get(cpid)
            if cinfo and cinfo['class_id'] == 114:
                target_mono_types.add(cinfo['type_index'])

    for ti in sorted(target_mono_types):
        t = usf.types[ti]
        sh = t.get('script_hash')
        th = t.get('type_hash')
        print(f"  type_index={ti}: script_hash={sh.hex() if sh else 'N/A'}, type_hash={th.hex() if th else 'N/A'}")

    # Compare raw data sizes of MonoBehaviours across working vs broken chunk boxes
    print("\n" + "="*80)
    print("COMPARISON: WORKING (753) vs BROKEN (852, 880) MONOBEHAVIOUR SIZES")
    print("="*80)

    for rt_pid in [753, 852, 880]:
        if rt_pid not in component_to_gameobject:
            print(f"  RT PID {rt_pid}: not found")
            continue
        go_pid = component_to_gameobject[rt_pid]
        name, components = gameobject_data[go_pid]
        monos = []
        for comp in components:
            cpid = comp['path_id']
            cinfo = pid_to_info.get(cpid)
            if cinfo and cinfo['class_id'] == 114:
                monos.append((cpid, cinfo['size'], cinfo['type_index']))
        print(f"\n  RT PID {rt_pid} -> GO \"{name}\":")
        for cpid, sz, ti in monos:
            print(f"    MonoBehaviour PID={cpid}, size={sz}, type_index={ti}")

    # Do byte-by-byte comparison of MonoBehaviours with same type_index
    print("\n" + "="*80)
    print("BYTE-LEVEL DIFF: MonoBehaviours between working (753) and broken (852, 880)")
    print("="*80)

    def get_monos_for_rt(rt_pid):
        """Get list of (pid, type_index, raw_data) for MonoBehaviours on this RT's GO."""
        if rt_pid not in component_to_gameobject:
            return []
        go_pid = component_to_gameobject[rt_pid]
        _, components = gameobject_data[go_pid]
        result = []
        for comp in components:
            cpid = comp['path_id']
            cinfo = pid_to_info.get(cpid)
            if cinfo and cinfo['class_id'] == 114:
                raw = usf.get_object_data(cpid)
                result.append((cpid, cinfo['type_index'], raw))
        return result

    ref_monos = get_monos_for_rt(753)
    ref_by_ti = {ti: (pid, raw) for pid, ti, raw in ref_monos}

    for broken_pid in [852, 880]:
        broken_monos = get_monos_for_rt(broken_pid)
        for bpid, bti, braw in broken_monos:
            if bti in ref_by_ti:
                rpid, rraw = ref_by_ti[bti]
                print(f"\n  Comparing: PID {rpid} (working, RT 753) vs PID {bpid} (broken, RT {broken_pid})")
                print(f"  Same type_index={bti}, sizes: {len(rraw)} vs {len(braw)}")

                if rraw == braw:
                    print(f"  IDENTICAL bytes!")
                else:
                    # Find differences
                    min_len = min(len(rraw), len(braw))
                    diffs = []
                    for i in range(min_len):
                        if rraw[i] != braw[i]:
                            diffs.append(i)
                    if len(rraw) != len(braw):
                        diffs.append(min_len)  # size diff marker

                    print(f"  DIFFERENCES at {len(diffs)} byte positions:")
                    for d in diffs[:30]:  # show first 30 diffs
                        if d < min_len:
                            # Show context: 4 floats around the diff
                            aligned = (d // 4) * 4
                            if aligned + 4 <= min_len:
                                rv = struct.unpack_from('<f', rraw, aligned)[0]
                                bv = struct.unpack_from('<f', braw, aligned)[0]
                                print(f"    @{d} (float@{aligned}): ref=0x{rraw[d]:02x} broken=0x{braw[d]:02x}  float: {rv} vs {bv}")
                            else:
                                print(f"    @{d}: ref=0x{rraw[d]:02x} broken=0x{braw[d]:02x}")
                        else:
                            print(f"    Size difference: {len(rraw)} vs {len(braw)}")
            else:
                print(f"\n  PID {bpid} (broken, RT {broken_pid}): type_index={bti} - NO MATCH in working RT 753")
                print(f"  Raw ({len(braw)} bytes):")
                print(dump_hex(braw, 256))

    print("\n\nDONE.")


if __name__ == "__main__":
    main()
