"""Translate TextLocalized fields that the RU mod skipped (flow-state objects in resources.assets).

Only the English slot (index 1) of TextLocalized string arrays is changed; IDs and other
fields stay intact. For UpdateProfileState the drag-highlight indices are recomputed so they
point at the Russian fragment.

Usage: apply_loc.py <in_dir> <out_dir> [<dict.json or dir> ...]   (later sources win)
Default sources: <repo>/translated (all batches of the mod) and then
<repo>/translated/batch_fix_untranslated.json (strings that had no translation yet).
"""
import os, re, sys, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttg import load

sys.stdout.reconfigure(encoding="utf-8")
CYR = re.compile("[А-Яа-яЁё]")
ID = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)+$")  # internal ids (image_xxx, slot_xxx): never touch

# plain string fields (not TextLocalized) that are only displayed
PLAIN_FIELDS = ("_weatherText", "_quote", "_thesisText")

# drag fragment overrides: english value -> russian fragment inside the russian value
DRAG_FIX = {
    "was threatened with death": "угрожали убийством",
    "received a Medal of Honor for saving civilians": "медаль",
    "believes Pargesian President Kassart to be Nation-controlled": "президент Паргеса Кассарт",
    "is being funded by donations from \"Angels of The Nation\"": "пожертвованиями от «Ангелов Нации»",
    "using a wheelchair": "в инвалидной коляске",
    "former principal at Prava Secondary": "Средней школы Правы",
    "lost his ability to walk due to being buried under concrete blocks after a FTP attack on his school": "СИП",
    "previously assigned to Outer Bonton Reception Camp after immigrating to The Nation": "приёмный лагерь Внешнего Бонтона",
    "is working on army supplies": "армейскими запасами",
    "interested in world peace, yoga, and green tea": "мировым миром, йогой и зелёным чаем",
    "threatens to make other people disappear": "устранить",
    "holds a degree in Psychology and Medicine": "психологии и медицине",
    "is maintaining a counselling website named Open Soteria": "Open Soteria",
    "member of Hand of Blood Fanclub": "фанклуба Hand of Blood",
    "received financial support by The Party": "Партии",
    "veteran of the Pargesian civil war": "ветеран",
    "officer of the Pargesian army": "офицер",
    "mobile phone UID: SP-33742-0683": "SP-33742-0683",
}


REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def json_pairs(path):
    """English->Russian pairs from any of the mod's JSON layouts (dict, {original, translation}, lists)."""
    d = json.load(open(path, encoding="utf-8"))
    if isinstance(d, dict) and isinstance(d.get("translations"), dict):
        d = d["translations"]
    items = d.items() if isinstance(d, dict) else enumerate(d if isinstance(d, list) else [])
    for k, v in items:
        if isinstance(v, str):
            yield k, v
        elif isinstance(v, dict):
            yield (v.get("original") or v.get("en") or v.get("text") or k), (v.get("translation") or v.get("ru"))


def load_dicts(paths):
    """First translation found wins inside a directory; a later source overrides earlier ones."""
    tr = {}
    for p in paths:
        files = sorted(glob.glob(os.path.join(p, "**", "*.json"), recursive=True)) if os.path.isdir(p) else [p]
        layer = {}
        for f in files:
            for k, v in json_pairs(f):
                if isinstance(k, str) and isinstance(v, str) and v and CYR.search(v):
                    # the mod's batches often carry a stray "\r"; keep it only where the key has one
                    layer.setdefault(k, v if k.endswith("\r") else v.rstrip("\r"))
                    layer.setdefault(k.strip(), v.rstrip("\r"))
        tr.update(layer)
    return tr


def translate(tr, s):
    if not s.strip() or CYR.search(s) or ID.match(s.strip()):
        return None
    return tr.get(s) or tr.get(s.strip())


def stem(w):
    w = w.lower().strip("«»\"'.,:;!?()")
    return w[:max(3, len(w) - 2)] if len(w) > 4 else w


def locate(ru_value, candidates):
    """Return (start, end_inclusive) of the best match of a candidate fragment in ru_value."""
    for c in candidates:
        if not c:
            continue
        c = c.strip()
        i = ru_value.find(c)
        if i < 0:
            i = ru_value.lower().find(c.lower())
        if i >= 0:
            return i, i + len(c) - 1
    # stem match on word sequences
    words = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", ru_value)]
    for c in candidates:
        if not c:
            continue
        cw = [stem(w) for w in c.split()]
        n = len(cw)
        for j in range(len(words) - n + 1):
            if all(stem(words[j + k][2]).startswith(cw[k][:max(3, len(cw[k]) - 1)]) or
                   cw[k].startswith(stem(words[j + k][2])) for k in range(n)):
                s, e = words[j][0], words[j + n - 1][1]
                while e > s and ru_value[e - 1] in ".,:;!?)":
                    e -= 1
                return s, e - 1
    return None


def main(in_dir, out_dir, dict_paths):
    tr = load_dicts(dict_paths)
    os.makedirs(out_dir, exist_ok=True)
    env = load(os.path.join(in_dir, "resources.assets"))
    stats = dict(objects=0, strings=0, drag_ok=0, drag_reset=0)
    report = []
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        raw = o.get_raw_data()
        if b"TextLocalized" not in raw and not re.search(rb"State \(", raw[:120]):
            pass
        try:
            t = o.read_typetree()
        except Exception:
            continue
        changed = False

        def walk(x):
            nonlocal changed
            if isinstance(x, dict):
                arr = x.get("_text")
                if isinstance(arr, list) and len(arr) > 1 and all(isinstance(s, str) for s in arr):
                    ru = translate(tr, arr[1])
                    if ru is not None and ru != arr[1]:
                        arr[1] = ru
                        changed = True
                        stats["strings"] += 1
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    if isinstance(v, (dict, list)):
                        walk(v)

        orig_value = None
        dd = t.get("_data") if isinstance(t.get("_data"), dict) else None
        if dd and "DragTextStartIndex" in dd:
            orig_value = dd["value"]["_text"][1]
            s0 = dd["DragTextStartIndex"]["_textIndex"][1]
            e0 = dd["DragTextEndIndex"]["_textIndex"][1]
            frag_en = orig_value[s0:e0 + 1] if s0 >= 0 else None
        walk(t)
        for k in PLAIN_FIELDS:
            if isinstance(t.get(k), str):
                ru = translate(tr, t[k])
                if ru is not None and ru != t[k]:
                    t[k] = ru
                    changed = True
                    stats["strings"] += 1
        if orig_value is not None and changed and frag_en is not None:
            rv = dd["value"]["_text"][1]
            if rv != orig_value:
                cands = [DRAG_FIX.get(orig_value), translate(tr, frag_en), frag_en,
                         dd["DropTextLocalized"]["_text"][1]]
                loc = locate(rv, cands)
                if loc:
                    dd["DragTextStartIndex"]["_textIndex"][1], dd["DragTextEndIndex"]["_textIndex"][1] = loc
                    stats["drag_ok"] += 1
                    report.append(f"OK   {orig_value[:50]!r} -> [{rv[loc[0]:loc[1] + 1]}]")
                else:
                    dd["DragTextStartIndex"]["_textIndex"][1] = -1
                    dd["DragTextEndIndex"]["_textIndex"][1] = -1
                    stats["drag_reset"] += 1
                    report.append(f"RESET {orig_value[:50]!r} -> {rv!r}")
        if changed:
            o.save_typetree(t)
            stats["objects"] += 1
    data = list(env.files.values())[0].save()
    open(os.path.join(out_dir, "resources.assets"), "wb").write(data)
    open(os.path.join(out_dir, "drag_report.txt"), "w", encoding="utf-8").write("\n".join(report))
    print(stats)


if __name__ == "__main__":
    srcs = sys.argv[3:] or [os.path.join(REPO, "translated"),
                            os.path.join(REPO, "translated", "batch_fix_untranslated.json")]
    main(sys.argv[1], sys.argv[2], srcs)
