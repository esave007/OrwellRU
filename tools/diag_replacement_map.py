#!/usr/bin/env python3
"""
DEEP DIAGNOSTIC: full replacement map for level3.
For EVERY replacement that patch_level3.py would make, record:
  (pid, script_class_name, offset_in_object, key)
Resolve MonoBehaviour script class names via m_Script PPtr -> MonoScript in external assets.
Flag:
  - replacements at m_Name offset (28)
  - replacements in non-display script classes (anything not TextMeshProUGUI etc.)
  - replacements at suspicious early offsets
"""
import os, sys, struct, json, glob
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

PROJECT = Path(r"C:\Projects\OrwellRU")
BACKUP = PROJECT / "backup"

# Same SKIP_PIDS as patch_level3.py
SKIP_PIDS = {
    44155, 44858,
    41412, 41652, 41856, 41931, 42208, 42221, 42226, 42419, 42683, 42822,
    43123, 43702, 43741, 44066, 44067, 44072, 44443, 44527, 44790, 44983,
    45023, 45149, 45221, 45251, 45329, 45550, 45654, 45705, 45729, 46450,
    46583, 46947, 46965, 47041, 47147, 47196, 47252, 47281, 47362, 47405,
    47510, 47519, 47584, 47596, 47909, 48018, 48057, 48097, 48490, 48559,
    48716, 48723, 48728, 48759, 48767, 48961, 49061, 49114, 49134, 49247,
    49304, 49392, 50181, 50759, 50868, 50969, 50982, 51002, 51035, 51052,
    51190, 51532, 51860, 52012, 52354, 53255, 53494, 53564, 53661, 53706,
    53809, 53942, 54421,
}


def load_translations():
    translations = {}
    pattern = str(PROJECT / "translated" / "batch_level3_*.json")
    for fpath in sorted(glob.glob(pattern)):
        with open(fpath, 'r', encoding='utf-8') as f:
            batch = json.load(f)
        for k, v in batch.items():
            if v:
                translations[k] = (v, Path(fpath).name)
    return translations


def find_matches(raw, translations_sorted):
    """Simulate find_and_replace_strings, but record (offset, key) per match.
    Replicates the exact in-place mutation order so offsets match reality."""
    data = bytearray(raw)
    hits = []
    for eng, (rus, src) in translations_sorted:
        eng_bytes = eng.encode('utf-8')
        rus_bytes = rus.encode('utf-8')
        prefix = struct.pack('<I', len(eng_bytes))
        needle = prefix + eng_bytes
        pos = 0
        while True:
            pos = data.find(needle, pos)
            if pos == -1:
                break
            old_len = len(eng_bytes)
            new_len = len(rus_bytes)
            old_padding = (4 - (old_len % 4)) % 4
            new_padding = (4 - (new_len % 4)) % 4
            old_total = 4 + old_len + old_padding
            new_total = 4 + new_len + new_padding
            replacement = struct.pack('<I', new_len) + rus_bytes + b'\x00' * new_padding
            hits.append((pos, eng, src))
            data[pos:pos + old_total] = replacement
            pos += new_total
    return hits


def read_string_at(raw, off):
    try:
        slen = struct.unpack_from('<I', raw, off)[0]
        if slen > 100000 or off + 4 + slen > len(raw):
            return None
        return raw[off+4:off+4+slen].decode('utf-8', errors='replace')
    except Exception:
        return None


def main():
    print("Parsing backup/level3 ...")
    usf = UnitySerializedFile(str(BACKUP / "level3"))
    print(f"  {len(usf.objects)} objects, unity {usf.unity_version}")

    translations = load_translations()
    print(f"  {len(translations)} translations loaded")
    translations_sorted = sorted(translations.items(), key=lambda x: len(x[0]), reverse=True)

    # ------------------------------------------------------------------
    # Resolve script class name per MonoBehaviour type_index
    # m_Script PPtr: fileID @16 (int32), pathID @20 (int64)
    # ------------------------------------------------------------------
    print("\nResolving MonoScript names per type_index ...")
    # Gather one sample (fileID, pathID) per type_index
    sample_script = {}  # type_index -> (file_id, path_id)
    for obj in usf.objects:
        ti = obj['type_index']
        if usf.types[ti]['class_id'] != 114 or ti in sample_script:
            continue
        raw = usf.get_object_data(obj['path_id'])
        if not raw or len(raw) < 28:
            continue
        fid = struct.unpack_from('<i', raw, 16)[0]
        pid = struct.unpack_from('<q', raw, 20)[0]
        sample_script[ti] = (fid, pid)

    # Map externals index -> file path (fileID is 1-based into externals; 0 = self)
    ext_files = {}
    for i, e in enumerate(usf.externals):
        name = e['file_path'].split('/')[-1]
        ext_files[i + 1] = name

    # Load MonoScripts from referenced files via UnityPy
    import UnityPy
    GAME_BACKUP_FILES = {
        'globalgamemanagers.assets': BACKUP / 'globalgamemanagers.assets',
        'sharedassets1.assets': BACKUP / 'sharedassets1.assets',
        'sharedassets3.assets': BACKUP / 'sharedassets3.assets',
        'sharedassets0.assets': BACKUP / 'sharedassets0.assets',
        'resources.assets': BACKUP / 'resources.assets',
    }
    GAME_DIR = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")

    monoscript_names = {}  # (ext_name, path_id) -> class name
    needed_files = set(ext_files.get(fid) for fid, _ in sample_script.values() if fid > 0)
    needed_files.discard(None)
    for fname in needed_files:
        fpath = GAME_BACKUP_FILES.get(fname)
        if fpath is None or not fpath.exists():
            fpath = GAME_DIR / fname
        if not fpath.exists():
            print(f"  WARN: cannot find {fname}")
            continue
        env = UnityPy.load(str(fpath))
        n = 0
        for o in env.objects:
            if o.type.name == 'MonoScript':
                tree = o.read_typetree()
                monoscript_names[(fname, o.path_id)] = tree.get('m_ClassName', '?')
                n += 1
        print(f"  {fname}: {n} MonoScripts")

    type_name = {}
    for ti, (fid, spid) in sample_script.items():
        fname = ext_files.get(fid, f'<file{fid}>')
        type_name[ti] = monoscript_names.get((fname, spid), f'<unresolved {fname}#{spid}>')

    # ------------------------------------------------------------------
    # Build full replacement map
    # ------------------------------------------------------------------
    print("\nBuilding full replacement map (this takes a while) ...")
    from collections import defaultdict, Counter

    per_class_hits = defaultdict(list)  # class_name -> [(pid, offset, key, src)]
    total = 0
    for obj in usf.objects:
        ti = obj['type_index']
        if usf.types[ti]['class_id'] != 114:
            continue
        if obj['path_id'] in SKIP_PIDS:
            continue
        raw = usf.get_object_data(obj['path_id'])
        if not raw or len(raw) < 20:
            continue
        hits = find_matches(raw, translations_sorted)
        if not hits:
            continue
        cname = type_name.get(ti, '?')
        for off, key, src in hits:
            per_class_hits[cname].append((obj['path_id'], off, key, src, raw))
            total += 1

    print(f"  TOTAL replacements: {total}")

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("REPLACEMENTS PER SCRIPT CLASS")
    print("=" * 70)
    for cname in sorted(per_class_hits, key=lambda c: -len(per_class_hits[c])):
        hits = per_class_hits[cname]
        offs = Counter(h[1] for h in hits)
        off_summary = ', '.join(f'@{o}x{n}' for o, n in offs.most_common(6))
        print(f"\n{cname}: {len(hits)} hits in {len(set(h[0] for h in hits))} objects")
        print(f"  offsets: {off_summary}{' ...' if len(offs) > 6 else ''}")

    # Suspicious: m_Name hits (offset 28)
    print("\n" + "=" * 70)
    print("SUSPICIOUS: replacements at m_Name offset (28) or earlier")
    print("=" * 70)
    n_susp = 0
    for cname, hits in per_class_hits.items():
        for pid, off, key, src, raw in hits:
            if off <= 28:
                mname = read_string_at(raw, 28)
                print(f"  {cname} PID={pid} @{off} key={key[:60]!r} src={src} m_Name={mname!r}")
                n_susp += 1
    if n_susp == 0:
        print("  none")

    # Dump detailed JSON for further analysis
    out = []
    for cname, hits in per_class_hits.items():
        for pid, off, key, src, raw in hits:
            out.append({'class': cname, 'pid': pid, 'offset': off,
                        'key': key, 'src': src})
    out_path = PROJECT / 'originals' / 'level3_replacement_map.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\nSaved detailed map: {out_path} ({len(out)} entries)")


if __name__ == '__main__':
    main()
