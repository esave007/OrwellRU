"""Translate leftover English UI text in scene files (TMP m_text) and the episode names
(_flowLevelNames, must match the strings the RU mod put into Assembly-CSharp.dll).

Also shrinks single-word labels that do not fit their rect (TMP breaks them mid-word).
Font metrics are read from <fonts_dir> (default <in_dir>), i.e. the already font-patched assets.

Russian texts longer than the English original use the free space below them; only if that is not
enough they get a smaller font (english text is read from the original game files in ORWELL_ORIG,
default <repo>/backup).

Usage: apply_scenes.py <in_dir> <out_dir> <file> [<file> ...]   (env ORWELL_FONTS_DIR = fonts_dir)
"""
import os, re, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttg import load
from apply_loc import load_dicts, translate
import UnityPy

sys.stdout.reconfigure(encoding="utf-8")
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

EPISODES = {  # identical to translated/dll_strings.json
    "Episode One: Thesis": "Эпизод первый: Тезис",
    "Episode Two: Antithesis": "Эпизод второй: Антитезис",
    "Episode Three: Synthesis": "Эпизод третий: Синтез",
}

# NB: never translate dates/times in TMP labels: DateTool parses its label with DateTime.Parse
# and FileImportTools.AddTimeStamps searches timestamps in texts (the day flow breaks otherwise).
TMP_TEXT = {
    "CC": "Копия",
    "To": "Кому",
    "To\r": "Куда\r",  # only used in Ilya's e-ticket (From/To = route)
    "stored": "сохранено",  # bookmarks counter "12 STORED"
    "on": "вкл",
    "off": "выкл",
    "mobile": "мобильный",
    "No\r": "Нет\r",
    "Hi\r": "Привет\r",
    "Active": "Активно",
    "Inactive": "Неактивно",
    "Episode One": "Эпизод первый",
    "Episode Two": "Эпизод второй",
    "Episode Three": "Эпизод третий",
    "Play Podcast:\r\nTHIS IS MY LAST ANNOUNCEMENT\r": "Воспроизвести подкаст:\r\nЭТО МОЁ ПОСЛЕДНЕЕ ОБЪЯВЛЕНИЕ\r",
    "Play Podcast: I AM NOT AFRAID OF YOU AND I WILL NOT GO AWAY\r": "Воспроизвести подкаст: Я ВАС НЕ БОЮСЬ И НИКУДА НЕ УЙДУ\r",
    "Play Podcast: \r\nThe Government of The Nation IS LYING TO YOU\r": "Воспроизвести подкаст: \r\nПравительство Нации ВАМ ЛЖЁТ\r",
    "Play Podcast: The Government of The Nation IS LYING TO YOU\r": "Воспроизвести подкаст: Правительство Нации ВАМ ЛЖЁТ\r",
}
TMP_CLASSES = ("TextMeshProUGUI", "TextMeshPro")
SINGLE_WORD = re.compile(r"[А-ЯЁа-яё][А-ЯЁа-яё\-]*[.!?…:]?")
TAG = re.compile(r"<[^>]+>")
# toolbar tabs "–– Прослушка ––": the decorative dashes make the Russian words wrap into 3 lines
DASHED_LABEL = re.compile(r"^[–—]{2}\s*([^–—\r\n]{1,40}?)\s*[–—]{2}$")


class FontMetrics:
    """Glyph advances of the TMP font assets referenced from a scene (read from the patched files)."""

    def __init__(self, fonts_dir):
        self.dir = fonts_dir
        self.envs = {}
        self.cache = {}

    def get(self, file_name, pid):
        key = (file_name, pid)
        if key not in self.cache:
            info = None
            path = os.path.join(self.dir, file_name)
            if os.path.exists(path):
                if file_name not in self.envs:
                    self.envs[file_name] = {o.path_id: o for o in load(path).objects}
                o = self.envs[file_name].get(pid)
                t = o.read_typetree() if o is not None and o.type.name == "MonoBehaviour" else {}
                if "m_glyphInfoList" in t:
                    fi = t["m_fontInfo"]
                    info = (fi["PointSize"], {g["id"]: g["xAdvance"] for g in t["m_glyphInfoList"]},
                            t.get("boldSpacing", 0.0), fi["Ascender"], fi["Descender"], fi["LineHeight"])
            self.cache[key] = info
        return self.cache[key]


# "13 отметок «Нравится»" (English "13 Likes") is three times longer than the box: "13 лайков"
LIKES = re.compile(r"(?:(\d+)\s+отмет\w*|Отметки)\s+«Нравится»:?")


def likes_ru(n):
    """13 -> "13 лайков", 33 -> "33 лайка", 21 -> "21 лайк"."""
    n = int(n)
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} лайк"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f"{n} лайка"
    return f"{n} лайков"


LINE_BREAK = re.compile(r"\r\n|\r|\n|<br>")


def count_lines(text, size, font, width, t):
    """Greedy word wrap as TMP does it, measured with the font asset's glyph advances."""
    pt, adv, bold_spacing = font[:3]
    scale = size / pt
    extra = t.get("m_characterSpacing", 0.0) + (bold_spacing if t.get("m_fontStyle", 0) & 1 else 0.0)
    if t.get("m_fontStyle", 0) & (16 | 32):
        text = text.upper()
    space = (adv.get(32, pt * 0.25) + extra) * scale
    text = text.strip("\r\n ")
    lines = 0
    for para in LINE_BREAK.split(TAG.sub(lambda m: "\n" if m.group(0) == "<br>" else "", text)):
        lines += 1
        x = 0.0
        for word in para.split(" "):
            w = sum((adv.get(ord(c), pt * 0.55) + extra) * scale for c in word)
            if x > 0 and x + space + w <= width:
                x += space + w
                continue
            if x > 0:
                lines += 1
            while w > width:  # TMP breaks words longer than the line
                lines += 1
                w -= width
            x = w
    return lines


class Layout:
    """Absolute layout of a scene: rects of GameObjects grouped by parent (the websites/documents are
    hand-placed blocks with top-left anchors)."""

    def __init__(self, env, scripts):
        self.rect = {}      # go -> (RectTransform object, tree)
        self.children = {}  # parent RectTransform pid -> [go]
        self.go = {}        # go -> GameObject tree
        self.objs = {}
        for o in env.objects:
            self.objs[o.path_id] = o
            if o.type.name == "RectTransform":
                rt = o.read_typetree()
                g = rt["m_GameObject"]["m_PathID"]
                self.rect[g] = (o, rt)
                self.children.setdefault(rt["m_Father"]["m_PathID"], []).append(g)
            elif o.type.name == "GameObject":
                self.go[o.path_id] = o.read_typetree()
        self.scripts = scripts

    def box(self, g):
        rt = self.rect[g][1]
        if rt["m_AnchorMin"] != rt["m_AnchorMax"]:
            return None
        w, h = rt["m_SizeDelta"]["x"], rt["m_SizeDelta"]["y"]
        left = rt["m_AnchoredPosition"]["x"] - rt["m_Pivot"]["x"] * w
        top = rt["m_AnchoredPosition"]["y"] + (1 - rt["m_Pivot"]["y"]) * h
        return left, top, left + w, top - h

    def is_background(self, g):
        for c in self.go[g]["m_Component"]:
            o = self.objs.get(c["component"]["m_PathID"])
            if o is not None and o.type.name == "MonoBehaviour":
                fid, pid = struct.unpack_from("<iq", o.get_raw_data(), 16)
                if self.scripts.get(pid) in TMP_CLASSES:
                    return False
        return True

    def free_height(self, g):
        """Height available below the top of g: up to the next active sibling below it (overlapping
        horizontally), or to the bottom of a background panel g sits on. None = nothing below."""
        me = self.box(g)
        if me is None:
            return None
        rt = self.rect[g][1]
        l0, t0, r0, b0 = me
        limit = None
        for s in self.children.get(rt["m_Father"]["m_PathID"], []):
            if s == g or s not in self.go or not self.go[s].get("m_IsActive", 1):
                continue
            if self.go[s]["m_Name"].startswith("chunk box") or self.rect[s][1]["m_AnchorMin"] != rt["m_AnchorMin"]:
                continue
            b = self.box(s)
            if b is None or b[2] - b[0] < 2 or b[1] - b[3] < 2:
                continue
            l, t, r, bot = b
            if min(r, r0) - max(l, l0) < 20:
                continue
            if t < t0 - 2:
                room = t0 - t - 16
            elif bot < t0 - 5 and l <= l0 + 5 and r >= r0 - 5 and self.is_background(s):
                room = t0 - bot - 35  # keep a bottom padding inside the panel
            else:
                continue
            if room > 0 and (limit is None or room < limit):
                limit = room
        return limit


READABLE_SIZE = 34.0


def text_height(text, size, font, width, t):
    pt, asc, desc, lh = font[0], font[3], font[4], font[5]
    n = count_lines(text, size, font, width, t)
    return n, (asc - desc + (n - 1) * (lh + t.get("m_lineSpacing", 0.0))) * size / pt


def fit_to_space(t, g, en_text, layout, metrics, ext):
    """The scenes were laid out for the English text. A longer Russian text may use the free space
    below it (up to the next block / the end of its background panel); only if even that is not
    enough the font gets smaller (paragraphs not below 80%). The rect is stretched over the space
    used, so the runtime fix does not shrink it again. Returns (font_changed, rect_changed)."""
    ru_text = t.get("m_text") or ""
    if (not en_text or en_text == ru_text or not re.search("[А-Яа-яЁё]", ru_text)
            or "<size" in ru_text or not t.get("m_enableWordWrapping") or t.get("m_enableAutoSizing")):
        return False, False
    if g not in layout.rect or layout.box(g) is None:
        return False, False
    robj, rect = layout.rect[g]
    fa = t["m_fontAsset"]
    file_name = ext(fa["m_FileID"])
    font = metrics.get(file_name, fa["m_PathID"]) if file_name else None
    if not font:
        return False, False
    margin = t.get("m_margin", {})
    # the wrap simulation is a bit optimistic (no kerning, TMP rounding): measure on 94% of the width
    width = (rect["m_SizeDelta"]["x"] - margin.get("x", 0) - margin.get("z", 0)) * 0.94
    if width <= 10:
        return False, False
    size = t["m_fontSize"]
    en_lines, en_h = text_height(en_text, size, font, width, t)
    free = layout.free_height(g)
    if free is None:
        budget = float("inf")
    else:
        budget = free if free >= en_h * 0.6 else en_h  # odd geometry: fall back to the English height
    ru_lines, ru_h = text_height(ru_text, size, font, width, t)
    new = size
    if ru_h > budget:
        # long paragraphs stay readable (>= 80%); headings and short blocks may shrink more
        lo = size * (0.8 if ru_lines >= 5 else 0.65)
        hi = size
        for _ in range(10):
            mid = (lo + hi) / 2
            if text_height(ru_text, mid, font, width, t)[1] <= budget:
                lo = mid
            else:
                hi = mid
        new = round(lo, 2)
        t["m_fontSize"] = t["m_fontSizeBase"] = new
    elif size < READABLE_SIZE and ru_lines >= 2:
        # websites are drawn ~2x smaller than their 2000-unit canvas: body text below ~34 units is
        # hard to read; make it bigger where the free space below allows it
        lo, hi = size, min(READABLE_SIZE, size * 1.3)
        if text_height(ru_text, hi, font, width, t)[1] > budget:
            for _ in range(10):
                mid = (lo + hi) / 2
                if text_height(ru_text, mid, font, width, t)[1] <= budget:
                    lo = mid
                else:
                    hi = mid
            hi = lo
        if hi > size + 0.5:
            new = round(hi, 2)
            t["m_fontSize"] = t["m_fontSizeBase"] = new
    need = text_height(ru_text, new, font, width, t)[1] + new * 0.3
    if free is not None:
        need = min(need, budget)
    h = rect["m_SizeDelta"]["y"]
    if need <= h + 1:
        return new != size, False
    top = rect["m_AnchoredPosition"]["y"] + (1 - rect["m_Pivot"]["y"]) * h
    rect["m_SizeDelta"]["y"] = need
    rect["m_AnchoredPosition"]["y"] = top - (1 - rect["m_Pivot"]["y"]) * need
    robj.save_typetree(rect)
    return new != size, True


def shrink_to_fit(t, rect, metrics, ext):
    """Single-word labels wider than their rect get broken mid-word by TMP ("СКРЫ / ТЬ"):
    reduce the font size so the word fits on one line. Returns True if changed."""
    text = TAG.sub("", t.get("m_text") or "").strip()
    if not SINGLE_WORD.fullmatch(text) or not t.get("m_enableWordWrapping") or t.get("m_enableAutoSizing"):
        return False
    if rect is None or rect["m_AnchorMin"]["x"] != rect["m_AnchorMax"]["x"]:
        return False  # stretched rect: width depends on the parent, skip
    fa = t["m_fontAsset"]
    file_name = ext(fa["m_FileID"])
    m = metrics.get(file_name, fa["m_PathID"]) if file_name else None
    if not m:
        return False
    pt, adv, bold_spacing = m[:3]
    size = t["m_fontSize"]
    style = t.get("m_fontStyle", 0)
    if style & (16 | 32):  # UpperCase / SmallCaps render capitals
        text = text.upper()
    width = sum(adv.get(ord(c), pt * 0.6) for c in text) * size / pt
    width += (len(text) - 1) * t.get("m_characterSpacing", 0.0) * size / 100.0
    if style & 1:  # bold
        width *= 1 + bold_spacing / 100.0
    margin = t.get("m_margin", {"x": 0, "z": 0})
    avail = rect["m_SizeDelta"]["x"] - margin.get("x", 0) - margin.get("z", 0)
    if avail <= 0 or width <= avail:
        return False
    new = max(size * 0.55, size * avail / width * 0.96)
    t["m_fontSize"] = t["m_fontSizeBase"] = round(new, 2)
    return True


def main(in_dir, out_dir, files):
    os.makedirs(out_dir, exist_ok=True)
    gg = UnityPy.load(os.path.join(in_dir, "globalgamemanagers.assets"))
    scripts = {o.path_id: o.read_typetree()["m_ClassName"] for o in gg.objects if o.type.name == "MonoScript"}
    metrics = FontMetrics(os.environ.get("ORWELL_FONTS_DIR", in_dir))
    captions = load_dicts([os.path.join(REPO, "translated"),
                           os.path.join(REPO, "translated", "batch_fix_untranslated.json")])
    for f in files:
        env = load(os.path.join(in_dir, f))
        sf = list(env.files.values())[0]
        externals = [e.path.split("/")[-1] for e in sf.externals]

        def ext(file_id):
            return f if file_id == 0 else externals[file_id - 1]

        english = {}
        orig_path = os.path.join(os.environ.get("ORWELL_ORIG", os.path.join(REPO, "backup")), f)
        if os.path.exists(orig_path):
            for o in load(orig_path).objects:
                if o.type.name == "MonoBehaviour":
                    raw = o.get_raw_data()
                    fid, pid = struct.unpack_from("<iq", raw, 16)
                    if scripts.get(pid) in TMP_CLASSES:
                        english[o.path_id] = o.read_typetree().get("m_text")
        layout = Layout(env, scripts)
        n_tmp = n_ep = n_fit = n_height = n_cap = n_rect = 0
        for o in env.objects:
            if o.type.name != "MonoBehaviour":
                continue
            raw = o.get_raw_data()
            fid, pid = struct.unpack_from("<iq", raw, 16)
            cls = scripts.get(pid)
            if cls in TMP_CLASSES:
                t = o.read_typetree()
                changed = False
                ru = TMP_TEXT.get(t.get("m_text"))
                if ru is None and t.get("m_text") and LIKES.search(t["m_text"]):
                    ru = LIKES.sub(lambda m: likes_ru(m.group(1)) if m.group(1) else "Нравится:", t["m_text"])
                if ru is None and t.get("m_text"):
                    m = DASHED_LABEL.match(t["m_text"].strip())
                    if m and re.search("[А-Яа-яЁё]", m.group(1)):
                        ru = m.group(1)
                if ru:
                    t["m_text"] = ru
                    changed = True
                    n_tmp += 1
                g = t["m_GameObject"]["m_PathID"]
                rect = layout.rect[g][1] if g in layout.rect else None
                font_changed, rect_changed = fit_to_space(t, g, english.get(o.path_id), layout, metrics, ext)
                n_rect += rect_changed
                if font_changed:
                    changed = True
                    n_height += 1
                if shrink_to_fit(t, rect, metrics, ext):
                    changed = True
                    n_fit += 1
                if changed:
                    o.save_typetree(t)
            elif cls == "Website":
                # page captions shown in the bookmarks / address bar; the key is the separate _id
                t = o.read_typetree()
                ru = translate(captions, t.get("_displayName") or "")
                if ru:
                    t["_displayName"] = ru
                    o.save_typetree(t)
                    n_cap += 1
            elif b"_flowLevelNames" in raw or b"Episode One: Thesis" in raw:
                t = o.read_typetree()
                names = t.get("_flowLevelNames")
                if not names:
                    continue
                vals = names["_Values"]
                for i, v in enumerate(vals):
                    if v in EPISODES:
                        vals[i] = EPISODES[v]
                        n_ep += 1
                o.save_typetree(t)
        data = list(env.files.values())[0].save()
        open(os.path.join(out_dir, f), "wb").write(data)
        print(f, "tmp texts", n_tmp, "episode names", n_ep, "shrunk labels", n_fit, "shrunk to free space", n_height, "rects stretched", n_rect, "page captions", n_cap, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
