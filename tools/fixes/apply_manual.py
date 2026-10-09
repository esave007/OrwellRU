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
- Bookmark list: site names and the counter keep the game's Ubuntu Light (FONT_FROM_ORIGINAL restores it
  where an earlier version of this script had put Ubuntu Medium); «сохранено» gets STORED_SIZE.
- TEXT_REPLACE: phrases replaced inside Russian texts (TMP texts and podcast transcripts).
- Timelines profiles, «… нравится» tiles: the light plate under each caption was cut to the English word
  (bg_like_text_N). interest_tiles() sets the caption to one or two centred lines (as large as the English
  40 allows, at most TILE_MAX_W wide) and puts the plate and the text rect around it.
- Like counters «Нравится: 13» (made by apply_scenes from the mod's «13 отметок «Нравится»») -> «13 лайков».
- DEBRIEF_EDITS: end-of-day summary (NewDebriefingElementState in resources.assets): untranslated entries and
  sentences where a name placeholder ({CHAR_…} is replaced by the name in the nominative) broke the grammar.

Usage: apply_manual.py <in_dir> <out_dir> <file> [<file> ...]
(in_dir must contain globalgamemanagers.assets, the *.resS files, the font-patched sharedassets and level3;
English originals are read from ORWELL_ORIG, default <repo>/backup)
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttg import load
import re
from apply_scenes import FontMetrics, count_lines, text_height, likes_ru
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

# resources.assets NewDebriefingElementState path_id -> {field: new value}
DEBRIEF_EDITS = {
    1510: {"_text": "Наш агент {CHAR_BAYTE} пропал. Незадолго до исчезновения он говорил по телефону, и запись "
                    "этого звонка попала в онлайн-газету «Национальный обозреватель». Его собеседник — "
                    "{CHAR_RABAN}. Управление решило вмешаться и с помощью Orwell найти пропавшего агента."},
    1495: {"_globalHeadlineText": "Вмешательство",
           "_text": "Когда мы установили, где находится {CHAR_BAYTE}, мы отправили группу вмешательства. "
                    "Он был обнаружен в руинах Правской средней школы."},
    1493: {"_text": "Казалось, его обрадовало, что {CHAR_BAYTE} исчез."},
    1509: {"_text": "Казалось, его расстроило, что {CHAR_BAYTE} исчез."},
    1494: {"_text": "Он иммигрировал в Нацию вместе со своим братом — {CHAR_ILYA}."},
    1500: {"_text": "Он, вероятно, причастен к нападению на школу, которой руководил {CHAR_RABAN}."},
    1501: {"_text": "По результатам расследования мы заключили, что он не мог быть причастен к нападению на "
                    "школу, которой руководил {CHAR_RABAN}."},
    1504: {"_text": "По его словам, в нападении на школу, директором которой он был, виновен {CHAR_BAYTE}."},
}

# file -> {TMP path_id: text appended at the end (once)}: the translators in the main menu credits
# (earlier wordings of the line are replaced)
OLD_APPENDS = ("\n\n\n \r\nНад русской локализацией работали <b>esave007</b> и <b>StimDesu</b>.",)
TEXT_APPEND = {
    "level1": {1333: "\n\n\n \r\nНад русской локализацией работали <b>eSave</b> и <b>StimDesu</b>."},
}

# Bookmark list: site names and the «N сохранено» counter are Ubuntu Light, which looks too thin in
# Cyrillic next to the bold page names -> Ubuntu Medium (font asset, material) from sharedassets1.
# Bookmark list texts that get the font asset / material of the original file back (the game uses the
# thin Ubuntu Light there; v0.6.0 had switched them to Ubuntu Medium)
FONT_FROM_ORIGINAL_TMP = {"sharedassets3.assets": {3068}}  # OnlinePresenceBookmark._caption (site names)
FONT_FROM_ORIGINAL_GO_NAMES = ("bookmarks_found",)         # «сохранено» next to the counter
FONT_FROM_ORIGINAL_COUNTERS = ("WebsiteBookmarkPresenter", "InsiderDocumentBookmarkPresenter")
STORED_SIZE = 19.1  # «сохранено» in Light fits its 118-wide rect at this size (the mod's value)

# phrases inside Russian texts: the mod left the newspaper name in English in a few places
TEXT_REPLACE = [
    ("под названием The National Beholder", "под названием «Национальный обозреватель»"),
    ("с коррупцией The National Beholder", "с коррупцией «Национального обозревателя»"),
    ("www.the-national-beholder.tna - The National Beholder - ",
     "www.the-national-beholder.tna - «Национальный обозреватель» - "),
    # TNB: the mod writes «НО:» before the newspaper's questions in interviews (and in the ticker)
    ("в стиле привычной нам подачи ТНО", "в стиле привычной нам подачи «Национального обозревателя»"),
    ("Ни слова от TNB о последнем СКАНДАЛЕ", "«Обозреватель» молчит о последнем СКАНДАЛЕ"),
    ("Куча последователей TNB", "Куча поклонников «Национального обозревателя»"),
    ("TNB: Что именно", "НО: Что именно"),
    ("TNB: Миссис Левин", "НО: Миссис Левин"),
    ("TNB: Итак, чем", "НО: Итак, чем"),
    # Karen's calendar: the appointments ran out of their cells (four lines instead of three)
    ("Сеанс с пациентом — София Радич", "Сеанс: София Радич"),
    ("Сеанс пациента Алексея Ковачи", "Сеанс: Алексей Ковачи"),
    ("Сеанс пациента Ильи Вхарта", "Сеанс: Илья Вхарт"),
    # Singular chat: Ilya answers Mary
    ("Ты прав. Раньше всё было ради благородства.", "Ты права. Раньше всё было ради благородства."),
    # Rita Grayham and Ana Milova are women
    ("Очень хотел бы к вам присоединиться", "Очень хотела бы к вам присоединиться"),
    ("Согласен, и говорю это как гражданин Паргеса.", "Согласна, и говорю это как гражданка Паргеса."),
    # «… MEDIA LAMBS»: the article and its link say «МЕДИА-ЯГНЯТ», one link said «МЕДИА-ОВЕЦ»
    ("МОЛЧАНИЕ правительственных МЕДИА-ОВЕЦ", "МОЛЧАНИЕ правительственных МЕДИА-ЯГНЯТ"),
    ("#BestCoworkersEver", "#ЛучшиеКоллегиНаСвете"),
    # Karen's album: she writes it
    ("Никогда бы тогда не угадал, что нас ждёт.", "Никогда бы тогда не угадала, что нас ждёт."),
    # Penn St Apartments: one name, Russian like in the addresses
    ("Управляющий жилого комплекса Пенн-стрит", "Управляющий жилым комплексом «Пенн-стрит»"),
    ("Спасибо за аренду в Penn St Apartments.", "Спасибо, что арендуете жильё в комплексе «Пенн-стрит»."),
    # Watergate intranet: the company keeps its Latin name (like everywhere else); Matt is a name
    ("последнее, чего хотят Уотергейты — это чтобы", "последнее, что нужно Watergate, — это чтобы"),
    ("но мэтт уволит нас обоих", "но Мэтт уволит нас обоих"),
    # the company is Watergate (the family keeps «Уотергейт», the «скандал «Уотергейт»» pun stays)
    ("произошло в «Уотергейт».", "произошло в Watergate."),
    ("@PeoplesVoice В «Уотергейт» ведётся", "@PeoplesVoice В Watergate ведётся"),
    # The People's Voice (TPV): the hashtag had four spellings -> #ГНЛжецыИВоры (ГН = «Голос Народа», like НО
    # for the National Beholder); in sentences the name itself
    ("#TPVareLiarsAndThieves", "#ГНЛжецыИВоры"),
    ("#TPVЛжецыИВоры", "#ГНЛжецыИВоры"),
    ("#ГНС_лжецыИворы", "#ГНЛжецыИВоры"),
    ("#ПрощайTPV", "#ПрощайГН"),
    ("что TPV отстаивает мои ценности", "что «Голос Народа» отстаивает мои ценности"),
    ("редактора TPV.", "редактора «Голоса Народа»."),
    ("Теперь понятно, как TPV финансируется.", "Теперь понятно, как финансируется «Голос Народа»."),
    ("что касается TPV,", "что касается «Голоса Народа»,"),
    ("ИЗБАВИТЬСЯ ОТ НЕГО И TPV!", "ИЗБАВИТЬСЯ ОТ НЕГО И «ГОЛОСА НАРОДА»!"),
    ("если бы ты не вышвырнул меня из TPV,", "если бы ты не вышвырнул меня из «Голоса Народа»,"),
    # Blabber hashtags the mod left in English (the mod's own Russian ones: #КоррупцияСМИ, #НациональныйЛжец)
    ("#SaveKarenAndIlya", "#СпаситеКаренИИлью"),
    ("#LiarsGetLiedTo", "#ЛжецамВрут"),
    ("#LiarsGetLeftBehind", "#ЛжецовБросают"),
    ("#ThePeoplesSilencing", "#МолчаниеНарода"),
    ("#CowardBrother", "#БратТрус"),
    ("#TraitorOfThePeople", "#ПредательНарода"),
    ("#SaveBakay", "#СпаситеБакая"),
    ("#SAVEPARGES", "#СПАСЁМПАРГЕС"),
    ("#saveparges", "#спасёмпаргес"),
    ("#TRIFLITHRIOTS", "#БУНТЫВТРИФЛИТЕ"),
    ("#BlameOnVhart", "#ВиноватВхарт"),
    ("#BlameOnRaban", "#ВиноватРабан"),
    ("#MediaCorruption", "#КоррупцияСМИ"),
    ("#LiesLiesLies", "#ЛожьЛожьЛожь"),
    ("#TheNationalLiar", "#НациональныйЛжец"),
    ("#TRUTH", "#ПРАВДА"),
    ("#FakeMarriage", "#ФиктивныйБрак"),
    ("#PargesianHero", "#ГеройПаргеса"),
    ("#refugee", "#беженец"),
    # mail subject: too long for the mail list row (also MAIL_SUBJECTS and the Mail objects in level3)
    ("Подпишитесь на Singular Pro уже сегодня!", "Оформите Singular Pro сегодня!"),
]

# Blabber display names (the @handles stay as they are); keys: the English name and the mod's variants
BLABBER_NAMES = {
    "PeoplesVoice": "Голос Народа",
    "Not your average weirdo": "Не простой чудак", "Не обычный чудак": "Не простой чудак",
    "Backp0int": "Бэкп0инт",
    "Raging Ralf": "Бешеный Ральф",
    "B. Leaver": "Б. Ливер",
    "Moonrise Hell": "Лунный Ад",
    "Liam Love": "Лиам Лав",
    "Brain Stu": "Брейн Стю",
    "Kanzto": "Канзто",
    "Tyler Durden": "Тайлер Дёрден",
    "FightBack999": "ДайОтпор999",
    "Jon Doe": "Джон Доу",
    "Единственный выживший в Трифлите": "Единственный выживший из Трифлита",
    "Beequeen": "Пчелиная Королева",
    "Terence H": "Теренс Х",
    "Resist The Gov": "Против Власти",
    "Henriette_K": "Генриетта_К",
    "Guacamole": "Гуакамоле",
}
BLABBER_NAME = re.compile(r"(?<![\w@])(" + "|".join(sorted(map(re.escape, BLABBER_NAMES), key=len, reverse=True)) +
                          r")(?=\s*\(?@)")
BLABBER_COUNTER = re.compile(r"^[\d,]+ (re-blabbers|replies|votes)\s*$")

# resources.assets NewMailState path_id -> (accepted subjects, new subject): too long for the mail list row
MAIL_SUBJECTS = {2662: (("Подпишитесь на Singular Pro уже сегодня!",), "Оформите Singular Pro сегодня!")}

# Watergate intranet
WATERGATE_DATE_SIZE = 41.8     # message list: the dates like the subjects next to them
WATERGATE_BUTTON_SIZE = 50.0   # «Ваш профиль» / «Ваши сообщения» (36 in a 67 high box)
# chats laid out block under block (see restack_messages): the Watergate intranet and the phones' messengers
MESSAGE_PAGES = ("website_watergate_ilyamessage", "insider_karensphone_messagehistory", "insider_ilyasphone_message",
                 "insider_baytephone_message")

# resources.assets UpdateProfileState path_id -> (English value, Russian value): dossier values the mod missed
PROFILE_VALUES = {
    1638: ("deceased", "скончался"),
    4363: ("deceased", "скончалась"),
    2892: ("athletic", "спортивного телосложения"),
    2896: ("heterosexual", "гетеросексуал"),
    2903: ("single", "холост"),
    2904: ("unreliable", "ненадёжный работник"),  # the opposite of «надёжный работник»
    4334: ("optimistic", "оптимист"),
}

# SmartBank account page: «13 апреля 2017 г.» wrapped into two/three lines in the narrow date column
BANK_DATE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December) "
                       r"(\d{1,2}), (\d{4})\s*$")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
BANK_DATE_SIZE = 33.5
# the transaction column: one size for every row (the mod's texts had 34..40), boxes as wide as the widest
BANK_TEXT_SIZE = 36.0
BANK_TEXT_WIDTH = 702.0

# Website._displayName (the page title in the address bar)
PAGE_TITLES = {"Молчание ПРАВИТЕЛЬСТВЕННЫХ ОВЕЦ": "Молчание ПРАВИТЕЛЬСТВЕННЫХ МЕДИА-ЯГНЯТ"}

# resources.assets UpdateProfileState path_id -> (value, drop text, drag start, drag end): dossier entries
# that did not fit their two-line field
PROFILE_EDITS = {
    # Karen, occupation (refugee counselor at Rehabilitation Council)
    2960: ("консультант по беженцам в Реабилитационном совете", "консультант по беженцам", 0, 22),
}

LIKES_LABEL = re.compile(r"^Нравится: (\d+)(\s*)$")

# Timelines «… нравится» tiles
TILE_MAX_W = 300.0     # caption width (the pictures are ~370 wide)
TILE_PAD = 34.0        # plate = caption + this (the English plates: 32..37)
TILE_MIN_ONE_LINE = 32.0  # a one-line caption smaller than this is set in two lines
TILE_DROP = 0.1        # the centred text sits high on the plate: moved down by this × size / lines
TILE_ONE_LINE_GROW = 6.0  # one-line plates grow upwards by this (room for «Й»)
TILE_LINE_SPACING = -20.0  # two-line captions: lines closer together


def replace_phrases(text):
    for old, new in TEXT_REPLACE:
        text = text.replace(old, new)
    return text


# resources.assets NewChatMessageState path_id -> (mod text, new text): single chat lines too short for TEXT_REPLACE
CHAT_EDITS = {
    2041: ("НОЛЬ", "НИ МАЛЕЙШЕГО"),  # «You have NO IDEA what it's like» / «ZERO»
    2063: ("Ты прав.", "Ты права."),  # Karen answers Molly
}


def chat_text(pid, text):
    old, new = CHAT_EDITS.get(pid, (None, None))
    return replace_phrases(new if text == old else text)

# file -> {TMP path_id: (accepted current texts, new text, new font size or None)}
TEXT_EDITS = {
    "sharedassets3.assets": {
        2838: (("соединение установлено",), "связь установлена", 32.0),  # call: 2nd line was cut off
        # profile update tooltip: «ОТКЛЮЧИТЬ»/«ВКЛЮЧИТЬ» ran into the icon after them
        3205: (("Отключить",), "Отключить", 30.0),
        3252: (("Отключить",), "Отключить", 30.0),
        3355: (("Включить",), "Включить", 30.0),
        # conflict tooltip: «ПОКАЗАТЬ КОНФЛИКТ» ran out of its button; the picture button says «КОНФЛИКТ ▸»
        # (same size and place as on the picture, RECT_EDITS)
        3244: (("ПОКАЗАТЬ КОНФЛИКТ", "КОНФЛИКТ"), "КОНФЛИКТ", 34.0),
        3363: (("ПОКАЗАТЬ КОНФЛИКТ", "КОНФЛИКТ"), "КОНФЛИКТ", 34.0),
        # connections graph: the selected person's name, «Левин-Вхарт» did not fit and broke at the hyphen
        2486: (("Mary Bligh",), "Mary Bligh", 27.0),
        2720: (("Karen Levine-Vhart",), "Karen Levine-Vhart", 27.0),
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
        # end-of-day summary: «ГЛАВНОЕ МЕНЮ» in one line on its button
        36483: (("Главное меню",), "Главное меню", 42.0),
        # Karen's Timelines status in one line (the second line went under the header)
        36099: (("Статус: «Всем не помочь, но каждый может помочь кому-то».\r", "Статус: «Мы не можем помочь каждому, но каждый может помочь кому-то».\r"), "Статус: «Мы не можем помочь каждому, но каждый может помочь кому-то».\r", 49.0),
        36186: (("Статус: «Всем не помочь, но каждый может помочь кому-то».\r", "Статус: «Мы не можем помочь каждому, но каждый может помочь кому-то».\r"), "Статус: «Мы не можем помочь каждому, но каждый может помочь кому-то».\r", 49.0),
        37637: (("Статус: «Всем не помочь, но каждый может помочь кому-то».\r", "Статус: «Мы не можем помочь каждому, но каждый может помочь кому-то».\r"), "Статус: «Мы не можем помочь каждому, но каждый может помочь кому-то».\r", 49.0),
        39769: (("Статус: «Всем не помочь, но каждый может помочь кому-то».\r", "Статус: «Мы не можем помочь каждому, но каждый может помочь кому-то».\r"), "Статус: «Мы не можем помочь каждому, но каждый может помочь кому-то».\r", 49.0),
        # Karen's site: Diane is «Диана» in the letters and the sidebar
        35863: (("Дайан Коулман",), "Диана Коулман", None),
        36749: (("Дайан Коулман",), "Диана Коулман", None),
        # Karen's site: «Назад к входящим» ran into the arrow (text moved right of it, RECT_EDITS)
        38354: (("Назад к входящим",), "Назад к входящим", 36.0),
        39651: (("Назад к входящим",), "Назад к входящим", 36.0),
        40812: (("Назад к входящим",), "Назад к входящим", 36.0),
        41038: (("Назад к входящим",), "Назад к входящим", 36.0),
        # Karen's calendar: «CW 15» is the calendar week
        36144: (("КН\r\n15\r",), "Нед.\r\n15\r", None),
        # Singular questionnaire: answers that fit the questions
        40336: (("Кот\r\nСобака\r\nНикого\r\nНе люблю животных",),
                "Кошек\r\nСобак\r\nНи тех, ни других\r\nНе люблю животных", None),
        38090: (("... левая рука.\r\n... правая рука.\r\nЧто это за вопрос?!",),
                "... на левую руку.\r\n... на правую руку.\r\nЧто это за вопрос?!", None),
        # Blabber: the profile name and the slogan (shrunk to 22 in its box: the box grows, the size of the
        # English text)
        40297: (("PeoplesVoice",), "Голос Народа", None),
        37993: (("Blabber. Говори, что думаешь.\r",), "Blabber. Говори, что думаешь.\r", 30.0),
        # Blabber: followers / following (the mod had «Прослушка», i.e. wiretapping)
        36238: (("Прослушка",), "Слушатели", None),
        38995: (("Прослушка",), "Слушатели", None),
        39870: (("Прослушивание", "Слушает"), "Слушает", 42.4),  # the same size as «Слушатели»
        # Hologram (an Instagram parody) keeps its name, like in the bookmark list
        35894: (("Голограмма",), "Hologram", None),
        # patient database: the hint ran out of its box
        36389: (("Введите полное имя пациента или номер социального страхования.\r",),
                "Введите полное имя пациента или номер соцстрахования.\r", 34.0),
        40352: (("Введите полное имя пациента или номер социального страхования.\r",),
                "Введите полное имя пациента или номер соцстрахования.\r", 34.0),
        # Hologram: search hint in one line
        41260: (("Введите название места или адрес для поиска по вашему альбому.\r",),
                "Введите название места или адрес для поиска по альбому.\r", None),
        # Karen's album: the place under the photo in one line (the city is named after the comma)
        39041: (("Внешний приёмный лагерь Бонтона, Бонтон",), "Внешний приёмный лагерь, Бонтон", None),
        # SmartBank: two lines at the common size (BANK_TEXT_SIZE)
        38023: (("Национальный транспорт Бонтона — Ваш месячный проездной на апрель 2017 г.",),
                "Национальный транспорт Бонтона — проездной на апрель 2017 г.", None),
        # weather photo caption in one line (the second line ran below the picture)
        38566: (("Надвигаются тяжёлые дождевые тучи! Фото: stock-overflow.tna\r",),
                "Надвигаются грозовые тучи! Фото: stock-overflow.tna\r", 37.0),
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
        # «Отключить» / «Включить» buttons (260 wide, LAYOUT_EDITS): text and icon spaced out
        1177: {"x": -24.0}, 1167: {"x": -24.0}, 1166: {"x": -24.0},
        1109: {"x": 95.0}, 1207: {"x": 95.0}, 1205: {"x": 95.0},
        1232: {"x": 137.0}, 1135: {"x": 137.0},  # «КОНФЛИКТ» where the picture button has it
        1136: {"x": 154.0}, 1226: {"x": 154.0},  # and its arrow
    },
    "level3": {
        7236: {"w": 700.0},  # txt_outgoingsession, free bar up to the date
        5006: {"w": 700.0},  # txt_incomingsession
        # end-of-day summary: «◂ ГЛАВНОЕ МЕНЮ» moves left, the end of the text was under the slanted edge
        1330: {"x": 447.0, "w": 340.0},  # txt_mainmenu_over
        2777: {"x": 400.0},              # its arrow
        # Singular profile of Ilya: labels on the baseline of their values, values in two columns after the
        # longest label («Телосложение:», «Препараты:» at 36)
        8249: {"y": -2224.0, "w": 280.0, "h": 61.0}, 6384: {"y": -2314.7, "w": 280.0, "h": 61.0},
        5092: {"y": -2398.9, "w": 280.0, "h": 61.0},
        5771: {"y": -2224.9, "w": 220.0, "h": 61.0}, 10719: {"x": 1235.0, "y": -2317.2, "w": 220.0, "h": 61.0},
        9073: {"y": -2407.4, "w": 220.0, "h": 61.0},
        8368: {"x": 845.0, "w": 370.0}, 10344: {"x": 845.0, "w": 370.0}, 7158: {"x": 845.0, "w": 370.0},
        4994: {"x": 1461.0, "w": 369.0}, 6954: {"x": 1461.0, "w": 369.0}, 7666: {"x": 1461.0, "w": 369.0},
        # Karen's site: «Назад к входящим» between the arrow and the right edge of the button
        5153: {"x": 335.0, "w": 345.0}, 7931: {"x": 335.0, "w": 345.0},
        10494: {"x": 335.0, "w": 345.0}, 11012: {"x": 335.0, "w": 345.0},
        # Karen's site: the sender under the picture broke inside «Паттисон,» / «Коулман,» (to the letter text)
        406: {"w": 195.0}, 483: {"w": 195.0}, 1563: {"w": 195.0}, 4599: {"w": 195.0}, 5338: {"w": 195.0},
        # rehabilitation council (logged in): the two-line logo ran into «О нас» below it
        7244: {"y": -43.0},
        # SmartBank slogan in one line: the box grows to the left
        6585: {"x": 971.0, "w": 760.0},
        # Ampleford's remarks / objectives: a 4th Russian line ran into «ПРОДОЛЖИТЬ». The text keeps three
        # lines of room (a longer one gets a smaller font from the runtime fix), the button moves down a bit
        11231: {"h": 178.0},  # comment text
        2321: {"h": 178.0},   # objective text
        6671: {"x": 2370.0, "y": -505.0},  # continue text (its end touched the arrow)
        8921: {"y": -496.0},  # continue arrow
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

# file -> {GameObject path_id: {layout field: value}}: fields of the LayoutElement / LayoutGroup on it
LAYOUT_EDITS = {
    "sharedassets3.assets": {
        # «Отключить» / «Включить» buttons in the profile update tooltip: 220 -> 260 wide, growing to the
        # left (row padding 317 -> 277), so the right edge stays where it was
        1186: {"m_PreferredWidth": 260.0}, 1206: {"m_PreferredWidth": 260.0}, 1138: {"m_PreferredWidth": 260.0},
        1188: {"m_Padding.m_Left": 277}, 1228: {"m_Padding.m_Left": 277}, 1116: {"m_Padding.m_Left": 277},
    },
}

# file -> {TMP path_id: font size} whatever the text is
SIZE_EDITS = {
    "level3": {
        # Singular profile of Ilya: labels (the mod had 27..46) and values (44..46)
        39799: 36.0, 38940: 36.0, 38324: 36.0, 38655: 36.0, 40912: 36.0, 40169: 36.0,
        39857: 39.0, 40736: 39.0, 39283: 39.0, 38270: 39.0, 39199: 39.0, 39526: 39.0,
    },
}

# OnlinePresence id -> OnlinePresence._displayName (level3), only where the mod's name is wrong
PRESENCE_NAMES = {
    "website_karenssite": "Open Soteria",
    "website_socialite": "Socialite",
    "website_album": "Hologram",
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
    """From the original game file: TMP path_id -> (text, font size), page GameObject -> scroll height,
    TMP path_id -> (font asset, material).
    All size decisions are based on these, so running the script again changes nothing."""
    texts, heights, fonts = {}, {}, {}
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
                fonts[o.path_id] = (t["m_fontAsset"], t["m_sharedMaterial"])
            elif cls == "TabbedWindowPresenter":
                t = o.read_typetree()
                for c, h in zip(t.get("_tabCanvases") or [], t.get("_tabCanvasesHeight") or []):
                    rt = objs.get(c["m_PathID"])
                    if rt is not None:
                        heights[rt.read_typetree()["m_GameObject"]["m_PathID"]] = h
    return texts, heights, fonts


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


def tile_layout(env, objs, scripts, metrics, externals, f):
    """Timelines «… нравится» tiles. Returns ({GameObject: rect edit}, {TMP path_id: (text, size)}).
    Plates and English captions are taken from the original file, so the result does not depend on an
    earlier run."""
    org = {o.path_id: o for o in load(os.path.join(ORIG_DIR, f)).objects}
    names = {o.path_id: o.read_typetree()["m_Name"] for o in env.objects if o.type.name == "GameObject"}
    rect = lambda r: (r["m_AnchoredPosition"]["x"], r["m_AnchoredPosition"]["y"], r["m_SizeDelta"]["x"],
                      r["m_SizeDelta"]["y"])
    rt_go, children, tmp_of = {}, {}, {}
    for o in env.objects:
        if o.type.name == "RectTransform" and o.path_id in org:
            r = org[o.path_id].read_typetree()
            rt_go[o.path_id] = r["m_GameObject"]["m_PathID"]
            children[r["m_GameObject"]["m_PathID"]] = r
        elif o.type.name == "MonoBehaviour" and mono_class(o, scripts) == "TextMeshProUGUI":
            tmp_of[o.read_typetree()["m_GameObject"]["m_PathID"]] = o
    rect_edits, text_edits = {}, {}
    for g, name in names.items():
        if not name.startswith("bg_like_text") or g not in children:
            continue
        px, py, pw, ph = rect(children[g])
        parent = children.get(rt_go.get(children[g]["m_Father"]["m_PathID"]))
        caption = None
        for c in parent["m_Children"] if parent else ():
            cg = rt_go.get(c["m_PathID"])
            if cg in tmp_of:
                x, y, w, h = rect(children[cg])
                if x <= px + pw / 2 <= x + w and -50 < y - py < 0 and abs(x + w / 2 - (px + pw / 2)) < 20:
                    caption = cg
        if caption is None:
            continue
        o = tmp_of[caption]
        t = o.read_typetree()
        en = org[o.path_id].read_typetree()
        fa = t["m_fontAsset"]
        font = metrics.get(f if fa["m_FileID"] == 0 else externals[fa["m_FileID"] - 1], fa["m_PathID"])
        if not font or not re.search("[А-Яа-яЁё]", t["m_text"] or ""):
            continue
        pt, adv, asc, desc, lh = font[0], font[1], font[3], font[4], font[5]
        en_size = en["m_fontSize"]
        width = lambda s, size: max(sum(adv.get(ord(ch), pt * 0.55) for ch in line) for line in s.split("\n")) * size / pt
        height = lambda n, size: (asc - desc + (n - 1) * lh) * size / pt
        ru = re.sub(r"\s*\n\s*", "\n", (t["m_text"] or "").replace("\r", "").strip())
        one = ru.replace("\n", " ")
        two = ru if "\n" in ru else None
        if two is None:  # break at the space / hyphen that gives the shortest lines
            cuts = [i + 1 if one[i] == "-" else i for i in range(1, len(one) - 1) if one[i] in " -"]
            if cuts:
                i = min(cuts, key=lambda i: width(one[:i].strip() + "\n" + one[i:].strip(), en_size))
                two = one[:i].strip() + "\n" + one[i:].strip()
        fit = lambda s, n: min(en_size, en_size * TILE_MAX_W / width(s, en_size),
                               en_size * (ph if n == 2 and ph > 80 else 100.0) / height(n, en_size))
        lines_en = 2 if ph > 80 else 1
        if lines_en == 1:
            text, n = (one, 1) if two is None or fit(one, 1) >= TILE_MIN_ONE_LINE else (two, 2)
        else:
            text, n = (two, 2) if two else (one, 1)
        size = round(fit(text, n) if n == 2 else min(fit(text, 1), en_size), 2)
        w = round(width(text, size) + TILE_PAD)
        if n == lines_en:
            y, h = py, ph
            if n == 1:
                y, h = y + TILE_ONE_LINE_GROW, h + TILE_ONE_LINE_GROW
        elif n == 2:   # a one-line plate grows upwards to the two-line height of the neighbours
            y, h = py + 57.0, ph + 57.0
        else:
            y, h = py - 57.0 + TILE_ONE_LINE_GROW, ph - 57.0 + TILE_ONE_LINE_GROW
        x = round(px + pw / 2 - w / 2, 1)
        rect_edits[g] = {"x": x, "y": y, "w": w, "h": h}
        rect_edits[caption] = {"x": x, "y": round(y - TILE_DROP * size / n, 2), "w": w, "h": h}
        text_edits[o.path_id] = (text, size, TILE_LINE_SPACING if n == 2 else en["m_lineSpacing"])
    return rect_edits, text_edits


def restack_messages(env, objs, scripts, metrics, externals, f, english):
    """Chat pages (MESSAGE_PAGES) are laid out block under block for the English text; the scenes pass shrank
    Russian messages that needed a line more (sizes 42..55 in one chat), or the text ran out of its bubble.
    Here every text on a message background (bg_message*) gets its English size back and needs as many lines
    as it does: everything below moves down by the extra height, a background grows by the extra height of
    the texts on it, the page by the total. Positions come from the original file.
    Returns ({GameObject: rect edit}, {TMP path_id: size}, {page GameObject: extra height})."""
    org = {o.path_id: o for o in load(os.path.join(ORIG_DIR, f)).objects}
    rect_of, kids, name = {}, {}, {}
    for o in env.objects:
        if o.type.name == "RectTransform" and o.path_id in org:
            r = org[o.path_id].read_typetree()
            rect_of[r["m_GameObject"]["m_PathID"]] = r
        elif o.type.name == "GameObject":
            name[o.path_id] = o.read_typetree()["m_Name"]
    rt_go = {o.path_id: o.read_typetree()["m_GameObject"]["m_PathID"] for o in env.objects
             if o.type.name == "RectTransform" and o.path_id in org}
    tmp_of = {}
    for o in env.objects:
        if o.type.name == "MonoBehaviour" and mono_class(o, scripts) == "TextMeshProUGUI":
            tmp_of[o.read_typetree()["m_GameObject"]["m_PathID"]] = o
    rect_edits, sizes, extra = {}, {}, {}
    for page, page_name in name.items():
        if not page_name.startswith(MESSAGE_PAGES) or page not in rect_of:
            continue
        children = [rt_go[c["m_PathID"]] for c in rect_of[page]["m_Children"] if c["m_PathID"] in rt_go]
        backgrounds = [g for g in children if name.get(g, "").startswith("bg_message")]
        if not backgrounds:
            continue
        top = max(rect_of[g]["m_AnchoredPosition"]["y"] for g in backgrounds)
        y_of = lambda g: rect_of[g]["m_AnchoredPosition"]["y"]
        x_of = lambda g: rect_of[g]["m_AnchoredPosition"]["x"]
        h_of = lambda g: rect_of[g]["m_SizeDelta"]["y"]
        on_bg = lambda g: any(x_of(b) <= x_of(g) <= x_of(b) + rect_of[b]["m_SizeDelta"]["x"] and
                              y_of(b) - h_of(b) < y_of(g) <= y_of(b) for b in backgrounds)
        grow = {}
        for g in children:
            if g in backgrounds or y_of(g) > top or g not in tmp_of or not on_bg(g):
                continue
            o = tmp_of[g]
            t = o.read_typetree()
            en_text, en_size = english.get(o.path_id, (None, None))
            if not en_text:
                continue
            fa = t["m_fontAsset"]
            font = metrics.get(f if fa["m_FileID"] == 0 else externals[fa["m_FileID"] - 1], fa["m_PathID"])
            if not font:
                continue
            width = rect_of[g]["m_SizeDelta"]["x"]
            h_en = text_height(en_text, en_size, font, width, t)[1]
            h_ru = text_height(t["m_text"] or "", en_size, font, width * 0.94, t)[1]
            sizes[o.path_id] = en_size
            grow[g] = max(0.0, round(h_ru - h_en, 1))
        total = sum(grow.values())
        if not total:
            continue
        for g in children:
            if y_of(g) > top:
                continue
            shift = sum(d for g2, d in grow.items() if y_of(g2) > y_of(g))
            inside = (sum(d for g2, d in grow.items() if y_of(g) - h_of(g) < y_of(g2) <= y_of(g))
                      if g in backgrounds else grow.get(g, 0))
            edit = {}
            if shift:
                edit["y"] = round(y_of(g) - shift, 1)
            if inside:
                edit["h"] = round(h_of(g) + inside, 1)
            rect_edits[g] = edit
        extra[page] = total
    return rect_edits, sizes, extra


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
                out.setdefault(vid, (en, chat_text(o.path_id, t["_text"]["_text"][1]), False))
    cur = load(os.path.join(in_dir, "level3"))
    org = {o.path_id: o for o in load(os.path.join(ORIG_DIR, "level3")).objects}
    for o in cur.objects:
        if o.type.name == "MonoBehaviour" and mono_class(o, scripts) == "PodcastTranscript":
            t = o.read_typetree()
            if o.path_id in org:
                out.setdefault(t["PodcastId"], (org[o.path_id].read_typetree()["Text"], replace_phrases(t["Text"]), True))
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
        rects = dict(RECT_EDITS.get(f, {}))

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
        restore_tmp = set(FONT_FROM_ORIGINAL_TMP.get(f, ()))
        for o in env.objects:
            if o.type.name == "MonoBehaviour":
                cls = mono_class(o, scripts)
                if cls == "InsiderDocument":
                    t = o.read_typetree()
                    if t.get("_displayName") == "browser.hist":
                        history_docs.add(t["m_GameObject"]["m_PathID"])
                elif cls == "PodcastSubtitles":
                    subtitle_gos.add(o.read_typetree()["m_GameObject"]["m_PathID"])
                elif cls in FONT_FROM_ORIGINAL_COUNTERS:
                    ref = o.read_typetree().get("_bookmarkCounterText")
                    if ref and ref["m_FileID"] == 0:
                        restore_tmp.add(ref["m_PathID"])

        def in_history(g):
            for _ in range(4):
                g = parent_go.get(g)
                if g is None:
                    return False
                if g in history_docs:
                    return True
            return False

        def site_of(g):
            """name of the website page the GameObject is on ("" if none)"""
            for _ in range(6):
                g = parent_go.get(g)
                if g is None or g not in objs:
                    return ""
                name = objs[g].read_typetree()["m_Name"]
                if name.startswith("website_"):
                    return name
            return ""

        def in_bank(g):
            return site_of(g).startswith("website_bank")

        bank_texts = set()
        if f.startswith("level"):
            for o in env.objects:
                if o.type.name == "MonoBehaviour" and mono_class(o, scripts) == "TextMeshProUGUI":
                    g = o.read_typetree()["m_GameObject"]["m_PathID"]
                    rt = rt_of.get(g)
                    if (rt and 525 < rt["m_AnchoredPosition"]["x"] < 540 and rt["m_AnchoredPosition"]["y"] < -1300
                            and in_bank(g)):
                        bank_texts.add(o.path_id)
                        rects[g] = dict(rects.get(g, {}), w=BANK_TEXT_WIDTH)

        originals = original_textures(os.path.join(ORIG_DIR, f))
        english, en_heights, orig_fonts = english_originals(os.path.join(ORIG_DIR, f), scripts)
        if not f.startswith("level"):
            english, en_heights = {}, {}
        # Blabber: the counters «N переблаблов / ответов / голосов» in one line; the follower numbers right
        # after their (shorter or longer) Russian labels, with the English gap
        blabber_fit, slogan = {}, {}
        if f == "level3":
            org_rt = {}
            for o in load(os.path.join(ORIG_DIR, f)).objects:
                if o.type.name == "RectTransform":
                    r = o.read_typetree()
                    org_rt[r["m_GameObject"]["m_PathID"]] = r
            labels, numbers = [], []
            for o in env.objects:
                if o.type.name != "MonoBehaviour" or mono_class(o, scripts) != "TextMeshProUGUI":
                    continue
                t = o.read_typetree()
                g = t["m_GameObject"]["m_PathID"]
                en = (english.get(o.path_id) or ("",))[0] or ""
                if en.strip() in ("Listeners", "Listening to") or re.match(r"^[\d,]+\s*$", en):
                    if site_of(g).startswith("website_blabber") and g in org_rt:
                        (labels if not en.strip()[0].isdigit() else numbers).append((o, t, g, en))
                if BLABBER_COUNTER.match(en) and g in rt_of and site_of(g).startswith("website_blabber"):
                    blabber_fit[o.path_id] = rt_of[g]["m_SizeDelta"]["x"]
                if en == "Blabber. Speak your mind.\r" and g in org_rt:
                    r = org_rt[g]
                    slogan[g] = {"x": r["m_AnchoredPosition"]["x"] - 150.0, "w": r["m_SizeDelta"]["x"] + 300.0}
            rects.update(slogan)

            def font_of(t):
                fa = t["m_fontAsset"]
                return metrics.get(f if fa["m_FileID"] == 0 else externals[fa["m_FileID"] - 1], fa["m_PathID"])

            def text_width(t, text, size):
                fa = t["m_fontAsset"]
                font = metrics.get(f if fa["m_FileID"] == 0 else externals[fa["m_FileID"] - 1], fa["m_PathID"])
                return sum(font[1].get(ord(c), font[0] * 0.55) for c in text.strip()) * size / font[0] if font else None

            for o, t, g, en in labels:
                lr = org_rt[g]
                lx, ly, lw = lr["m_AnchoredPosition"]["x"], lr["m_AnchoredPosition"]["y"], lr["m_SizeDelta"]["x"]
                w_en = text_width(t, en, english[o.path_id][1])
                edit = texts.get(o.path_id)
                label_size = (edit and edit[2]) or t["m_fontSize"]
                w_ru = text_width(t, edit[1] if edit else t["m_text"], label_size)
                fl = font_of(t)
                if w_en is None or w_ru is None:
                    continue
                for o2, t2, g2, en2 in numbers:
                    nr = org_rt[g2]
                    nx, ny = nr["m_AnchoredPosition"]["x"], nr["m_AnchoredPosition"]["y"]
                    if parent_go.get(g2) == parent_go.get(g) and abs(ny - ly) < 30 and lx < nx < lx + lw + 120:
                        # the same baseline as the label (both top aligned: baseline = top - ascender); in the
                        # game the numbers still sat ~5 units lower than the bold labels
                        fn = font_of(t2)
                        y = ly - fl[3] * label_size / fl[0] + fn[3] * t2["m_fontSize"] / fn[0] + 5.0
                        rects[g2] = dict(rects.get(g2, {}), x=round(lx + w_ru + (nx - (lx + w_en)), 1), y=round(y, 1))

        page_need = auto_page_heights(env, objs, scripts, rt_of, parent_go, english, en_heights, metrics,
                                      externals, f) if english else {}
        voices = voice_texts(in_dir, scripts) if f == "resources.assets" else {}
        tile_rects, tile_texts = tile_layout(env, objs, scripts, metrics, externals, f) if f == "level3" else ({}, {})
        rects.update(tile_rects)
        msg_rects, msg_sizes, msg_extra = (restack_messages(env, objs, scripts, metrics, externals, f, english)
                                           if f == "level3" else ({}, {}, {}))
        rects.update(msg_rects)

        for o in env.objects:
            if o.type.name == "RectTransform":
                rt = o.read_typetree()
                edit = rects.get(rt["m_GameObject"]["m_PathID"])
                if edit and any(rt["m_AnchoredPosition"]["x"] != edit.get("x", rt["m_AnchoredPosition"]["x"]) or
                                rt["m_AnchoredPosition"]["y"] != edit.get("y", rt["m_AnchoredPosition"]["y"]) or
                                rt["m_SizeDelta"]["x"] != edit.get("w", rt["m_SizeDelta"]["x"]) or
                                rt["m_SizeDelta"]["y"] != edit.get("h", rt["m_SizeDelta"]["y"]) for _ in (0,)):
                    if "x" in edit:
                        rt["m_AnchoredPosition"]["x"] = edit["x"]
                    if "y" in edit:
                        rt["m_AnchoredPosition"]["y"] = edit["y"]
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
            if cls in ("LayoutElement", "HorizontalLayoutGroup", "VerticalLayoutGroup"):
                t = o.read_typetree()
                edit = LAYOUT_EDITS.get(f, {}).get(t["m_GameObject"]["m_PathID"], {})
                changed = False
                for key, value in edit.items():
                    *path, last = key.split(".")
                    node = t
                    for k in path:
                        node = node.get(k) if isinstance(node, dict) else None
                    if isinstance(node, dict) and last in node and node[last] != value:
                        node[last] = value
                        changed = True
                if changed:
                    o.save_typetree(t)
                    n["rects"] += 1
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
                if (o.path_id in restore_tmp or go_name in FONT_FROM_ORIGINAL_GO_NAMES) and o.path_id in orig_fonts:
                    asset, material = orig_fonts[o.path_id]
                    if t["m_fontAsset"] != asset or t["m_sharedMaterial"] != material:
                        t["m_fontAsset"], t["m_sharedMaterial"] = asset, material
                        changed = True
                        n["fonts"] = n.get("fonts", 0) + 1
                    if go_name in FONT_FROM_ORIGINAL_GO_NAMES and t["m_fontSize"] != STORED_SIZE:
                        t["m_fontSize"] = t["m_fontSizeBase"] = STORED_SIZE  # «СОХРАНЕНО» in its 118-wide rect
                        changed = True
                size = SIZE_EDITS.get(f, {}).get(o.path_id)
                if size and abs(t["m_fontSize"] - size) > 0.01:
                    t["m_fontSize"] = t["m_fontSizeBase"] = size
                    changed = True
                    n["texts"] += 1
                if o.path_id in tile_texts:
                    text, size, spacing = tile_texts[o.path_id]
                    if ((t["m_text"], t["m_textAlignment"], t["m_enableWordWrapping"], t["m_lineSpacing"])
                            != (text, 514, 0, spacing) or abs(t["m_fontSize"] - size) > 0.01):
                        t["m_text"], t["m_textAlignment"], t["m_enableWordWrapping"] = text, 514, 0  # middle centre
                        t["m_lineSpacing"] = spacing
                        t["m_fontSize"] = t["m_fontSizeBase"] = size
                        changed = True
                        n["tiles"] = n.get("tiles", 0) + 1
                en_text = (english.get(o.path_id) or ("",))[0] or ""
                m = BANK_DATE.match(en_text)
                site = site_of(g) if m or en_text in ("Your profile\r", "Your messages\r") else ""
                date_size = (BANK_DATE_SIZE if site.startswith("website_bank") else
                             WATERGATE_DATE_SIZE if site.startswith("website_watergate") else None)
                if m and date_size:
                    date = f"{int(m.group(2)):02}.{MONTHS.index(m.group(1)) + 1:02}.{m.group(3)}"
                    if t["m_text"] != date or abs(t["m_fontSize"] - date_size) > 0.01:
                        t["m_text"] = date
                        t["m_fontSize"] = t["m_fontSizeBase"] = date_size
                        changed = True
                        n["dates"] = n.get("dates", 0) + 1
                if (site.startswith("website_watergate") and not m
                        and abs(t["m_fontSize"] - WATERGATE_BUTTON_SIZE) > 0.01):
                    t["m_fontSize"] = t["m_fontSizeBase"] = WATERGATE_BUTTON_SIZE
                    changed = True
                    n["texts"] += 1
                if o.path_id in msg_sizes and abs(t["m_fontSize"] - msg_sizes[o.path_id]) > 0.01:
                    t["m_fontSize"] = t["m_fontSizeBase"] = msg_sizes[o.path_id]
                    changed = True
                    n["messages"] = n.get("messages", 0) + 1
                if o.path_id in blabber_fit and t.get("m_text"):
                    fa = t["m_fontAsset"]
                    font = metrics.get(f if fa["m_FileID"] == 0 else externals[fa["m_FileID"] - 1], fa["m_PathID"])
                    if font:
                        w = sum(font[1].get(ord(c), font[0] * 0.55) for c in t["m_text"].strip()) / font[0]
                        size = round(min(t["m_fontSize"], blabber_fit[o.path_id] * 0.95 / w), 2)
                        if t["m_enableWordWrapping"] or abs(t["m_fontSize"] - size) > 0.01:
                            t["m_enableWordWrapping"] = 0
                            t["m_fontSize"] = t["m_fontSizeBase"] = size
                            changed = True
                            n["counters"] = n.get("counters", 0) + 1
                if t.get("m_text") and BLABBER_NAME.search(t["m_text"]) and site_of(g).startswith("website_blabber"):
                    t["m_text"] = BLABBER_NAME.sub(lambda m: BLABBER_NAMES[m.group(1)], t["m_text"])
                    changed = True
                    n["names"] = n.get("names", 0) + 1
                if o.path_id in bank_texts and abs(t["m_fontSize"] - BANK_TEXT_SIZE) > 0.01:
                    t["m_fontSize"] = t["m_fontSizeBase"] = BANK_TEXT_SIZE
                    changed = True
                    n["bank"] = n.get("bank", 0) + 1
                m = LIKES_LABEL.match(t.get("m_text") or "")
                if m:
                    t["m_text"] = likes_ru(m.group(1)) + m.group(2)
                    changed = True
                    n["likes"] = n.get("likes", 0) + 1
                if t.get("m_text") and replace_phrases(t["m_text"]) != t["m_text"]:
                    t["m_text"] = replace_phrases(t["m_text"])
                    changed = True
                    n["texts"] += 1
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
            elif cls == "NewDebriefingElementState" and f == "resources.assets" and o.path_id in DEBRIEF_EDITS:
                t = o.read_typetree()
                edit = {k: v for k, v in DEBRIEF_EDITS[o.path_id].items() if t.get(k) != v}
                if edit:
                    t.update(edit)
                    o.save_typetree(t)
                    n["texts"] += 1
            elif cls == "Website" and f.startswith("level"):
                t = o.read_typetree()
                title = PAGE_TITLES.get(t.get("_displayName"), t.get("_displayName"))
                title = replace_phrases(title) if title else title
                if title != t.get("_displayName"):
                    t["_displayName"] = title
                    o.save_typetree(t)
                    n["sites"] += 1
            elif cls == "UpdateProfileState" and f == "resources.assets" and o.path_id in PROFILE_VALUES:
                t = o.read_typetree()
                en, ru = PROFILE_VALUES[o.path_id]
                if t["_data"]["value"]["_text"][1] == en:
                    t["_data"]["value"]["_text"][1] = ru
                    o.save_typetree(t)
                    n["texts"] += 1
            elif cls == "UpdateProfileState" and f == "resources.assets" and o.path_id in PROFILE_EDITS:
                t = o.read_typetree()
                value, drop, start, end = PROFILE_EDITS[o.path_id]
                d = t["_data"]
                if (d["value"]["_text"][1], d["DropTextLocalized"]["_text"][1], d["DragTextStartIndex"]["_textIndex"][1],
                        d["DragTextEndIndex"]["_textIndex"][1]) != (value, drop, start, end):
                    d["value"]["_text"][1], d["DropTextLocalized"]["_text"][1] = value, drop
                    d["DragTextStartIndex"]["_textIndex"][1], d["DragTextEndIndex"]["_textIndex"][1] = start, end
                    o.save_typetree(t)
                    n["texts"] += 1
            elif cls == "Mail":
                t = o.read_typetree()
                changed = False
                for key in ("_subject", "_displayName"):
                    if t.get(key) and replace_phrases(t[key]) != t[key]:
                        t[key] = replace_phrases(t[key])
                        changed = True
                if changed:
                    o.save_typetree(t)
                    n["texts"] += 1
            elif cls == "NewMailState" and f == "resources.assets" and o.path_id in MAIL_SUBJECTS:
                t = o.read_typetree()
                accepted, new = MAIL_SUBJECTS[o.path_id]
                if t.get("_subject") in accepted:
                    t["_subject"] = new
                    o.save_typetree(t)
                    n["texts"] += 1
            elif cls == "NewChatMessageState" and f == "resources.assets":
                t = o.read_typetree()
                txt = t["_text"]["_text"][1]
                if txt and chat_text(o.path_id, txt) != txt:
                    t["_text"]["_text"][1] = chat_text(o.path_id, txt)
                    o.save_typetree(t)
                    n["texts"] += 1
            elif cls == "PodcastTranscript":
                t = o.read_typetree()
                if replace_phrases(t["Text"]) != t["Text"]:
                    t["Text"] = replace_phrases(t["Text"])
                    o.save_typetree(t)
                    n["texts"] += 1
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
                changed = False
                if name and b.get("_captionOnlinepresence") != name:
                    b["_captionOnlinepresence"] = name
                    changed = True
                    n["sites"] += 1
                cap = (b.get("_captionsDocument") or {}).get("_text")
                if cap and len(cap) > 1 and cap[1] and replace_phrases(cap[1]) != cap[1]:
                    cap[1] = replace_phrases(cap[1])
                    changed = True
                    n["texts"] += 1
                if changed:
                    o.save_typetree(t)
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
                    if page in msg_extra:
                        want = max(want, round(en_heights.get(page, hs[i]) + msg_extra[page]))
                    if hs[i] < want:
                        print(f, "page height", name, round(hs[i]), "->", want)
                        hs[i] = want
                        changed = True
                        n["heights"] += 1
                en_max = max([en_heights.get(objs[c["m_PathID"]].read_typetree()["m_GameObject"]["m_PathID"], h)
                               for c, h in zip(t.get("_tabCanvases") or [], hs) if c["m_PathID"] in objs] or [0])
                dev = objs[t["m_GameObject"]["m_PathID"]].read_typetree()
                for comp in dev["m_Component"]:
                    dev_rt = objs.get(comp["component"]["m_PathID"])
                    if dev_rt is None or dev_rt.type.name != "RectTransform":
                        continue
                    for ch in dev_rt.read_typetree()["m_Children"]:
                        cro = objs.get(ch["m_PathID"])
                        cr = cro.read_typetree() if cro else None
                        if (cr and objs[cr["m_GameObject"]["m_PathID"]].read_typetree()["m_Name"] == "background"
                                and abs(cr["m_SizeDelta"]["y"] - en_max) < 1 and cr["m_SizeDelta"]["y"] < max(hs)):
                            print(f, "background", dev["m_Name"], round(cr["m_SizeDelta"]["y"]), "->", max(hs))
                            cr["m_SizeDelta"]["y"] = max(hs)
                            cro.save_typetree(cr)
                            n["heights"] += 1
                if changed:
                    o.save_typetree(t)
        data = list(env.files.values())[0].save()
        open(os.path.join(out_dir, f), "wb").write(data)
        print(f, ", ".join(f"{k} {v}" for k, v in n.items() if v) or "no changes", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
