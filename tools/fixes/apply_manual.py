"""Manual fixes that are not worth an automatic rule.

- Page scroll heights. A website page can only be scrolled as far as
  TabbedWindowPresenter._tabCanvasesHeight[i] (set per page in the editor for the English text),
  so a longer Russian article is cut off at the bottom. auto_page_heights() simulates the English and
  the Russian text blocks of every page and raises the height by the extra length of the Russian text
  (keeping the English bottom margin); PAGE_HEIGHTS can force a minimum for single pages.
- UI images with English text are redrawn by ui_images.py from the original textures (ORWELL_ORIG)
  and replace the Texture2D of the same name; no game artwork is stored in the repository.
- Single labels that do not fit (TEXT_EDITS: new wording / size) and rects that have to move
  (RECT_EDITS: the arrow after «Кому» on the call screen, wider session captions).
- Website names. The bookmark list shows NewBookmarkState._bookmark._captionOnlinepresence
  (resources.assets, left in English by the mod): SITE_NAMES translates the descriptive names, proper
  names of sites/brands stay in the original (except «Голос Народа» and «Национальный обозреватель»,
  which the texts of the mod use everywhere). The sites themselves (OnlinePresence._displayName and the
  logo text in level3) were translated by the mod and are only corrected where the translation is wrong
  (PRESENCE_NAMES, TEXT_EDITS): «Открыть Soteria», «Светский человек».
- Character names (PERSON_NAMES, Cosmos._persons) and document titles (DOC_NAMES, CAPTION_REPLACE).
- Ampleford is a woman (_isFemale): LINE_FIXES puts her own words into the feminine form.
- Browser history (InsiderDocument «browser.hist», level3): every row has room for as many lines as the
  English entry; a Russian entry that needs more lines gets a smaller font (fit_lines).
- Podcast subtitles (TMP with PodcastSubtitles): the box shows two lines of the English font; the Russian
  replacement fonts have taller lines, so the text gets SUBTITLE_SIZE.
- Voice-over word timings of podcasts and calls are recomputed for the Russian words (retime_vo.py).
- Bookmark list: site names and the counter use Ubuntu Medium instead of Light (MEDIUM_*).

Usage: apply_manual.py <in_dir> <out_dir> <file> [<file> ...]
(in_dir must contain globalgamemanagers.assets, the *.resS files, the font-patched sharedassets and level3;
English originals are read from ORWELL_ORIG, default <repo>/backup)
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttg import load
from apply_scenes import FontMetrics, count_lines, text_height
from retime_vo import retime
from ui_images import RENDERERS
import UnityPy
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# page GameObject name -> new height (English text ends ~120 units above the original height)
PAGE_HEIGHTS = {
    "website_peoplesvoice_crimerate": 3010.0,   # was 2735.5
    "website_beholder_school": 3520.0,          # was 3239.7
}
ORIG_DIR = os.environ.get("ORWELL_ORIG", os.path.join(REPO, "backup"))

# Cosmos person id -> name (the texts of the mod say «Эмплфорд», «группа вмешательства»)
PERSON_NAMES = {
    "CHAR_AMPLE": "Эмплфорд",
    "CHAR_INTERVENTION": "Группа вмешательства",
}
PERSON_FIELDS = ("_realName", "_displayName", "_defaultTelephoneName")

# InsiderDocument._id -> _displayName (shown in the breadcrumb); file names like «browser.hist» stay
DOC_NAMES = {"insider_rabanpc_unfinishedimage": "Площадь Свободы (СДЕЛАТЬ)"}
# exact strings replaced anywhere in the scenario states (document captions in resources.assets)
CAPTION_REPLACE = {"Площадь Свободы (TO DO)": "Площадь Свободы (СДЕЛАТЬ)",
                   "Площадь Свободы (доделать)": "Площадь Свободы (СДЕЛАТЬ)",
                   "Площадь Свободы (ДОДЕЛАТЬ)": "Площадь Свободы (СДЕЛАТЬ)"}

# resources.assets NewCommentaryLineState path_id -> [(old, new)] in _text._text[1]: Ampleford is a woman
LINE_FIXES = {
    1150: [("Я знал,", "Я знала,")],
    1190: [("я просил ", "я просила ")],
    1205: [("Видел я", "Видела я")],
    1280: [("я вам проиграл.", "я вам проиграла.")],
    1297: [("я должен", "я должна")],
    1327: [("Я бы предупредил заранее, но боялся", "Я бы предупредила заранее, но боялась")],
    1331: [("Рад, что", "Рада, что")],
    2229: [("я усвоил", "я усвоила")],
    2356: [("которую я отправил", "которую я отправила")],
    2374: [("что я просил", "что я просила")],
    2387: [("Готов поспорить", "Готова поспорить")],
    2409: [("Я обдумывал", "Я обдумывала")],
    2411: [("Я обдумывал", "Я обдумывала")],
    2414: [("Уверен, ты", "Уверена, ты")],
    2424: [("Я так и думал", "Я так и думала")],
    3539: [("я не уверен,", "я не уверена,")],
    3566: [("Уверен, вы", "Уверена, вы"), ("чтобы я смог ", "чтобы я смогла ")],
    3581: [("Я не уверен,", "Я не уверена,")],
    3585: [("разочарован", "разочарована")],
    3604: [("Не уверен,", "Не уверена,")],
    3694: [("Готов поспорить", "Готова поспорить")],
    3699: [("не ожидал", "не ожидала")],
    3703: [("чем я предполагал", "чем я предполагала")],
    3734: [("Уверен, это", "Уверена, это")],
    3760: [("как я уже говорил", "как я уже говорила")],
    3768: [("должен вас", "должна вас")],
}

SUBTITLE_SIZE = 34.0

# file -> {TMP path_id: text appended at the end (once)}: the translators in the main menu credits
# (earlier wordings of the line are replaced)
OLD_APPENDS = ("\n\n\n \r\nНад русской локализацией работали <b>esave007</b> и <b>StimDesu</b>.",)
TEXT_APPEND = {
    "level1": {1333: "\n\n\n \r\nНад русской локализацией работали <b>eSave</b> и <b>StimDesu</b>."},
}

# Bookmark list: site names and the «N сохранено» counter are Ubuntu Light, which looks too thin in
# Cyrillic next to the bold page names -> Ubuntu Medium (font asset, material) from sharedassets1.
MEDIUM_FONT = ("sharedassets1.assets", 241, 4)
MEDIUM_TMP = {"sharedassets3.assets": {3068}}  # OnlinePresenceBookmark._caption of the website list
MEDIUM_GO_NAMES = ("bookmarks_found",)         # «сохранено» next to the counter
MEDIUM_COUNTERS = ("WebsiteBookmarkPresenter", "InsiderDocumentBookmarkPresenter")
STORED_SIZE = 18.0

# file -> {TMP path_id: (accepted current texts, new text, new font size or None)}
TEXT_EDITS = {
    "sharedassets3.assets": {
        2838: (("соединение установлено",), "связь установлена", 32.0),  # call: 2nd line was cut off
    },
    "level3": {
        39316: (("Исходящая сессия",), "Исходящий сеанс", None),  # Listener: 'Session' is «Сеанс»
        38276: (("Входящая сессия",), "Входящий сеанс", None),
        39760: (("Сессия в процессе ...",), "Идёт сеанс ...", None),
        36492: (("Сессия закрыта.",), "Сеанс завершён.", None),
        # Pargesian Army home: the English slogan wraps into two centred lines inside the light box
        39951: (("Защита, Сохранение и Стойкость",), "Защита, сохранение" + chr(10) + "и стойкость", None),
        # one line on the banner like the English one
        39773: (("Горжусь тем, что служу народу Паргеса.",), "Горжусь служить народу Паргеса.", 76.0),
        # site logos
        40917: (("Открыть Soteria",), "Open Soteria", None),
        39856: (("Светский человек",), "Socialite", None),
        38226: (("Центральная медицинская база",), "Центральная медицинская база данных", 52.0),  # one line
        # Raban's desktop icon: same name as the document title («СДЕЛАТЬ» — his note to himself)
        41204: (('<link="insider_rabanpc_unfinishedimage"><#FFFFFF>Площадь Свободы (ДОДЕЛАТЬ)</color></link>\r',),
                '<link="insider_rabanpc_unfinishedimage"><#FFFFFF>Площадь Свободы (СДЕЛАТЬ)</color></link>\r', None),
        # Oleg's phone: secMsg is a messenger app name (iTrace stays as it is)
        40840: (('<link="insider_baytephone_message"><#FFFFFF>secMsg</color></link>\r',),
                '<link="insider_baytephone_message"><#FFFFFF>КриптоЧат</color></link>\r', None),
    },
    "level4": {
        978: (("готово",), "сохранено", None),  # bookmark counter, as in level3
    },
    "level1": {
        # profile list: «Параметры профиля» wrapped below the button
        1223: (("Параметры профиля",), "Профиль", None),
        1255: (("Параметры профиля",), "Профиль", None),
        1268: (("Параметры профиля",), "Профиль", None),
        1334: (("Параметры профиля",), "Профиль", None),
        # profile options: one line next to the delete icon (the full text would need ~30 instead of 38)
        1212: (("Удалить профиль",), "Удалить", None),
        # «ЗАГРУЗИТЬ ЭПИЗОД» fits the button in one line at 33 (fit_to_space had made it 24.7)
        1269: (("Загрузить эпизод",), "Загрузить эпизод", 33.0),
        1331: (("Загрузить эпизод",), "Загрузить эпизод", 33.0),
    },
}

# file -> {GameObject path_id: {"x": anchored x, "w": width}}
RECT_EDITS = {
    "sharedassets3.assets": {
        856: {"x": 1152.0},  # icon_phone_to: after «КОМУ» (was after «TO»)
        923: {"x": 72.0},    # icon_phone_from: after «ОТ» (was after «FROM»)
    },
    "level3": {
        7236: {"w": 700.0},  # txt_outgoingsession, free bar up to the date
        5006: {"w": 700.0},  # txt_incomingsession
    },
    "level1": {
        53: {"x": 1760.0},   # «НАЗАД» ran over the right edge of the button: closer to the arrow
        264: {"x": 1760.0},
        # credits: the scroll content ends right after the text (9943 = 1480 + 8457 for the English text,
        # 1480 + 8673 with the translators line); the text rect gets its real height, otherwise the
        # runtime fix sees a Cyrillic text overflowing its 56-unit rect and shrinks the whole credits
        290: {"h": 10160.0},
        397: {"h": 8720.0},
    },
}

# OnlinePresence id -> OnlinePresence._displayName (level3), only where the mod's name is wrong
PRESENCE_NAMES = {
    "website_karenssite": "Open Soteria",
    "website_socialite": "Socialite",
    "website_medical": "Центральная медицинская база данных",
    "website_pvadmin": "«Голос Народа» — панель управления",
}

# OnlinePresence id -> site name in the bookmark list
SITE_NAMES = {
    "website_album": "Hologram",
    "website_aptitudetest": "Тест на пригодность",
    "website_bank2": "SmartBank24",
    "website_beholder": "Национальный обозреватель",
    "website_blabber": "Blabber",
    "website_campaign": "Кампания Элизабет Левин",
    "website_cards": "Фан-клуб Hand of Blood",
    "website_government": "Правительство Нации — Управление",
    "website_immigration": "Национальная иммиграционная база данных",
    "website_karenssite": "Open Soteria",
    "website_leaks": "Percoleaks",
    "website_medical": "Центральная медицинская база данных",
    "website_pargesianarmy": "Паргесская армия",
    "website_party": "Партия",
    "website_peoplesvoice": "Голос Народа",
    "website_police": "Полицейская база данных Бонтона",
    "website_prava": "Город Права",
    "website_pvadmin": "«Голос Народа» — панель управления",
    "website_school": "Средняя школа",
    "website_single": "Singular",
    "website_social": "Реабилитационный совет",
    "website_socialite": "Socialite",
    "website_timelines": "Timelines",
    "website_vhart": "Инициатива «Спасём Паргес»",
    "website_watergate": "Watergate Pharmaceuticals",
}


def mono_class(o, scripts):
    fid, pid = struct.unpack_from("<iq", o.get_raw_data(), 16)
    return scripts.get(pid)


def replace_strings(t, table):
    """Replace exact string values anywhere in a typetree. Returns the number of replacements."""
    n = 0
    items = t.items() if isinstance(t, dict) else enumerate(t) if isinstance(t, list) else ()
    for k, v in list(items):
        if isinstance(v, str) and v in table:
            t[k] = table[v]
            n += 1
        elif isinstance(v, (dict, list)):
            n += replace_strings(v, table)
    return n


def english_originals(path, scripts):
    """From the original game file: TMP path_id -> (text, font size), page GameObject -> scroll height.
    All size decisions are based on these, so running the script again changes nothing."""
    texts, heights = {}, {}
    if os.path.exists(path):
        env = load(path)
        objs = {o.path_id: o for o in env.objects}
        for o in env.objects:
            if o.type.name != "MonoBehaviour":
                continue
            cls = mono_class(o, scripts)
            if cls in ("TextMeshProUGUI", "TextMeshPro"):
                t = o.read_typetree()
                texts[o.path_id] = (t.get("m_text"), t["m_fontSize"])
            elif cls == "TabbedWindowPresenter":
                t = o.read_typetree()
                for c, h in zip(t.get("_tabCanvases") or [], t.get("_tabCanvasesHeight") or []):
                    rt = objs.get(c["m_PathID"])
                    if rt is not None:
                        heights[rt.read_typetree()["m_GameObject"]["m_PathID"]] = h
    return texts, heights


def fit_lines(t, width, english, font):
    """Font size at which the Russian text needs no more lines than the English one had at its size
    (never larger than the English size, not below 60% of it). Returns True if the size changed."""
    ru_text = t.get("m_text") or ""
    if not english or not english[0] or not font or not t.get("m_enableWordWrapping") or width <= 10:
        return False
    en_text, en_size = english
    en_lines = count_lines(en_text, en_size, font, width, t)  # as the English text was laid out
    width *= 0.94  # the wrap simulation is a bit optimistic (see apply_scenes.fit_to_space)
    target = en_size
    if count_lines(ru_text, en_size, font, width, t) > en_lines:
        lo, hi = en_size * 0.6, en_size
        for _ in range(12):
            mid = (lo + hi) / 2
            if count_lines(ru_text, mid, font, width, t) <= en_lines:
                lo = mid
            else:
                hi = mid
        target = round(lo, 2)
    if abs(t["m_fontSize"] - target) < 0.01:
        return False
    t["m_fontSize"] = t["m_fontSizeBase"] = target
    return True

def auto_page_heights(env, objs, scripts, rt_of, parent_go, english, en_heights, metrics, externals, f):
    """page GameObject -> height needed for the Russian text (only pages that need more)."""
    gos = {o.path_id: o.read_typetree() for o in env.objects if o.type.name == "GameObject"}
    pages = {}
    for o in env.objects:
        if o.type.name == "MonoBehaviour" and mono_class(o, scripts) == "TabbedWindowPresenter":
            t = o.read_typetree()
            for c, h in zip(t.get("_tabCanvases") or [], t.get("_tabCanvasesHeight") or []):
                rt = objs.get(c["m_PathID"])
                if rt is not None:
                    pages[rt.read_typetree()["m_GameObject"]["m_PathID"]] = h
    top_left = lambda rt: rt["m_AnchorMin"] == rt["m_AnchorMax"] == {"x": 0.0, "y": 1.0}
    bottom_en, bottom_ru = {}, {}
    for o in env.objects:
        if o.type.name != "MonoBehaviour" or o.path_id not in english:
            continue
        if mono_class(o, scripts) not in ("TextMeshProUGUI", "TextMeshPro"):
            continue
        t = o.read_typetree()
        g = t["m_GameObject"]["m_PathID"]
        (en, en_size), ru = english[o.path_id], t.get("m_text") or ""
        if not en or en == ru or not t.get("m_enableWordWrapping") or t.get("m_enableAutoSizing"):
            continue
        # walk up to the page: every level must be a hand-placed top-left block and active
        y, cur, ok = 0.0, g, True
        while cur is not None and cur not in pages:
            rt = rt_of.get(cur)
            if rt is None or not top_left(rt) or not gos.get(cur, {}).get("m_IsActive", 1):
                ok = False
                break
            y += rt["m_AnchoredPosition"]["y"] + ((1 - rt["m_Pivot"]["y"]) * rt["m_SizeDelta"]["y"] if cur == g else 0)
            cur = parent_go.get(cur)
        if not ok or cur is None:
            continue
        fa = t["m_fontAsset"]
        font = metrics.get(f if fa["m_FileID"] == 0 else externals[fa["m_FileID"] - 1], fa["m_PathID"])
        if not font:
            continue
        margin = t.get("m_margin", {})
        width = rt_of[g]["m_SizeDelta"]["x"] - margin.get("x", 0) - margin.get("z", 0)
        if width <= 10:
            continue
        top = -y
        bottom_en[cur] = max(bottom_en.get(cur, 0), top + text_height(en, en_size, font, width, t)[1])
        bottom_ru[cur] = max(bottom_ru.get(cur, 0), top + text_height(ru, t["m_fontSize"], font, width * 0.94, t)[1])
    need = {}
    for page, h in pages.items():
        h = en_heights.get(page, h)  # the height made for the English text
        if page in bottom_ru and bottom_ru[page] > bottom_en.get(page, 0):
            margin = max(60.0, h - bottom_en.get(page, h))
            want = round(bottom_ru[page] + margin)
            if want > h + 60:  # ignore noise of the simulation
                need[page] = want
    return need


def original_textures(path):
    """Texture2D name -> image from the original game file, for the textures redrawn by ui_images.py."""
    out = {}
    if os.path.exists(path):
        for o in UnityPy.load(path).objects:
            if o.type.name == "Texture2D":
                tex = o.read()
                if tex.m_Name in RENDERERS:
                    out[tex.m_Name] = tex.image
    return out


def voice_texts(in_dir, scripts):
    """voice-over id -> (english text, russian text, is podcast)"""
    out = {}
    cur = load(os.path.join(in_dir, "resources.assets"))
    org = {o.path_id: o for o in load(os.path.join(ORIG_DIR, "resources.assets")).objects}
    for o in cur.objects:
        if o.type.name == "MonoBehaviour" and mono_class(o, scripts) == "NewChatMessageState":
            t = o.read_typetree()
            vid = t.get("_voiceOverIdFull")
            if vid and o.path_id in org:
                en = org[o.path_id].read_typetree()["_text"]["_text"][1]
                out.setdefault(vid, (en, t["_text"]["_text"][1], False))
    cur = load(os.path.join(in_dir, "level3"))
    org = {o.path_id: o for o in load(os.path.join(ORIG_DIR, "level3")).objects}
    for o in cur.objects:
        if o.type.name == "MonoBehaviour" and mono_class(o, scripts) == "PodcastTranscript":
            t = o.read_typetree()
            if o.path_id in org:
                out.setdefault(t["PodcastId"], (org[o.path_id].read_typetree()["Text"], t["Text"], True))
    return out


def main(in_dir, out_dir, files):
    os.makedirs(out_dir, exist_ok=True)
    gg = UnityPy.load(os.path.join(in_dir, "globalgamemanagers.assets"))
    scripts = {o.path_id: o.read_typetree()["m_ClassName"] for o in gg.objects if o.type.name == "MonoScript"}
    metrics = FontMetrics(in_dir)
    for f in files:
        env = load(os.path.join(in_dir, f))
        sf = list(env.files.values())[0]
        externals = [e.path.split("/")[-1] for e in sf.externals]
        objs = {o.path_id: o for o in env.objects}
        n = dict(heights=0, images=0, texts=0, rects=0, sites=0, persons=0, docs=0, lines=0, history=0,
                 subtitles=0, timings=0)
        texts = TEXT_EDITS.get(f, {})
        rects = RECT_EDITS.get(f, {})

        # layout (GameObject -> RectTransform, parent) for the browser history and subtitle passes
        rt_of, parent_go, rt_go = {}, {}, {}
        for o in env.objects:
            if o.type.name == "RectTransform":
                rt = o.read_typetree()
                rt_of[rt["m_GameObject"]["m_PathID"]] = rt
                rt_go[o.path_id] = rt["m_GameObject"]["m_PathID"]
        for g, rt in rt_of.items():
            parent_go[g] = rt_go.get(rt["m_Father"]["m_PathID"])
        history_docs, subtitle_gos = set(), set()
        medium_tmp = set(MEDIUM_TMP.get(f, ()))
        medium_file_id = 1 + externals.index(MEDIUM_FONT[0]) if MEDIUM_FONT[0] in externals else None
        for o in env.objects:
            if o.type.name == "MonoBehaviour":
                cls = mono_class(o, scripts)
                if cls == "InsiderDocument":
                    t = o.read_typetree()
                    if t.get("_displayName") == "browser.hist":
                        history_docs.add(t["m_GameObject"]["m_PathID"])
                elif cls == "PodcastSubtitles":
                    subtitle_gos.add(o.read_typetree()["m_GameObject"]["m_PathID"])
                elif cls in MEDIUM_COUNTERS:
                    ref = o.read_typetree().get("_bookmarkCounterText")
                    if ref and ref["m_FileID"] == 0:
                        medium_tmp.add(ref["m_PathID"])

        def in_history(g):
            for _ in range(4):
                g = parent_go.get(g)
                if g is None:
                    return False
                if g in history_docs:
                    return True
            return False

        originals = original_textures(os.path.join(ORIG_DIR, f))
        english, en_heights = english_originals(os.path.join(ORIG_DIR, f), scripts)             if f.startswith("level") else ({}, {})
        page_need = auto_page_heights(env, objs, scripts, rt_of, parent_go, english, en_heights, metrics,
                                      externals, f) if english else {}
        voices = voice_texts(in_dir, scripts) if f == "resources.assets" else {}

        for o in env.objects:
            if o.type.name == "RectTransform":
                rt = o.read_typetree()
                edit = rects.get(rt["m_GameObject"]["m_PathID"])
                if edit:
                    if "x" in edit:
                        rt["m_AnchoredPosition"]["x"] = edit["x"]
                    if "w" in edit:
                        rt["m_SizeDelta"]["x"] = edit["w"]
                    if "h" in edit:
                        rt["m_SizeDelta"]["y"] = edit["h"]
                    o.save_typetree(rt)
                    n["rects"] += 1
            elif o.type.name == "Texture2D":
                tex = o.read()
                if tex.m_Name in RENDERERS and tex.m_Name in originals:
                    img = RENDERERS[tex.m_Name](originals[tex.m_Name])
                    assert img.size == (tex.m_Width, tex.m_Height), tex.m_Name
                    fmt = int(tex.m_TextureFormat)  # 3 = RGB24, 4 = RGBA32
                    tex.set_image(img.convert("RGB" if fmt == 3 else "RGBA"), target_format=fmt)
                    tex.save()
                    n["images"] += 1
            if o.type.name != "MonoBehaviour":
                continue
            cls = mono_class(o, scripts)
            if cls in ("TextMeshProUGUI", "TextMeshPro"):
                t = o.read_typetree()
                g = t["m_GameObject"]["m_PathID"]
                changed = False
                if o.path_id in texts:
                    accepted, new, size = texts[o.path_id]
                    if t["m_text"] not in accepted + (new,):
                        print(f, "SKIP text", o.path_id, repr(t["m_text"]))
                    else:
                        t["m_text"] = new
                        if size:
                            t["m_fontSize"] = t["m_fontSizeBase"] = size
                        changed = True
                        n["texts"] += 1
                go_name = objs[g].read_typetree()["m_Name"] if g in objs else ""
                if medium_file_id and (o.path_id in medium_tmp or go_name in MEDIUM_GO_NAMES):
                    if t["m_fontAsset"] != {"m_FileID": medium_file_id, "m_PathID": MEDIUM_FONT[1]}:
                        t["m_fontAsset"] = {"m_FileID": medium_file_id, "m_PathID": MEDIUM_FONT[1]}
                        t["m_sharedMaterial"] = {"m_FileID": medium_file_id, "m_PathID": MEDIUM_FONT[2]}
                        changed = True
                        n["fonts"] = n.get("fonts", 0) + 1
                    if go_name in MEDIUM_GO_NAMES and t["m_fontSize"] != STORED_SIZE:
                        t["m_fontSize"] = t["m_fontSizeBase"] = STORED_SIZE  # «СОХРАНЕНО» in its 118-wide rect
                        changed = True
                suffix = TEXT_APPEND.get(f, {}).get(o.path_id)
                if suffix and not (t.get("m_text") or "").endswith(suffix):
                    base = t.get("m_text") or ""
                    for old_suffix in OLD_APPENDS:
                        if base.endswith(old_suffix):
                            base = base[:-len(old_suffix)]
                    t["m_text"] = base + suffix
                    changed = True
                    n["texts"] += 1
                if g in subtitle_gos and t["m_fontSize"] > SUBTITLE_SIZE:
                    t["m_fontSize"] = t["m_fontSizeBase"] = SUBTITLE_SIZE
                    changed = True
                    n["subtitles"] += 1
                if g in rt_of and in_history(g):
                    fa = t["m_fontAsset"]
                    font_file = f if fa["m_FileID"] == 0 else externals[fa["m_FileID"] - 1]
                    margin = t.get("m_margin", {})
                    width = rt_of[g]["m_SizeDelta"]["x"] - margin.get("x", 0) - margin.get("z", 0)
                    if fit_lines(t, width, english.get(o.path_id), metrics.get(font_file, fa["m_PathID"])):
                        changed = True
                        n["history"] += 1
                if changed:
                    o.save_typetree(t)
            elif cls == "OnlinePresence":
                t = o.read_typetree()
                name = PRESENCE_NAMES.get(t.get("_id"))
                if name and t.get("_displayName") != name:
                    t["_displayName"] = name
                    o.save_typetree(t)
                    n["sites"] += 1
            elif cls == "NewBookmarkState":
                t = o.read_typetree()
                b = t["_bookmark"]
                name = SITE_NAMES.get(b.get("_parentId"))
                if name and b.get("_captionOnlinepresence") != name:
                    b["_captionOnlinepresence"] = name
                    o.save_typetree(t)
                    n["sites"] += 1
            elif cls == "Cosmos":
                t = o.read_typetree()
                changed = False
                for p in t["_persons"]["_Values"]:
                    name = PERSON_NAMES.get(p.get("_id"))
                    for field in PERSON_FIELDS if name else ():
                        if p.get(field) and p[field] != name:
                            p[field] = name
                            changed = True
                if changed:
                    o.save_typetree(t)
                    n["persons"] += 1
            elif cls == "InsiderDocument":
                t = o.read_typetree()
                name = DOC_NAMES.get(t.get("_id"))
                if name and t.get("_displayName") != name:
                    t["_displayName"] = name
                    o.save_typetree(t)
                    n["docs"] += 1
            elif cls == "InsiderDocumentUpdateState":
                t = o.read_typetree()
                if replace_strings(t, CAPTION_REPLACE):
                    o.save_typetree(t)
                    n["docs"] += 1
            elif cls == "NewCommentaryLineState" and f == "resources.assets" and o.path_id in LINE_FIXES:
                t = o.read_typetree()
                txt = t["_text"]["_text"][1]
                for old, new in LINE_FIXES[o.path_id]:
                    if new in txt:  # already fixed ("разочарован" is a part of "разочарована")
                        continue
                    if old in txt:
                        txt = txt.replace(old, new, 1)
                    else:
                        print(f, "SKIP line", o.path_id, repr(old))
                if txt != t["_text"]["_text"][1]:
                    t["_text"]["_text"][1] = txt
                    o.save_typetree(t)
                    n["lines"] += 1
            elif cls == "VoiceOverTimingsCollectionObject":
                t = o.read_typetree()
                d = t["_timings"]
                # the English tables from the original file (the current ones may be retimed already)
                org = load(os.path.join(ORIG_DIR, f)).objects
                en_tables = next(dict(zip(x.read_typetree()["_timings"]["_Keys"],
                                          (v["_values"] for v in x.read_typetree()["_timings"]["_Values"])))
                                 for x in org if x.path_id == o.path_id)
                for key, val in zip(d["_Keys"], d["_Values"]):
                    if key not in voices or key not in en_tables:
                        continue
                    en, ru, podcast = voices[key]
                    new = retime(en, ru, en_tables[key], podcast)
                    if new is not None and new != val["_values"]:
                        val["_values"] = new
                        n["timings"] += 1
                if n["timings"]:
                    o.save_typetree(t)
            elif cls == "TabbedWindowPresenter":
                t = o.read_typetree()
                hs = t.get("_tabCanvasesHeight") or []
                changed = False
                for i, c in enumerate(t.get("_tabCanvases") or []):
                    rt = objs.get(c["m_PathID"])
                    if rt is None or i >= len(hs):
                        continue
                    page = rt.read_typetree()["m_GameObject"]["m_PathID"]
                    name = objs[page].read_typetree()["m_Name"]
                    want = max(PAGE_HEIGHTS.get(name, 0), page_need.get(page, 0))
                    if hs[i] < want:
                        print(f, "page height", name, round(hs[i]), "->", want)
                        hs[i] = want
                        changed = True
                        n["heights"] += 1
                if changed:
                    o.save_typetree(t)
        data = list(env.files.values())[0].save()
        open(os.path.join(out_dir, f), "wb").write(data)
        print(f, ", ".join(f"{k} {v}" for k, v in n.items() if v) or "no changes", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
