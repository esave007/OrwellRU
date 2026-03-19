#!/usr/bin/env python3
"""
Patch level1 with Russian translations for main menu / profile UI.
Reads from BACKUP, outputs to patches/level1.

v2: Added missing translations, shortened overflowing text,
    added RectTransform adjustments for buttons/containers.
"""
import os, sys, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile, find_and_replace_strings

PROJECT = Path(r"C:\Projects\OrwellRU")
BACKUP = PROJECT / "backup"

# All English → Russian translations for level1
# Main menu, profile creation, settings, episode selection UI
TRANSLATIONS = {
    # --- Buttons & Navigation ---
    "Cancel": "Отмена",
    "Next step": "Далее",
    "Previous step": "Назад",
    "back": "назад",
    "Create": "Новый",
    "Log In": "Войти",
    "Loading": "Загрузка",
    "Please Wait": "Подождите",

    # --- Profile ---
    "Delete Profile": "Удалить профиль",
    "Profile Options": "Параметры профиля",
    "Profile Name": "Имя профиля",
    "Setting up Profile": "Настройка профиля",
    "Please create a profile:": "Создайте профиль:",
    "Enter your name": "Введите ваше имя",
    "Select a profile picture": "Выберите аватар",
    "Are you sure you want to delete this profile?": "Вы уверены, что хотите удалить этот профиль?",
    "Yes, delete profile": "Да, удалить профиль",
    "No, keep profile": "Нет, оставить профиль",
    "All profile slots occupied": "Все слоты профилей заняты",
    "Incompatible profile. Please update Orwell.": "Несовместимый профиль. Обновите Orwell.",
    "Name": "Имя",
    "\u200bName": "\u200bИмя",

    # --- Settings ---
    "Audio": "Звук",
    "Video": "Видео",
    "Volume Sound Effects": "Громкость эффектов",
    "Volume Music": "Громкость музыки",
    "Volume Voices": "Громкость голосов",
    "Full screen": "Полный экран",
    "Settings\r\n": "Настройки\r\n",
    "Credits\r\n": "Авторы\r\n",
    "on": "вкл",
    "off": "выкл",

    # --- Welcome & Registration ---
    "WELCOME, AGENT!": "С ВОЗВРАЩЕНИЕМ, АГЕНТ!",
    "WELCOME,": "С ВОЗВРАЩЕНИЕМ,",
    "welcome,": "с возвращением,",
    "DID YOU KNOW?": "ВЫ ЗНАЛИ?",
    "YOU HAVE BEEN SELECTED FOR SPECIAL DUTY.": "ВЫ ОТОБРАНЫ ДЛЯ ОСОБОГО ЗАДАНИЯ.",
    "YOUR DUTY IS TO SAFEGUARD THE NATION.": "ВАШ ДОЛГ — ЗАЩИЩАТЬ НАЦИЮ.",
    "YOUR REGISTRATION IS NOW COMPLETE.": "РЕГИСТРАЦИЯ ЗАВЕРШЕНА.",
    "YOU MAY NOW ENTER YOUR eMAIL ADDRESS:": "ВВЕДИТЕ ВАШ АДРЕС ЭПОЧТЫ:",
    "Thank you for serving the nation.": "Благодарим за службу Нации.",
    "Thank you for heeding the call of The Office.": "Благодарим за отклик на призыв Управления.",
    "BE DILIGENT,": "БУДЬТЕ БДИТЕЛЬНЫ,",
    "Ignorance is strength": "Незнание — сила",
    # --- NEW: missing welcome/registration strings ---
    "YOU HAVE BEEN ACCEPTED\nINTO ORWELL.": "ВЫ ПРИНЯТЫ\nВ СИСТЕМУ ORWELL.",
    "CONGRATULATIONS,": "ПОЗДРАВЛЯЕМ,",
    "CONGRATULATIONS,\r\n": "ПОЗДРАВЛЯЕМ,\r\n",
    "FOR ENSURING THE SAFETY OF \r\nTHE NATION'S PEOPLE.": "ЗА ОБЕСПЕЧЕНИЕ БЕЗОПАСНОСТИ\r\nГРАЖДАН НАЦИИ.",
    "THANK YOU\r\n\r\n": "БЛАГОДАРИМ\r\n\r\n",
    "THANK YOU": "БЛАГОДАРИМ",
    "YOU ARE 1 OF 18.069 PROSPECTIVE AGENTS.\r\n": "ВЫ 1 ИЗ 18 069 КАНДИДАТОВ В АГЕНТЫ.\r\n",
    "YOU ARE 1 OF 18.069 PROSPECTIVE AGENTS.": "ВЫ 1 ИЗ 18 069 КАНДИДАТОВ В АГЕНТЫ.",

    # --- Episodes ---
    "Load Episode": "Загрузить эпизод",
    "Episode 1": "Эпизод 1",
    "Episode 2": "Эпизод 2",
    "Episode 3": "Эпизод 3",
    "Episode Five: Under The Spreading Chestnut Tree": "Эпизод пятый: Под развесистым каштаном",
    # Note: "Episode 5" is a short label, keep numbering
    "Episode 5": "Эпизод 5",
    "Please select an Episode. ALl subsequent progress will be lost.": "Выберите эпизод. Весь последующий прогресс будет утрачен.",
    "Finish all episodes to unlock chapter selection": "Пройдите все эпизоды, чтобы открыть выбор глав",

    # --- Investigator Pairing ---
    "AGENT INVESTIGATOR PAIRING": "НАЗНАЧЕНИЕ СЛЕДОВАТЕЛЯ АГЕНТУ",
    "The following investigators are available for pairing. Please chose the corresponding profile of the investigator you wish to be paired with, if any.":
        "Следующие следователи доступны для назначения. Выберите профиль следователя, с которым хотите работать в паре, если таковой имеется.",
    "We strongly recommend pairing with an investigator for an enhanced user experience.":
        "Мы настоятельно рекомендуем работать в паре со следователем для расширенного пользовательского опыта.",
    "There are no investigators available for pairing at this time. Please refer to the regular Orwell program.":
        "В настоящее время нет доступных следователей для назначения. Обратитесь к обычной программе Orwell.",

    # --- Assigned Case ---
    "Assigned Case: Bonton Bombings": "Назначенное дело: Взрывы в Бонтоне",
    "Days on duty:": "Дней на службе:",
    "Days on duty: 05": "Дней на службе: 05",

    # --- Steps ---
    "Step 01/03": "Шаг 01/03",
    "Step 02/03": "Шаг 02/03",
    "Step 03/03": "Шаг 03/03",
    "Step 02/04": "Шаг 02/04",

    # --- Privacy / Terms ---
    "PLEASE AGREE TO THE FOLLOWING TERMS:": "ПРИМИТЕ СЛЕДУЮЩИЕ УСЛОВИЯ:",
    "I agree to the terms stated above.": "Я принимаю вышеуказанные условия.",
    # Shortened to fit button: was "Показать политику конфиденциальности"
    "Show Privacy Policy in Browser": "Политика конфиденциальности",
    "I am under 16 years old": "Мне не исполнилось 16 лет",
    "Import credentials from Facebook*": "Импорт данных из Facebook*",
    "* optional": "* необязательно",
    "or": "или",
    "Enter email address (optional)": "Введите эл. почту (необязательно)",
    "Please tell us your proper name or else you shall be doomed.":
        "Пожалуйста, укажите ваше настоящее имя, иначе вас постигнет кара.",
    # Shortened email text to avoid overflow
    "Entering your email address will allow us to inform you about updates on your Orwell case, potential new cases and monthly e-newsletters about news, related products and more. Your information will be handled with care and not used for any other purpose.":
        "Указав эл. почту, вы будете получать уведомления о вашем деле в Orwell, новых делах и рассылках. Данные не будут использованы в иных целях.",
    "As part of our privacy policy and term, we do not collect the data of those under the age of 16. You may proceed with your mission.":
        "В соответствии с политикой конфиденциальности мы не собираем данные лиц младше 16 лет. Вы можете продолжить задание.",
    # --- NEW: terms bullet points ---
    "· I am willing to severely affect the lives of citizens and non-citizens of The Nation.\n· I will do whatever is necessary to keep The Nation from harm.\n· While working I will only adhere only to the statutes and principles of The Office.":
        "· Я готов существенно влиять на жизни граждан и неграждан Нации.\n· Я сделаю всё необходимое для защиты Нации.\n· При работе я буду следовать исключительно уставу и принципам Управления.",
    # --- NEW: unsubscribe notice (text ends with \r in the asset) ---
    "If you wish to unsubscribe, you can do so at any time by clicking the unsubscribe notice at the end of every e-newsletter we send to your email address.\r":
        "Для отписки нажмите на ссылку внизу любой рассылки, отправленной на ваш адрес эл. почты.\r",

    # --- Propaganda slogans (pid=1476) ---
    "WE PROTECT THE NATION.": "МЫ ЗАЩИЩАЕМ НАЦИЮ.",
    "YOUR WORK WILL FURTHER THE NATION.": "ВАШ ТРУД ПОСЛУЖИТ НАЦИИ.",
    "THANK YOU FOR STANDING WATCH.": "БЛАГОДАРИМ ЗА БДИТЕЛЬНОСТЬ.",
}

# RectTransform adjustments for Russian text
# {rt_path_id: (new_width, new_height)}
RT_ADJUSTMENTS = {
    992:  (400, 80),     # PreviousStepButton (was 385x80) — "Назад" is shorter, but keep safe width
    969:  (560, 30),     # Privacy Policy link (was 532x30) — "Политика конфиденциальности" slightly wider
    1026: (1451, 210),   # Terms bullet points text (was 1451x188) — Russian text slightly taller
    1057: (1164, 100),   # Email notification text (was 1164x140) — shortened Russian fits, reduce height
    1149: (1164, 80),    # Unsubscribe notice text (was 1164x140) — shortened Russian fits, reduce height
    # --- Welcome screen: widen containers so Russian text fits on 1 line ---
    832:  (1700, 92.48),  # "С ВОЗВРАЩЕНИЕМ, АГЕНТ!" — was 1297x92 (too narrow for Russian)
    983:  (1700, 92.48),  # "с возвращением," variant (same position)
    1004: (1700, 92.48),  # "С ВОЗВРАЩЕНИЕМ," variant (same position)
    1093: (1700, 174.48), # "Благодарим за отклик..." subtitle — widen to match
}

# Y position adjustments for welcome/registration screen.
Y_ADJUSTMENTS = {
    1093: -601.05,   # "Благодарим за отклик..." subtitle — moved DOWN 70px (was -531.05)
}


def modify_rect_transform(raw_data, new_width, new_height):
    """Modify sizeDelta in a RectTransform's raw data."""
    data = bytearray(raw_data)
    children_count = struct.unpack_from('<I', data, 52)[0]
    size_delta_offset = 92 + children_count * 12
    old_w, old_h = struct.unpack_from('<ff', data, size_delta_offset)
    struct.pack_into('<ff', data, size_delta_offset, new_width, new_height)
    return bytes(data), old_w, old_h


def modify_rect_position_y(raw_data, new_y):
    """Modify anchoredPosition.Y in a RectTransform's raw data."""
    data = bytearray(raw_data)
    children_count = struct.unpack_from('<I', data, 52)[0]
    anchor_y_offset = 88 + children_count * 12
    old_y = struct.unpack_from('<f', data, anchor_y_offset)[0]
    struct.pack_into('<f', data, anchor_y_offset, new_y)
    return bytes(data), old_y


def main():
    print("=" * 60)
    print("LEVEL1 PATCHER v2: Translations + UI adjustments")
    print("=" * 60)

    # ALWAYS parse from BACKUP (original English)
    backup_path = BACKUP / "level1"
    print(f"\nParsing BACKUP {backup_path}...")
    usf = UnitySerializedFile(str(backup_path))
    print(f"  Objects: {len(usf.objects)}, File size: {usf.file_size}")
    print(f"  Translations loaded: {len(TRANSLATIONS)}")

    replacements = {}
    total_replaced = 0

    # Apply text translations to ALL MonoBehaviour objects
    print("\nApplying translations to all MonoBehaviour objects:")
    for obj in usf.objects:
        if obj['type_index'] >= len(usf.types):
            continue
        class_id = usf.types[obj['type_index']]['class_id']
        if class_id != 114:  # MonoBehaviour only
            continue
        raw = usf.get_object_data(obj['path_id'])
        if not raw or len(raw) < 20:
            continue
        new_raw, count = find_and_replace_strings(raw, TRANSLATIONS)
        if count > 0:
            replacements[obj['path_id']] = new_raw
            total_replaced += count
            print(f"  pid={obj['path_id']:5d}: {count} replacement(s), "
                  f"{len(raw)} -> {len(new_raw)} bytes")

    print(f"\nText: {total_replaced} replacements in {len(replacements)} objects")

    # Apply RectTransform adjustments
    print("\nUI adjustments (RectTransform sizeDelta):")
    for rt_pid, (new_w, new_h) in RT_ADJUSTMENTS.items():
        raw = usf.get_object_data(rt_pid)
        if raw is None:
            print(f"  RT pid={rt_pid}: NOT FOUND")
            continue
        new_raw, old_w, old_h = modify_rect_transform(raw, new_w, new_h)
        replacements[rt_pid] = new_raw
        print(f"  RT pid={rt_pid}: ({old_w:.0f}x{old_h:.0f}) -> ({new_w:.0f}x{new_h:.0f})")

    # Apply Y position adjustments
    print("\nY position adjustments:")
    for rt_pid, new_y in Y_ADJUSTMENTS.items():
        raw = replacements.get(rt_pid) or usf.get_object_data(rt_pid)
        if raw is None:
            print(f"  RT pid={rt_pid}: NOT FOUND")
            continue
        new_raw, old_y = modify_rect_position_y(raw, new_y)
        replacements[rt_pid] = new_raw
        print(f"  RT pid={rt_pid}: Y {old_y:.1f} -> {new_y:.1f} (delta={new_y - old_y:.1f})")

    # Rebuild
    output_path = PROJECT / "patches" / "level1"
    print(f"\nRebuilding {output_path}...")
    usf.rebuild_with_replacements(replacements, str(output_path))

    # Verify: check Russian strings are present in output
    print("\nVerification (Russian strings):")
    with open(output_path, 'rb') as f:
        data = f.read()
    checks = [
        "Отмена",                       # Cancel
        "Далее",                         # Next step (was "Следующий шаг")
        "Назад",                         # Previous step (was "Предыдущий шаг")
        "Удалить профиль",             # Delete Profile
        "Параметры профиля",           # Profile Options
        "Создать",                       # Create
        "Войти",                         # Log In
        "Загрузка",                      # Loading
        "С ВОЗВРАЩЕНИЕМ, АГЕНТ!",     # WELCOME, AGENT!
        "Звук",                          # Audio
        "Видео",                         # Video
        "Громкость эффектов",          # Volume Sound Effects
        "Громкость музыки",            # Volume Music
        "Полный экран",                 # Full screen
        "Загрузить эпизод",            # Load Episode
        "Эпизод 1",                     # Episode 1
        "Эпизод 2",                     # Episode 2
        "Эпизод 3",                     # Episode 3
        "Назначенное дело: Взрывы в Бонтоне",  # Assigned Case
        "МЫ ЗАЩИЩАЕМ НАЦИЮ.",         # WE PROTECT THE NATION.
        "Незнание — сила",             # Ignorance is strength
        "Дней на службе:",             # Days on duty:
        "ПРИМИТЕ СЛЕДУЮЩИЕ УСЛОВИЯ:",  # PLEASE AGREE TO...
        "Да, удалить профиль",         # Yes, delete profile
        "Нет, оставить профиль",       # No, keep profile
        "назад",                         # back
        "Шаг 01/03",                    # Step 01/03
        "ВЫ ОТОБРАНЫ ДЛЯ ОСОБОГО ЗАДАНИЯ.", # YOU HAVE BEEN SELECTED
        # --- NEW checks ---
        "ВЫ ПРИНЯТЫ",                  # YOU HAVE BEEN ACCEPTED
        "ПОЗДРАВЛЯЕМ,",                # CONGRATULATIONS
        "Я готов существенно влиять",  # Terms bullet 1
        "для защиты Нации",            # Terms bullet 2
        "уставу и принципам Управления", # Terms bullet 3
        "Для отписки",                  # Unsubscribe notice
        "Политика конфиденциальности", # Privacy Policy (shortened)
        "БЛАГОДАРИМ",                   # THANK YOU
        "КАНДИДАТОВ В АГЕНТЫ",         # PROSPECTIVE AGENTS
        "Настройки",                    # Settings
    ]
    ok = 0
    for c in checks:
        found = c.encode('utf-8') in data
        status = "ok" if found else "FAIL"
        if not found:
            print(f"  [{status}] {c}")
        else:
            ok += 1
    print(f"  {ok}/{len(checks)} verified OK")

    # Check English remnants for key strings
    print("\nEnglish remnants check:")
    english_checks = [
        "WELCOME, AGENT!",
        "Delete Profile",
        "Volume Sound Effects",
        "PLEASE AGREE TO THE FOLLOWING TERMS",
        "Next step",
        "Previous step",
        "WE PROTECT THE NATION.",
        "Load Episode",
        "AGENT INVESTIGATOR PAIRING",
        "YOU HAVE BEEN ACCEPTED",
        "CONGRATULATIONS,",
        "I am willing to severely",
        "If you wish to unsubscribe",
        "Show Privacy Policy in Browser",
    ]
    remnants = 0
    for c in english_checks:
        found = c.encode('utf-8') in data
        status = "STILL PRESENT" if found else "removed"
        if found:
            print(f"  [{status}] {c}")
            remnants += 1
    if remnants == 0:
        print(f"  All {len(english_checks)} key English strings successfully replaced")
    else:
        print(f"  WARNING: {remnants} English strings still present!")


if __name__ == "__main__":
    main()
