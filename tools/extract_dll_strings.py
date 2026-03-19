#!/usr/bin/env python3
"""
Extract and translate user-facing strings from Assembly-CSharp.dll #US heap.
Outputs translated/dll_strings.json with translation mapping.
"""
import struct, json, re, os, sys

os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

dll_path = r'C:\Projects\OrwellRU\backup\Assembly-CSharp.dll'
with open(dll_path, 'rb') as f:
    data = f.read()

# #US heap location (from PE/.NET metadata parsing)
us_offset = 0x1AD628
us_size = 0x1C18C
us_data = data[us_offset:us_offset + us_size]

# Parse all strings from #US heap
strings = []
pos = 1  # skip first null byte
while pos < us_size:
    b0 = us_data[pos]
    if b0 == 0:
        pos += 1
        continue
    # Compressed integer length
    if (b0 & 0x80) == 0:
        length = b0
        pos += 1
    elif (b0 & 0xC0) == 0x80:
        if pos + 1 >= us_size:
            break
        length = ((b0 & 0x3F) << 8) | us_data[pos + 1]
        pos += 2
    elif (b0 & 0xE0) == 0xC0:
        if pos + 3 >= us_size:
            break
        length = ((b0 & 0x1F) << 24) | (us_data[pos+1] << 16) | (us_data[pos+2] << 8) | us_data[pos+3]
        pos += 4
    else:
        pos += 1
        continue
    if length <= 0 or pos + length > us_size:
        pos += 1
        continue
    str_bytes = us_data[pos:pos + length - 1]
    try:
        s = str_bytes.decode('utf-16-le')
        if s.strip():
            strings.append({'offset': hex(pos), 'text': s, 'byte_length': length})
    except:
        pass
    pos += length

print(f"Total strings in #US heap: {len(strings)}")

# ============================================================
# Translation mapping: English -> Russian
# Only user-facing strings that appear in the game UI
# ============================================================
TRANSLATE = {
    # === APTITUDE TEST / ONBOARDING ===
    "Next step": "Следующий шаг",
    "Cancel": "Отмена",
    "Finish": "Готово",
    "DID YOU KNOW?": "А ВЫ ЗНАЛИ?",
    "YOU ARE 1 OF {0} ACCEPTED APPLICANTS.": "ВЫ ОДИН ИЗ {0} ПРИНЯТЫХ КАНДИДАТОВ.",
    "YOU ARE THE FIRST ACCEPTED APPLICANT.": "ВЫ ПЕРВЫЙ ПРИНЯТЫЙ КАНДИДАТ.",
    "YOU ARE USING THE OFFICE VERSION OF ORWELL.": "ВЫ ИСПОЛЬЗУЕТЕ СЛУЖЕБНУЮ ВЕРСИЮ ORWELL.",
    "NO CONNECTION": "НЕТ ПОДКЛЮЧЕНИЯ",
    "GO ONLINE TO SIGN-UP FOR OUR NEWSLETTER.": "ПОДКЛЮЧИТЕСЬ К СЕТИ, ЧТОБЫ ПОДПИСАТЬСЯ НА РАССЫЛКУ.",
    "Please choose a profile picture.": "Пожалуйста, выберите изображение профиля.",
    "Please enter a name.": "Пожалуйста, введите имя.",
    "Please enter a valid email address.": "Пожалуйста, введите корректный адрес эл. почты.",
    "Please insert at least one datachunk.": "Пожалуйста, загрузите хотя бы один блок данных.",
    "Setting up profile": "Настройка профиля",
    "You must agree to the stated terms.": "Вы должны принять указанные условия.",
    "Aptitude Test": "Тест на профпригодность",
    "Logging in": "Вход в систему",
    "Processing": "Обработка",
    "Create new profile": "Создать новый профиль",
    "new portrait": "новый портрет",

    # === MAIN MENU / PROFILES ===
    "Empty Profile": "Пустой профиль",
    "Days on duty: ": "Дней на службе: ",
    "Days on duty: 0": "Дней на службе: 0",
    "Profile 0": "Профиль 0",
    "Profile ": "Профиль ",
    "None": "Нет",
    "Assigned Case: Bonton Bombings": "Назначенное дело: Взрывы в Бонтоне",
    "Delete profile": "Удалить профиль",
    "Are you sure you want to delete this profile?": "Вы уверены, что хотите удалить этот профиль?",
    "No, keep profile": "Нет, сохранить",
    "Yes, delete profile": "Да, удалить",
    "Load episode ": "Загрузить эпизод ",
    "Are you sure you want to load this Episode?": "Вы уверены, что хотите загрузить этот эпизод?",
    "All subsequent progress of this profile will be lost.": "Весь последующий прогресс этого профиля будет утерян.",
    "No, keep progress": "Нет, сохранить прогресс",
    "Yes, load episode": "Да, загрузить",
    "Episode One: Thesis": "Эпизод первый: Тезис",
    "Episode Two: Antithesis": "Эпизод второй: Антитезис",
    "Episode Three: Synthesis": "Эпизод третий: Синтез",
    "One": "Первый",
    "Two": "Второй",
    "Three": "Третий",
    "Four": "Четвёртый",
    "Five": "Пятый",
    "Ignorance is Strength": "Незнание \u2014 сила",

    # === IN-GAME UI: DIALOGS ===
    "Log Out": "Выйти",
    "Log out": "Выйти",
    "Are you sure you want to log out? Orwell will remember where you left off.": "Вы уверены, что хотите выйти? Orwell сохранит ваш прогресс.",
    "Yes": "Да",
    "No": "Нет",
    "Quit Orwell": "Выйти из Orwell",
    "Are you sure you want to quit your session? Orwell will remember where you left off.": "Вы уверены, что хотите завершить сеанс? Orwell сохранит ваш прогресс.",
    "Are you sure you want to quit to your desktop?": "Вы уверены, что хотите выйти на рабочий стол?",
    "FINISH WORK?": "ЗАВЕРШИТЬ РАБОТУ?",
    "Are you sure you want to finish your work for today? All unprocessed Datachunks will expire.": "Вы уверены, что хотите завершить работу на сегодня? Все необработанные блоки данных будут утрачены.",
    "Yes, log out": "Да, выйти",
    "No, stay logged in": "Нет, остаться",
    "Summary Day ": "Итоги дня ",

    # === LISTENER (CALLS/CHATS) ===
    "Incoming Call": "Входящий звонок",
    "Incoming Chat": "Входящий чат",
    " is starting a conference call.": " начинает конференц-звонок.",
    " calling ": " звонит ",
    "Do you want to tune in now?": "Хотите подключиться сейчас?",
    "Archive for later": "Отложить",
    "Tune in": "Подключиться",
    " messaging ": " пишет ",
    "Read Messages": "Читать сообщения",

    # === PROFILER ===
    "Physique": "Телосложение",
    "N/A": "Н/Д",
    "Agent": "Агент",

    # === DEVICE/DOCUMENT TYPES ===
    "Desktop": "Рабочий стол",
    "Text": "Текст",
    "Note": "Заметка",
    "Map": "Карта",
    "History": "История",
    "Picture": "Изображение",
    "Mail": "Почта",
    "Subject": "Тема",
    "Contacts": "Контакты",
    "Chat": "Чат",

    # === OBJECTIVES/NOTIFICATIONS ===
    "New objective": "Новая задача",
    "Objective solved": "Задача выполнена",
    "Notice": "Уведомление",
    "Orwell-ID: ": "Orwell-ID: ",
    "Data uploading": "Загрузка данных",
    "Data uploaded": "Данные загружены",
    "Solved: ": "Решено: ",
    "Solved Objective": "Задача выполнена",
    "New Objective": "Новая задача",

    # === CONNECTIVITY ===
    "Orwell has lost the connection to the main server.": "Orwell потерял подключение к главному серверу.",
    "The connection to the main server has been re-established.": "Подключение к главному серверу восстановлено.",

    # === TIME LABELS (chat timestamps) ===
    "    just now": "    только что",
    "1 min ago": "1 мин. назад",
    "2 min ago": "2 мин. назад",
    "3 min ago": "3 мин. назад",
    "4 min ago": "4 мин. назад",
    "5 min ago": "5 мин. назад",
    "recorded earlier": "записано ранее",
    "earlier": "ранее",

    # === EXHIBITION MODE ===
    "Exhibition Mode": "Выставочный режим",
    "Insufficient activity detected. Restarting Orwell in ...": "Обнаружено отсутствие активности. Перезапуск Orwell через ...",
    "Continue playing": "Продолжить",
    "Restart": "Перезапуск",
    " (Exhibition Mode)": " (Выставочный режим)",

    # === CONFLICT MESSAGES (in-game datachunk UI, shown to player) ===
    "A conflict with another <link=": "Конфликт с другим <link=",
    "><u><i>datachunk</i></u></link> was already solved.": "><u><i>блоком данных</i></u></link> уже решён.",
    "There is a conflict with another <link=": "Обнаружен конфликт с другим <link=",
    "><u><i>datachunk</i></u></link>.": "><u><i>блоком данных</i></u></link>.",
    "A conflict with ": "Конфликт с ",
    " unknown datachunk was already solved.": " неизвестным блоком данных уже решён.",
    "There is a conflict with ": "Обнаружен конфликт с ",
    " unknown datachunk.": " неизвестным блоком данных.",
    "There is a conflict with unknown datachunks.": "Обнаружен конфликт с неизвестными блоками данных.",

    # === PAIRING SCREEN ===
    "Disable Pairing": "Отключить сопряжение",
    "Note: We strongly recommend pairing with an investigator for an enhanced user experience.": "Примечание: для улучшения работы настоятельно рекомендуется сопряжение с дознавателем.",

    # === MISCELLANEOUS UI-VISIBLE ===
    "Orwell": "Orwell",
    "BIG Attendee": "Участник BIG",
    "Submit": "Отправить",
    "a communication": "сообщение",
    "datachunk": "блок данных",
    "datachunks": "блоки данных",
    "was": "был",
    "were": "были",
    "this document": "этот документ",

    # === VERSION STRING (partially visible) ===
    "OrwellOS_office v.": "OrwellOS_office в.",
}

# ============================================================
# Match translations to heap entries and build output
# ============================================================
output = {
    "_meta": {
        "description": "Translation mapping for Assembly-CSharp.dll #US heap strings (Orwell: Ignorance is Strength)",
        "dll_path": "backup/Assembly-CSharp.dll",
        "us_heap_absolute_offset": hex(us_offset),
        "us_heap_size": us_size,
        "total_strings_in_heap": len(strings),
        "translatable_count": len(TRANSLATE),
        "patching_approach": "Mono.Cecil (recommended) or dnSpyEx IL editing",
        "notes": [
            "Strings are UTF-16LE encoded in the .NET #US (User Strings) heap",
            "Recommended: use Mono.Cecil to load assembly, iterate all methods, find ldstr instructions matching original text, replace with Russian",
            "Alternative: use dnSpyEx GUI to search for each string and edit IL directly",
            "IMPORTANT: Russian text is longer than English - verify UI layout after patching",
            "Some strings are concatenated at runtime (e.g. ' calling ') - context matters",
        ]
    },
    "translations": {}
}

found = {}
not_found = []

for en, ru in TRANSLATE.items():
    matched = False
    for s in strings:
        if s['text'] == en:
            found[en] = {
                "original": en,
                "translation": ru,
                "heap_offset": s['offset'],
                "byte_length": s['byte_length'],
                "original_chars": len(en),
                "translation_chars": len(ru),
                "length_ratio_pct": round(len(ru) / max(len(en), 1) * 100),
            }
            matched = True
            break
    if not matched:
        not_found.append(en)

output["translations"] = found
if not_found:
    output["not_found_in_heap"] = not_found

# Save
out_path = r'C:\Projects\OrwellRU\translated\dll_strings.json'
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Saved {len(found)} translations to {out_path}")
if not_found:
    print(f"NOT FOUND in heap ({len(not_found)}):")
    for nf in not_found:
        print(f"  {repr(nf)}")

print(f"\n=== LENGTH RATIO WARNINGS (>120%) ===")
warnings = 0
for en, info in found.items():
    if info["length_ratio_pct"] > 120:
        warnings += 1
        print(f"  {info['length_ratio_pct']}% | {repr(en[:60])} -> {repr(info['translation'][:60])}")
if warnings == 0:
    print("  None")
print(f"\nTotal: {len(found)} matched, {len(not_found)} not found, {warnings} length warnings")
