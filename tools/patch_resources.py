#!/usr/bin/env python3
"""
Direct binary patcher for resources.assets MonoBehaviour strings.
Uses same-size replacement with space padding for shorter translations
and truncation warnings for longer ones.
"""
import os, sys, struct, json
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path

PROJECT = Path(r"C:\Projects\OrwellRU")


def find_all_strings(data, min_length=3):
    """Find all length-prefixed UTF-8 strings in binary data."""
    strings = []
    i = 0
    while i < len(data) - 4:
        str_len = struct.unpack_from('<I', data, i)[0]
        if min_length <= str_len <= 50000 and i + 4 + str_len <= len(data):
            try:
                s = data[i+4:i+4+str_len].decode('utf-8')
                printable = sum(1 for c in s if c.isprintable() or c in '\n\r\t') / max(len(s), 1)
                if printable > 0.8:
                    padding = (4 - (str_len % 4)) % 4
                    strings.append({
                        'offset': i,
                        'byte_length': str_len,
                        'padding': padding,
                        'text': s,
                    })
                    i += 4 + str_len + padding
                    continue
            except (UnicodeDecodeError, ValueError):
                pass
        i += 1
    return strings


def apply_translations_binary(input_path, output_path, translations):
    """
    Apply translations via direct binary patching.
    translations: dict of {original_text: russian_text}

    Strategy:
    - If Russian text bytes <= original bytes: pad with spaces
    - If Russian text bytes > original bytes: log warning, skip or truncate
    """
    with open(input_path, 'rb') as f:
        data = bytearray(f.read())

    applied = 0
    skipped = 0
    too_long = []

    for original, russian in translations.items():
        if not russian or russian == original:
            continue

        orig_bytes = original.encode('utf-8')
        ru_bytes = russian.encode('utf-8')
        prefix = struct.pack('<I', len(orig_bytes))
        needle = prefix + orig_bytes

        # Find all occurrences
        start = 0
        positions = []
        while True:
            pos = data.find(needle, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1

        if not positions:
            continue

        if len(ru_bytes) <= len(orig_bytes):
            # Pad with spaces
            padded = ru_bytes + b' ' * (len(orig_bytes) - len(ru_bytes))
            for pos in positions:
                data[pos+4:pos+4+len(orig_bytes)] = padded
                applied += 1
        else:
            # Too long - log and skip
            too_long.append({
                'original': original[:60],
                'russian': russian[:60],
                'orig_bytes': len(orig_bytes),
                'ru_bytes': len(ru_bytes),
                'diff': len(ru_bytes) - len(orig_bytes),
            })
            skipped += len(positions)

    # Write output
    with open(output_path, 'wb') as f:
        f.write(data)

    return applied, skipped, too_long


def main():
    print("=" * 60)
    print("BINARY PATCHER: resources.assets MonoBehaviour strings")
    print("=" * 60)

    # Test with a small batch of translations
    test_translations = {
        # Commentary/dialogue - handler speaking
        "Orwell was designed in such way that not one person alone can look at the documents and interpret the data to make a judgement call.":
            "Orwell устроен так, что ни один человек не может в одиночку просматривать документы и интерпретировать данные для принятия решения.",

        "Every operator is controlled by a handler.":
            "Каждый оператор контролируется куратором.",

        # Simple UI-like strings
        "Unknown Person": "Неизвестная личность",

        # Task/objective names
        "New objective: Motive": "Новое задание: Мотив",
        "New objective: Way of contact": "Новое задание: Способ связи",
        "Objective solved: Main objective": "Задание выполнено: Основное задание",

        # Datachunk labels
        "Datachunk: Task Safer Nation": "Блок данных: Задание Безопасная Нация",
        "Update: Task Safer Nation": "Обновление: Задание Безопасная Нация",
        "Update: Task Dickmove": "Обновление: Задание Подлость",
    }

    input_path = r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data\resources.assets"
    output_path = PROJECT / "patches" / "resources_patched.assets"

    applied, skipped, too_long = apply_translations_binary(
        input_path, output_path, test_translations
    )

    print(f"\nResults:")
    print(f"  Applied: {applied} replacements")
    print(f"  Skipped (too long): {skipped}")

    if too_long:
        print(f"\n  Translations too long ({len(too_long)}):")
        for t in too_long:
            print(f"    '{t['original']}' -> '{t['russian']}'")
            print(f"      {t['orig_bytes']} -> {t['ru_bytes']} bytes (+{t['diff']})")

    # Verify
    print(f"\n  File sizes: input={os.path.getsize(input_path)}, output={os.path.getsize(str(output_path))}")

    # Check Russian text in output
    with open(output_path, 'rb') as f:
        content = f.read()

    checks = ["Orwell устроен", "Неизвестная личность", "Новое задание"]
    for c in checks:
        if c.encode('utf-8') in content:
            print(f"  Verify '{c}': OK")
        else:
            print(f"  Verify '{c}': NOT FOUND")


if __name__ == "__main__":
    main()
