#!/usr/bin/env python3
"""
DEEP DIAGNOSTIC for resources.assets: full replacement map with script class names.
Replicates patch_resources_mono.py skip logic exactly.
"""
import os, sys, struct, json, glob
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

PROJECT = Path(r"C:\Projects\OrwellRU")
BACKUP = PROJECT / "backup"

SKIP_TYPE_INDICES = {
    7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
    25, 26, 27, 28, 29, 31, 37, 39, 40, 41, 45, 46, 47, 48, 49, 50, 51,
    52, 53, 54, 55,
}
SKIP_PIDS = {
    696, 697, 698, 699, 700,
    733, 734, 735, 736, 737, 738, 739, 740, 741, 742,
    796, 797, 798, 799, 800, 801, 802, 803, 804, 805,
    806, 807, 808, 809, 810, 811, 812, 813, 814, 815,
    816, 817, 818, 819, 820, 821, 822, 823, 824, 825,
    826, 827, 828,
}


def load_translations():
    translations = {}
    pattern = str(PROJECT / "translated" / "batch_resources_*.json")
    for fpath in sorted(glob.glob(pattern)):
        with open(fpath, 'r', encoding='utf-8') as f:
            batch = json.load(f)
        for k, v in batch.items():
            if v and v != k:
                translations[k] = (v, Path(fpath).name)
    l3_pattern = str(PROJECT / "translated" / "batch_level3_*.json")
    for fpath in sorted(glob.glob(l3_pattern)):
        with open(fpath, 'r', encoding='utf-8') as f:
            batch = json.load(f)
        for k, v in batch.items():
            if v and k not in translations:
                translations[k] = (v, Path(fpath).name)
    return translations


def find_matches(raw, translations_sorted):
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
            old_len, new_len = len(eng_bytes), len(rus_bytes)
            old_total = 4 + old_len + (4 - old_len % 4) % 4
            new_total = 4 + new_len + (4 - new_len % 4) % 4
            replacement = struct.pack('<I', new_len) + rus_bytes + b'\x00' * ((4 - new_len % 4) % 4)
            hits.append((pos, eng, src, rus))
            data[pos:pos + old_total] = replacement
            pos += new_total
    return hits


def main():
    print("Parsing backup/resources.assets ...")
    usf = UnitySerializedFile(str(BACKUP / "resources.assets"))
    print(f"  {len(usf.objects)} objects, {len(usf.types)} types")

    translations = load_translations()
    print(f"  {len(translations)} translations")
    translations_sorted = sorted(translations.items(), key=lambda x: len(x[0]), reverse=True)

    # Resolve script names: m_Script PPtr fileID @16, pathID @20
    sample_script = {}
    for obj in usf.objects:
        ti = obj['type_index']
        if usf.types[ti]['class_id'] != 114 or ti in sample_script:
            continue
        raw = usf.get_object_data(obj['path_id'])
        if not raw or len(raw) < 28:
            continue
        fid = struct.unpack_from('<i', raw, 16)[0]
        spid = struct.unpack_from('<q', raw, 20)[0]
        sample_script[ti] = (fid, spid)

    ext_files = {i + 1: e['file_path'].split('/')[-1] for i, e in enumerate(usf.externals)}
    print("  externals:", ext_files)

    import UnityPy
    GAME_DIR = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
    monoscript_names = {}
    needed = set()
    for fid, _ in sample_script.values():
        needed.add('<self>' if fid == 0 else ext_files.get(fid))
    needed.discard(None)
    for fname in needed:
        fpath = (BACKUP / 'resources.assets') if fname == '<self>' else (
            (BACKUP / fname) if (BACKUP / fname).exists() else GAME_DIR / fname)
        if not fpath.exists():
            print(f"  WARN: missing {fname}")
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
        fname = '<self>' if fid == 0 else ext_files.get(fid, f'<file{fid}>')
        type_name[ti] = monoscript_names.get((fname, spid), f'<unresolved {fname}#{spid}>')

    from collections import defaultdict, Counter
    per_class = defaultdict(list)
    total = 0
    for obj in usf.objects:
        ti = obj['type_index']
        if usf.types[ti]['class_id'] != 114:
            continue
        if ti in SKIP_TYPE_INDICES or obj['path_id'] in SKIP_PIDS:
            continue
        raw = usf.get_object_data(obj['path_id'])
        if not raw or len(raw) < 20:
            continue
        hits = find_matches(raw, translations_sorted)
        for off, key, src, rus in hits:
            real = (translations[key][0] != key)
            per_class[type_name.get(ti, f'?ti{ti}')].append(
                {'pid': obj['path_id'], 'ti': ti, 'offset': off, 'key': key,
                 'src': src, 'real': real})
            total += 1

    print(f"\nTOTAL replacements: {total}")
    print("\n" + "=" * 70)
    print("PER SCRIPT CLASS (real byte changes only)")
    print("=" * 70)
    out = []
    for cname in sorted(per_class, key=lambda c: -len(per_class[c])):
        hits = [h for h in per_class[cname] if h['real']]
        if not hits:
            continue
        offs = Counter(h['offset'] for h in hits)
        off_s = ', '.join(f'@{o}x{n}' for o, n in offs.most_common(6))
        print(f"\n{cname} (ti={hits[0]['ti']}): {len(hits)} real hits in "
              f"{len(set(h['pid'] for h in hits))} objects")
        print(f"  offsets: {off_s}")
        keys = Counter(h['key'] for h in hits)
        for k, n in keys.most_common(5):
            print(f"    x{n} {k[:70]!r}")
        out.extend(hits)

    for h in per_class.values():
        pass
    with open(PROJECT / 'originals' / 'resources_replacement_map.json', 'w', encoding='utf-8') as f:
        json.dump([h for v in per_class.values() for h in v], f, ensure_ascii=False, indent=1)
    print(f"\nSaved: originals/resources_replacement_map.json")


if __name__ == '__main__':
    main()
