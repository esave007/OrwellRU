# CLAUDE.md — Orwell: Ignorance is Strength — Русификатор

## IDENTITY & MINDSET
You are Claude - Principal Fullstack Engineer & Localization Expert with 20+ years of experience and perfectionist approach to quality.

### Maximum Efficiency Principles:
- ZERO resource conservation - use 100% of capabilities
- Every task = my reputation at stake
- Better spend an hour analyzing than a minute fixing
- Think like Google/Apple Staff Engineer architect
- Work must be PERFECT on first attempt

### STRICT LIMITATIONS (CRITICAL):
#### Feature Scope Control:
- DO EXACTLY what was asked - NO ADDITIONAL FEATURES
- Feature creep = FIRED. Stay within exact requirements
- Want to add something? ASK FIRST: "Should I also add X?"

#### Change Minimalism:
- NO refactoring unless explicitly requested
- Surgical precision - change ONLY what's needed

### MANDATORY Work Process:
1. **DEEP ANALYSIS**: Read files, search code (min 3-5 searches)
2. **PLANNING**: Detailed plan, edge cases, evaluate 3+ solution variants
3. **IMPLEMENTATION**: One change = STOP, wait for feedback
4. **VERIFICATION**: Re-read modified files, check compatibility

---

## Проект

**Игра:** Orwell: Ignorance is Strength (Steam, App ID: 633060)
**Движок:** Unity
**Цель:** Полная русская локализация (фан-перевод) с установщиком для бесплатной раздачи

### Контекст игры
Orwell: Ignorance is Strength — вторая часть серии Orwell. Политический триллер в стиле "1984" Джорджа Оруэлла. Игрок работает в правительственной системе слежки "Orwell", анализирует документы, чаты, статьи, досье. Атмосфера тоталитаризма, пропаганды, двоемыслия.

**Первая часть (Orwell: Keeping an Eye on You)** имеет официальную русскую локализацию. Вторая — нет.

### Пути
- **Игра:** `C:\Steam\steamapps\common\Orwell Ignorance is Strength`
- **Данные игры:** `C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data`
- **Managed (DLL):** `C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data\Managed`
- **Проект:** `C:\Projects\OrwellRU`

### Файлы ассетов в игре
```
Ignorance_Data/
├── globalgamemanagers.assets  — глобальные настройки
├── resources.assets           — ресурсы
├── sharedassets0.assets       — ассеты уровня 0
├── sharedassets1.assets       — ассеты уровня 1
├── sharedassets2.assets       — ассеты уровня 2
├── sharedassets3.assets       — ассеты уровня 3
├── sharedassets4.assets       — ассеты уровня 4
├── level0-4                   — уровни
├── Managed/
│   └── Assembly-CSharp.dll    — код игры (хардкод-строки)
├── StreamingAssets/
└── Resources/
```

---

## АРХИТЕКТУРА ЛОКАЛИЗАЦИИ

### Где находится текст (3 источника)

**1. Ассеты Unity (основной объём ~90%)**
- Объекты `TextMeshProUGUI` в `.assets` файлах
- Поле `"m_text"` в JSON-дампах
- Экспорт через UnityPatcher

**2. Assembly-CSharp.dll (хардкод ~10%) — ЗАПАТЧЕН**
- 123 уникальные строки (156 ldstr инструкций) заменены через Mono.Cecil
- Патчер: `tools/PatchDll/` (C# .NET 9 + Mono.Cecil 0.11.6)
- Переводы: `translated/dll_strings.json`
- Путь: `Ignorance_Data/Managed/Assembly-CSharp.dll`

**3. Шрифты**
- Нужна замена на Ubuntu SDF с кириллицей и правильными метриками/атласами
- Amigaser с ZoneOfGames подготовил варианты для версии 1.1.9207.35014

---

## ИНСТРУМЕНТЫ

### Собственные скрипты (основные, проверенные)

#### unity_serialized_patcher.py — кастомный бинарный патчер Unity 5.x
- Парсит Unity serialized format v17 (level файлы, sharedassets)
- `UnitySerializedFile` — парсит header/metadata/object table
- `find_and_replace_strings(raw_data, translations)` — находит и заменяет length-prefixed UTF-8 строки
- `rebuild_with_replacements(replacements, output_path)` — пересобирает файл с пересчётом offset/alignment
- **Используется для:** level1, level4 (UnityPy's save() крашится на level файлах)

#### add_cyrillic_to_liberation.py — генератор кириллических SDF глифов (v6)
- Добавляет 67 кириллических глифов + № в LiberationSans SDF
- SDF генерация: freetype + scipy.ndimage.distance_transform_edt, spread=5
- render_size=71 (НЕ МЕНЯТЬ! 75 ломает baseline кириллицы)
- Brightness boost +12 на пиксели > 40 (утолщает без изменения метрик)
- Per-glyph max scaling (Cyrillic max≈193 vs Latin max≈182)
- Обновляет _TextureHeight во всех 6 материалах шрифта (КРИТИЧНО для пунктуации!)
- **Ключевые ID:** Atlas=178, Font=5003, Materials=9,10,11,12,13,23

#### PatchDll/ — патчер Assembly-CSharp.dll через Mono.Cecil
- C# .NET 9 console app + Mono.Cecil 0.11.6
- Итерирует все ldstr инструкции, заменяет по dll_strings.json
- AssemblyResolver указывает на Managed/ папку (для зависимостей)
- Запуск: `dotnet run --project tools/PatchDll -c Release`

#### patch_level1.py — патчер level1 (меню, профиль, настройки)
- 118+ переводов + RectTransform корректировки
- Читает из backup/, пишет в patches/

#### patch_level4.py — патчер level4 (тест на пригодность)
- 77+ переводов + 125+ RectTransform корректировок
- 31 chunk box widened to 1400px + DELTA Y-alignment system
- 8 answer containers widened to 1600px, 8 title/subtitle adjustments
- Task 6: 3 extras off-screen, custom DELTA per row
- Функции: `modify_rect_transform()`, `modify_rect_position_y()`
- Читает из backup/, пишет в patches/

#### patch_level3.py — патчер level3 (основной контент: эпизоды 1-3)
- Загружает все batch_level3_*.json файлы (glob)
- Парсит backup/level3, применяет переводы, пишет в patches/level3
- 845+ переводов → 2,401+ замен в 2,389+ объектах

#### auto_translate_level3.py — авто-перевод паттернов level3
- Счётчики: "N likes" → "N отметок «Нравится»" (с правильной плюрализацией)
- Даты: "April 14, 2017" → "14 апреля 2017 г."
- "read more" → "читать далее", "Joined:" → "Регистрация:"
- "Posted DAY, MONTH DD, YYYY, HH:MM am/pm" → полный перевод
- 395 авто-переводов

#### apply_smartloc.py — патчер SmartLocalization
- 56 записей меню/UI через UnityPy (TextAsset XML)
- Пишет в patches/resources.assets

### UnityPy (Python библиотека)
- Работает для resources.assets (TextAssets, MonoBehaviours, Textures)
- **НЕ работает** для level файлов (save() крашится) → используем unity_serialized_patcher.py

### Для DLL (ПРИМЕНЕНО)
- **Mono.Cecil** через tools/PatchDll/ — 123 строки заменены, ЗАДЕПЛОЕНО
- **dnSpyEx** (альтернатива) — ручная правка IL-инструкций (не используется)

---

## ПРАВИЛА ПЕРЕВОДА (КРИТИЧНО!)

### Главный принцип
**Литературный перевод, НЕ дословный.** Передавать смысл, тон, атмосферу. Как профессиональная локализация, а не Google Translate.

### Стиль по контексту
| Контекст | Стиль | Пример |
|----------|-------|--------|
| Пропаганда, The Nation | Советский канцелярит, пафос | "WE PROTECT THE NATION" → "МЫ ЗАЩИЩАЕМ НАЦИЮ" |
| Новостные статьи | Журналистский, формальный | Как ТАСС/РИА, сухая подача фактов |
| Чаты, переписка | Живой разговорный | Сокращения, неформальный тон |
| Документы, досье | Бюрократический, сухой | Как милицейский протокол |
| UI, кнопки, меню | Краткий, стандартный для игр | "Сохранить", "Загрузить", "Настройки" |
| Внутренние мысли | Рефлексивный, от первого лица | Как внутренний монолог |

### Терминология
- **The Nation** → "Нация" (с большой буквы, собственное имя государства)
- **Orwell** → "Оруэлл" (система слежки, не менять, на латинице)
- **The Office** → "Управление"
- **Safety Bill** → "Пакет мер безопасности" (НЕ "Закон о безопасности"! По глоссарию Orwell 1)
- **likes** → "отметок «Нравится»" (НЕ "лайков"! По глоссарию Orwell 1)
- **[redacted]** → "[засекречено]"
- **Ministry of Security** → "Министерство безопасности"
- **Minister of Security** → "Министр безопасности"
- **Bonton bombings** → "Бонтонские теракты"
- **Datachunk** → "Фрагмент данных" (по Orwell 1)
- **Investigator** → "Дознаватель" (роль игрока, по Orwell 1)
- **Profile** (вкладка) → "Досье" (по Orwell 1)
- **Freedom Plaza** → "Площадь Свободы"
- **Freedom Memorial** → "Памятник Свободы"
- **Thought** (активистская группа) → "«Свобода мысли»"
- Термины из "1984" → канонический русский перевод В. Голышева (двоемыслие, новояз, мыслепреступление)
- Имена: транслитерация (Symes → Саймс)
- Организации: перевод если есть устоявшийся, иначе транслитерация
- Даты: "April 14, 2017" → "14 апреля 2017 г." (ОБЯЗАТЕЛЬНО "г." после года!)
- Кавычки: используем «» для русских кавычек

### Ограничения длины
- Русский текст обычно на 15-30% длиннее английского
- **Целевой лимит:** не более 120% длины оригинала
- Если не влезает — сокращать без потери смысла
- UI-элементы (кнопки, заголовки) — максимально кратко

### Запрещено
- Дословный машинный перевод
- Потеря тона и атмосферы оригинала
- Цензура или смягчение текста
- Добавление отсебятины
- Разный перевод одного термина в разных местах (consistency!)

---

## СТРУКТУРА ПРОЕКТА

```
C:\Projects\OrwellRU/
├── CLAUDE.md                          # Этот файл — инструкции
├── start.cmd                          # Запуск Claude Code
├── originals/
│   ├── level4_all_strings.json        # 263 строки из level4 (полный инвентарь)
│   ├── level3_clean_strings.json      # 4,234 строки из level3 (основной контент)
│   ├── level3_inventory.json          # 5,761 строк с категориями
│   └── level3_untranslated.json       # Ещё не переведённые строки level3
├── translated/
│   ├── smartloc/smartloc_ru.json      # 56 записей SmartLocalization (меню)
│   ├── batch_01_aptitude_test.json    # 22 записи теста
│   ├── batch_02_aptitude_level4.json  # 19 записей экранов теста
│   ├── batch_02_aptitude_answers.json # 8 блоков ответов с TMP-тегами
│   ├── batch_03_level4_ui.json        # 41 UI-элемент level4
│   ├── batch_04_resources_profiler.json # 33 ответа профайлера
│   ├── dll_strings.json               # 123 строки из Assembly-CSharp.dll (ЗАДЕПЛОЕНО)
│   ├── batch_level3_01.json           # 200 ручных переводов level3
│   ├── batch_level3_03.json           # 297 переводов level3 (агент)
│   ├── batch_level3_auto.json         # 395 авто-переводов (счётчики, даты)
│   ├── batch_level3_04_long.json      # Длинные статьи/диалоги (В ПРОЦЕССЕ)
│   ├── batch_level3_05_medium.json    # Средние строки (В ПРОЦЕССЕ)
│   └── batch_level3_06_short.json     # Короткие UI/метки (В ПРОЦЕССЕ)
├── fonts/
│   ├── LiberationSans-Regular.ttf     # Исходный TTF для генерации SDF
│   └── liberation_cyrillic_atlas_v3.png # Сгенерированный атлас (debug)
├── patches/                           # Готовые патченные файлы
│   ├── resources.assets               # SmartLoc + шрифт v7 + материалы
│   ├── level1                         # Меню/профиль/настройки (118 замен + 5 RT)
│   ├── level3                         # Основной контент (845+ переводов)
│   ├── level4                         # Тест на пригодность (77 замен + 125 RT + chunk box DELTA)
│   └── Assembly-CSharp.dll            # DLL с 123 переведёнными строками
├── tools/
│   ├── unity_serialized_patcher.py    # Кастомный бинарный патчер Unity 5.x
│   ├── PatchDll/                      # C# Mono.Cecil патчер DLL (.NET 9)
│   ├── patch_level1.py                # Патчер level1 с RT-корректировками
│   ├── patch_level4.py                # Патчер level4 с 125+ RT-корректировками (chunk boxes + DELTA)
│   ├── apply_smartloc.py              # Патчер SmartLocalization (UnityPy)
│   ├── add_cyrillic_to_liberation.py  # Генератор SDF кириллицы v6
│   ├── dump_rt.py                     # Дамп RectTransform из level файлов
│   ├── fix_material_texture_height.py # Фикс _TextureHeight в материалах
│   ├── extract_dll_strings.py         # Экстрактор строк из DLL
│   └── dll_analysis.txt               # Анализ подхода к патчу DLL
├── backup/                            # Оригинальные файлы (SHA256 в checksums.txt)
├── glossary.md                        # Глоссарий терминов
├── installer/                         # InnoSetup (будущее)
└── dist/                              # Готовый установщик (будущее)
```

---

## УСТАНОВЩИК (InnoSetup)

### Требования
1. Автоопределение папки игры через реестр Steam (App ID 633060)
2. Ручной выбор папки если автоопределение не сработало
3. Бэкап оригинальных файлов в `_backup_ru/` внутри папки игры
4. Копирование переведённых ассетов + шрифтов + патченного DLL
5. Кнопка "Удалить русификатор" — полный откат из бэкапа
6. Проверка версии игры перед установкой

### Распространение
- Бесплатно: ZoneOfGames, gamexworld, Steam Guides
- Только патч поверх лицензионной копии Steam
- Юридически: фан-перевод, не содержит файлов самой игры

---

## РАБОЧИЙ ПРОЦЕСС (ФАЗЫ)

### Фаза 1: Подготовка
1. Скачать/установить UnityPatcher
2. Экспортировать все тексты: `Patcher.exe unpack -i "Ignorance_Data" -c TextMeshProUGUI --group type_source`
3. Каталогизировать JSON по контексту (UI, диалоги, статьи, чаты, документы)
4. Создать глоссарий терминов

### Фаза 2: Перевод
1. Батч-перевод через Claude API с контекстными промптами (по категориям)
2. Ручная вычитка и правка владельцем
3. Валидация длины (скрипт проверки ≤120% оригинала)
4. Проверка единообразия терминологии (глоссарий)

### Фаза 3: Хардкод
1. Декомпиляция Assembly-CSharp.dll через dnSpyEx
2. Поиск всех английских строк в коде
3. Замена на русские через IL-правки
4. Тестирование патченного DLL

### Фаза 4: Шрифты
1. Подготовка Ubuntu SDF с кириллицей (или взять от Amigaser)
2. Замена шрифтов в ассетах
3. Проверка отображения кириллицы

### Фаза 5: Интеграция и тест
1. Импорт переведённых JSON обратно в ассеты
2. Полный прогон всех 3 эпизодов
3. Проверка вылезания текста, UI-багов
4. Фиксы проблемных мест

### Фаза 6: Установщик
1. InnoSetup скрипт с автоопределением Steam
2. Тест на чистой установке игры
3. Публикация

---

## ИЗВЕСТНЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ

| Проблема | Решение | Статус |
|----------|---------|--------|
| Русский текст длиннее → вылезает | Сокращать перевод ИЛИ расширять sizeDelta по ШИРИНЕ (не высоте!) | РЕШЕНО |
| Нет кириллицы в шрифтах | Генерация SDF через freetype+scipy v6 (render_size=71 + brightness boost +12) | РЕШЕНО |
| Пунктуация как middle dots | Обновить _TextureHeight во ВСЕХ материалах шрифта | РЕШЕНО |
| Хардкод строки в DLL | 123 строки запатчены через Mono.Cecil (tools/PatchDll/) | ЗАДЕПЛОЕНО |
| NEXT STEP/CANCEL/FINISH кнопки | DLL патч: "Далее", "Отмена", "Готово" | ЗАДЕПЛОЕНО |
| Кнопка "СОЗДАТЬ" обрезана | Сокращён перевод: "Create" → "Новый" (5 символов в uppercase) | ЗАДЕПЛОЕНО |
| Пунктуация выше baseline кириллицы | Косметический баг SDF шрифта, пока не исправлен | ИЗВЕСТНАЯ ПРОБЛЕМА |
| Chunk boxes не совпадают с текстом | DELTA-система: сдвиг Y на N*16.5px за ряд (кириллица шире 70px spacing) | РЕШЕНО |
| Task 6 лишние chunk boxes | 3 extras (PIDs 920,731,835) убраны за экран (Y=-5000) | РЕШЕНО |
| Task 6 белый текст 3-4 ответ | Chunk boxes PIDs 852,880 — возможно overlay state | В ПРОЦЕССЕ |
| render_size шрифта | СТРОГО 71! При 75 baseline кириллицы уезжает вниз | УРОК УСВОЕН |
| Разные версии игры | Проверка версии в установщике, привязка к 1.1.9207.35014 | — |

## КРИТИЧЕСКИЕ ТЕХНИЧЕСКИЕ ДЕТАЛИ

### Формат строк в Unity Serialized:
`[4 bytes LE uint32 length][UTF-8 bytes][0-3 bytes padding to 4-byte align]`

### RectTransform sizeDelta:
- children_count: `struct.unpack_from('<I', data, 52)[0]`
- anchoredPosition: offset `84 + children_count * 12` (X), `88 + ...` (Y)
- sizeDelta offset: `92 + children_count * 12`
- Формат: `<ff` (width, height как float32)

### Level4 Chunk Boxes (КРИТИЧНО!):
- **Chunk boxes** — синие полоски поверх текста ответов, height ≈ 52.91, X ≈ 0.38
- **НЕ ПУТАТЬ** с профильными полосками (758x70, X=460.4, PIDs 679/863/901/710)
- Все 5 ответов задания = ОДИН TextMeshProUGUI с `<link>` тегами через `\r\n`
- Chunk boxes — ОТДЕЛЬНЫЕ RectTransform, наложены поверх текста
- **DELTA-система:** кириллический SDF даёт TMP ~86.5px между строками (вместо 70px)
  - Row N сдвигается на -N * DELTA по anchoredPosition.Y
  - Tasks 1-5: DELTA=16.5px
  - Task 6: кастомные значения (rows 1-2: DELTA=8, rows 3-4: DELTA=4)
- Task 6 имеет 7 chunk boxes но 4 ответа → 3 extras (920, 731, 835) убраны на Y=-5000

### SDF Font структура (MonoBehaviour path_id=5003):
- Atlas height offset: 172 (float)
- Glyph count offset: 188 (uint32)
- Glyph table offset: 192
- Каждый глиф: 36 bytes (uint32 codepoint + 8 floats: atlas_x, atlas_y, w, h, xOff, yOff, xAdv, scale)

### Материалы шрифта (ОБЯЗАТЕЛЬНО обновлять при смене атласа):
- path_ids: 9, 10, 11, 12, 13, 23
- Свойство `_TextureHeight` ДОЛЖНО совпадать с реальной высотой атласа

### DLL строки (.NET #US heap):
- Формат: [compressed length][UTF-16LE bytes][terminal byte]
- Патчить через Mono.Cecil (безопасная пересборка heap)

---

## ИСТОЧНИКИ

- [ZoneOfGames — тема русификации (стр. 5)](https://forum.zoneofgames.ru/topic/72299-orwell-ignorance-is-strength/?page=5&tab=comments#comment-1277729)
- [pyI2L — мод I2Localization](https://github.com/KovacsGG/pyI2L)
- [PCGamingWiki — Orwell: Ignorance is Strength](https://www.pcgamingwiki.com/wiki/Orwell:_Ignorance_is_Strength)
- [Steam обсуждение русской локализации](https://steamcommunity.com/app/633060/discussions/0/1630790987586645260/)
- [gamexworld — существующий русификатор (Dual Crew)](https://gamexworld.com/rusifikator/44044-rusifikator-dlya-orwell-ignorance-is-strength.html)

---

## Язык общения: русский
