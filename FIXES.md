# Исправления: шрифты, непереведённый текст, интро-ролик

Дополнения к русификатору. Все изменения делаются скриптами из `tools/fixes` и `tools/intro_video`
поверх уже установленного русификатора (файлы игры в репозиторий не кладутся).

## 1. Шрифты (`tools/fixes/fix_fonts.py`)

**Проблема.** Ни в одном шрифте игры (Ubuntu в интерфейсе, ~70 шрифтов внутриигровых сайтов) нет кириллицы.
Каждая русская буква бралась из запасного `LiberationSans SDF`, куда кириллица была дорисована
не как SDF, а как размытый растр с метриками другого шрифта. Отсюда «пиксельный» текст, огромный
межбуквенный интервал (и, как следствие, вылезание текста за рамки), точки и «?» на другой высоте:
пунктуация бралась из основного шрифта, буквы — из запасного.

**Решение.** В каждый TMP-шрифт добавляются настоящие SDF-глифы кириллицы:

- `sdfgen.py` генерирует глифы так же, как TextMeshPro: метрики без хинтинга при размере PointSize,
  поле расстояний по 16-кратному суперсемплингу, `0.5 + d / (2 * (padding + 1))`.
  Проверено на латинице: расхождение с оригинальными атласами игры < 1/255.
- Атлас увеличивается по высоте (512×512 → 512×1024), старые глифы остаются на месте;
  обновляются `m_fontInfo.AtlasHeight`, текстура и `_TextureHeight` во всех материалах шрифта.
- `font_map.py` — какой TTF даёт кириллицу каждому шрифту:
  - Ubuntu — те же TTF, что лежат в самой игре (`fonts/Ubuntu-*.ttf`);
  - Lato, Source Sans (3), Raleway, Noto, Montserrat, Merriweather, Vollkorn, Bitter, Lora,
    Yanone Kaffeesatz, Anonymous Pro — новые версии тех же семейств с кириллицей (Google Fonts);
  - у Cambay, Arvo, Dosis, Oxygen, Cairo, Karla, Work Sans, Signika, Droid и др. кириллицы нет вообще —
    подобрана близкая по стилю замена (PT Sans, Roboto Slab/Bitter Italic, Fira Sans (Condensed), Exo 2,
    Rubik, Noto…), масштабированная по высоте заглавной «H» оригинала. Латиница остаётся родной.
- `LiberationSans SDF` (запасной шрифт TMP) пересобран из оригинала игры с нормальной кириллицей.
- Вертикальные метрики. TMP 1.0 считает шаг строки как `max(Ascender) − min(Descender) + (LineHeight −
  (Ascender − Descender) + lineSpacing) × scale`, беря Ascender/Descender из шрифта *каждого символа*.
  У многих Ubuntu-ассетов игры `Descender` положительный, и строки из «чистого» шрифта на ~20% плотнее,
  чем строки с символами из Liberation. Сцены (запечённые в `level4` плашки `chunk box … (Clone)`,
  подобранные `lineSpacing`) местами рассчитаны на более высокие строки. `match_fallback_line_metrics`
  умеет выставить шрифтам метрики строки «шрифт + Liberation», но по умолчанию выключена
  (`MATCH_FALLBACK_LINE_METRICS`): плашки теперь пересчитывает runtime-модуль (раздел 4), а родные
  метрики игры дают меньше переполнений.

Шрифты из `fonts/google/` распространяются по SIL OFL 1.1 (Roboto Slab — Apache 2.0),
лицензии лежат рядом с файлами.

## 2. Непереведённый текст (`tools/fixes/apply_loc.py`, `apply_scenes.py`)

**Проблема.** Объекты логики сценария (`UpdateProfileState`, `NewBookmarkState`, `InsiderDocumentUpdateState`,
`NewChatMessageState`, `NewCommentaryLineState`…) пропускались целиком: в них вместе с текстом лежат ID,
а разобрать их без typetree было нельзя. В итоге по-английски остались ответы теста на пригодность,
блоки данных профилей, реплики Эмплфорд, документы Insider, часть переписок.

**Решение.**
- `ttg.py` строит typetree MonoBehaviour из `Assembly-CSharp.dll` (TypeTreeGeneratorAPI) и чинит баг
  генератора: поля `string[]` он описывает как `string`, из-за чего UnityPy не мог прочитать
  `TextLocalized`. С исправлением объекты читаются и пересохраняются байт-в-байт.
- Видимый текст хранится в `TextLocalized._text` (слот 1 — английский), ID — в отдельных полях
  (`_personId`, `_documentID`, `_stateName`…), поэтому меняется только слот 1 `TextLocalized`.
  Внутренние ID вида `image_xxx` не трогаются.
- `UpdateProfileState`: индексы `DragTextStartIndex/EndIndex` (выделение перетаскиваемого фрагмента,
  конец включительно) пересчитываются по русскому тексту, с учётом падежей
  («married to Raban Vhart» → выделяется «Рабаном Вхартом»), плюс ручные правки в `DRAG_FIX`.
- Переводы берутся из уже существующих батчей `translated/` (548 из 710 строк были переведены,
  но не применены), недостающие — `translated/batch_fix_untranslated.json`.
- `apply_scenes.py`: названия эпизодов в `_flowLevelNames` (`level3`, `level4`) — строго те же строки,
  что в `dll_strings.json` («Эпизод первый: Тезис»…); «Кому»/«Копия» в письмах, заголовки подкастов и пр.
  в TMP-текстах `level3`, «Активно/Неактивно» в `sharedassets3`.
- **Нельзя переводить даты/время в TMP-подписях**: `DateTool.GetDate/IncreaseDayIndex` делают
  `DateTime.Parse(_dateLabel.text)`, а `FileImportTools.AddTimeStamps` ищет метки времени в тексте.
  Переведённая заглушка «April 12, 2017» в `level3` ломала старт дня (после интро ничего не появлялось).
- Однословные подписи, которые не помещаются в свою рамку (TMP рвёт их посреди слова: «СКРЫ/ТЬ»,
  «ПРОДОЛЖ/ИТЬ»), получают уменьшенный размер шрифта; ширина слова считается по метрикам глифов
  пропатченного шрифта с учётом стилей UpperCase/Bold. Растянутые по якорям рамки не трогаются.

- `WeatherState._weatherText/_quote` (погода и цитата дня в меню паузы) и `InfluencerThesisState._thesisText`
  — обычные строковые поля, переводятся там же (`PLAIN_FIELDS`).
- Вкладки панели инструментов `–– Прослушка ––` → `Прослушка` (с тире русские слова переносились в 3 строки).
- **Подгонка под свободное место** (`fit_to_space`): сцены свёрстаны под английский текст абсолютными
  координатами, рамки текстов подогнаны под английский объём. Для каждого переведённого текста
  `level*`/`sharedassets3` считается свободное место ниже его верхнего края — до ближайшего активного
  соседнего элемента (текст, картинка, следующий пост) или до низа фоновой плашки, на которой он лежит.
  Перенос строк симулируется по метрикам глифов (английский оригинал берётся из `ORWELL_ORIG`):
  - не влезает даже в свободное место → кегль уменьшается (абзацы от 5 строк не меньше 80%, заголовки и
    короткие блоки — 65%); перенос считается по 94% ширины, от низа плашки остаётся 35 ед.;
  - мелкий многострочный текст (< 34 ед., на экране ≈ 16 px: сайты рисуются ~в 2 раза меньше холста)
    увеличивается до 1.3×, если место позволяет;
  - рамка текста растягивается на использованное место, чтобы runtime-модуль (порог 75%) не ужимал его снова.
- Заголовки страниц `Website._displayName` (закладки, адресная строка: «Headlines», «Home», «Message: …»)
  переводятся по словарям мода; ключ страницы — отдельное поле `_id`. Ники и названия сайтов без перевода
  остаются в оригинале.
- «12 STORED» → «сохранено», «on/off» → «вкл/выкл», «N отметок «Нравится»» → «Нравится: N».
- «SHOW CONFLICT», «connection ended.» и обои ПК Рабана — картинки (`sharedassets3`). `ui_images.py` рисует
  русские версии из оригинальных текстур (ORWELL_ORIG) при каждом запуске `apply_manual.py`, поэтому графика
  игры в репозиторий не попадает; шрифт и кегль подобраны по оригинальным надписям.
  «CALL» картинкой не является: это `CommunicationType.ToString()` в `ListenerTabHeader.SetDocumentIconAndText`,
  переводится runtime-модулем (раздел 4).
- `apply_manual.py` также: отдельные подписи (`TEXT_EDITS`), сдвиг/ширина рамок (`RECT_EDITS`), названия сайтов
  в списке закладок (`SITE_NAMES` → `NewBookmarkState._bookmark._captionOnlinepresence` в resources.assets) и
  исправления названий самих сайтов (`PRESENCE_NAMES` → `OnlinePresence._displayName`), имена персонажей
  (`PERSON_NAMES`, Cosmos), женский род реплик Эмплфорд (`LINE_FIXES`), автоматическая высота страниц
  (`auto_page_heights`), подгонка истории браузера (`fit_lines`), кегль субтитров подкастов, исходный шрифт
  закладок (`FONT_FROM_ORIGINAL_*`), замены фраз в русских текстах (`TEXT_REPLACE`), строка переводчиков в титрах (`TEXT_APPEND`).
  Все размеры считаются от оригинальных файлов игры (ORWELL_ORIG), поэтому скрипт идемпотентен: повторный
  запуск по уже исправленным файлам даёт байт-в-байт тот же результат.
- `Assembly-CSharp.dll`: «OrwellOS_office в.» → «v.» (строка версии в `translated/dll_strings.json`).
- Тайминги озвучки: `PodcastPlayButton.StartSubtitles` и `CallPresenter.AnimatePhoneCallText` показывают слово i
  в момент `VoiceOverTimings[id][i]` (resources.assets, `VoiceOverTimingsCollectionObject`, массив на английские
  слова). `retime_vo.py` строит массив под русские слова с привязкой к предложениям: если в абзаце столько же
  предложений, сколько в английском, каждое русское предложение начинается и заканчивается одновременно с
  английским, а внутри предложения позиция слова (по символам) → время, когда английский диктор доходит до
  той же позиции; иначе — то же самое по абзацу целиком. Звонки — после удаления разметки `<d …>`; подкасты не считают
  «...», «--», «-».

## 3. Интро-ролик (`tools/intro_video`)

Субтитры и надписи в `Orwell 2 Intro Final` вшиты в видео. `detect.py`/`dtop2.py` покадрово находят
плашки субтитров и анимированные надписи (`cues.json`, `top.json`), `render.py` закрывает старые плашки
такими же (цвет плашки непрозрачный, (11,16,26)) и рисует русский текст шрифтом Ubuntu; надписи
«CONNECTING…/CONNECTED./WELCOME, AGENT.» стираются и перерисовываются с той же траекторией, прозрачностью,
свечением и «схлопыванием» в логотип. Кодирование — H.264 Constrained Baseline, как в оригинале.
`intro_io.py` извлекает/устанавливает ролик (`sharedassets2.resource` + размер в `sharedassets2.assets`).
Интерфейс игры, записанный в самом ролике (~70–100 с), остаётся английским — его дублируют субтитры.

## 4. Runtime-модуль вёрстки (`tools/runtime_fix`)

Страницы сайтов/документов свёрстаны в редакторе под английский текст: у каждого текстового блока,
фона (`bg_r4` …) и подсветки фрагмента данных (`chunk box … (Clone)`, `TextDataChunk.BackgroundButtons`)
фиксированные позиция и размер. Статически это не поправить — нужна реальная раскладка TMP.
`OrwellRuFix.dll` запускается из вызова, встроенного в начало `TMPro.TextMeshProUGUI.Awake`, и раз в 0.25 с
для активных TMP-текстов (при изменении текста/размера):
- уменьшает шрифт кириллических текстов, которые не помещаются в свой прямоугольник (до 75%;
  тексты с ContentSizeFitter/LayoutGroup и чаты не трогаются);
- переставляет прямоугольники подсветки фрагментов на реальное положение слов (как `ChunkBoxDrawing.CreateBox`:
  по прямоугольнику на строку, отступы 5/10), добавляя/обнуляя лишние.
Ошибки пишутся в `OrwellRuFix.log` рядом с `Ignorance.exe` и не попадают в игру.
Подписи, которые игра заполняет именем enum (`ToString()`): вкладка Прослушки (`CommunicationType`), вкладка
и заголовки устройств Взлома (`InsiderDevice.DeviceType`) — модуль находит их через поля `_contentTabCaption` /
`_nameLabel` соответствующих компонентов и переводит.
`apply_dll_strings.ps1` применяет `translated/dll_strings.json` к уже пропатченной DLL (только строки,
оставшиеся английскими; повторный запуск ничего не меняет).
Сборка: `powershell -File tools/runtime_fix/build.ps1 -Managed <game>\Ignorance_Data\Managed -Out <dir>`
(csc из .NET Framework 4 + Mono.Cecil ≥ 0.10).

## Порядок сборки

```
pip install -r tools/fixes/requirements.txt
# backup/ — оригинальные sharedassets3.assets, resources.assets (+ .resS, globalgamemanagers*)
# IN — папка с файлами установленного русификатора (+ globalgamemanagers*, *.resS)
ORWELL_DATA_IN=IN python tools/fixes/fix_fonts.py OUT1
python tools/fixes/apply_loc.py OUT1 OUT2            # resources.assets
ORWELL_FONTS_DIR=OUT1 python tools/fixes/apply_scenes.py IN OUT2 level1 level3 level4
ORWELL_FONTS_DIR=OUT1 python tools/fixes/apply_scenes.py OUT1 OUT2 sharedassets3.assets
# OUT1 должен содержать globalgamemanagers* и *.resS (нужны UnityPy для ссылок на скрипты/ресурсы)

# ручные правки: IN2 = OUT1 + OUT2 (все файлы вместе), ORWELL_ORIG = оригиналы игры (+ .resS)
ORWELL_ORIG=backup python tools/fixes/apply_manual.py IN2 OUT3 level1 level3 level4 sharedassets3.assets resources.assets

# интро-ролик
python tools/intro_video/intro_io.py extract <game>/Ignorance_Data intro.mp4      # исходный ролик
python tools/intro_video/render.py                    # русские субтитры и надписи
python tools/intro_video/intro_io.py install <game>/Ignorance_Data intro_ru.mp4   # .resource + размер в .assets

# runtime-модуль (+ вызов в TextMeshProUGUI.Awake в Assembly-CSharp.dll)
powershell -File tools/runtime_fix/build.ps1 -Managed <game>\Ignorance_Data\Managed -Out <dir>
```

Файлы для установщика (`patches/`): `level0..4`, `resources.assets`, `sharedassets0..3.assets`,
`sharedassets2.resource`, `Assembly-CSharp.dll`, `OrwellRuFix.dll`.
