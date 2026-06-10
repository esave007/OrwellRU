#!/usr/bin/env python3
"""
Fix all translation consistency issues across batch files.
P0: Circle Mall 4 variants → «Круг», double year suffix "г. года"
P1: FTP abbreviation, паргезский, Бонтонские взрывы→теракты, следователь→дознаватель
P2: МЕДИА-МОНСТРЫ, Левайн→Левин, ТНО→НО, Манипулятор→Инфлюенсер
"""
import json, glob, os
os.environ["PYTHONIOENCODING"] = "utf-8"

PROJECT = r"C:\Projects\OrwellRU"
TRANSLATED = os.path.join(PROJECT, "translated")


# Global replacements (safe everywhere)
GLOBAL_FIXES = [
    # P0: Double year suffix
    ("г. года", "г."),

    # P0: Circle Mall → «Круг»
    ("«Серкл Молл»", "«Круг»"),
    ("«Серкл»", "«Круг»"),

    # P1: паргезский → паргесский (stem covers all declensions)
    ("паргезск", "паргесск"),
    ("Паргезск", "Паргесск"),
    ("ПАРГЕЗСК", "ПАРГЕССК"),

    # P1: Бонтонские взрывы → теракты (all case forms)
    ("бонтонские взрывы", "бонтонские теракты"),
    ("Бонтонские взрывы", "Бонтонские теракты"),
    ("БОНТОНСКИЕ ВЗРЫВЫ", "БОНТОНСКИЕ ТЕРАКТЫ"),
    ("бонтонских взрывов", "бонтонских терактов"),
    ("Бонтонских взрывов", "Бонтонских терактов"),
    ("бонтонским взрывам", "бонтонским терактам"),
    ("бонтонскими взрывами", "бонтонскими терактами"),
    ("бонтонских взрывах", "бонтонских терактах"),
    ("бонтонского взрыва", "бонтонского теракта"),
    ("бонтонском взрыве", "бонтонском теракте"),
    ("бонтонскому взрыву", "бонтонскому теракту"),
    # Also "взрывы в Бонтоне" patterns
    ("взрывов в Бонтоне", "терактов в Бонтоне"),
    ("взрывы в Бонтоне", "теракты в Бонтоне"),
    ("взрыва в Бонтоне", "теракта в Бонтоне"),
    ("взрывах в Бонтоне", "терактах в Бонтоне"),

    # P1: ФТП → СИП (Forces of True Parges)
    ("ФТП", "СИП"),

    # P2: МЕДИА-МОНСТРЫ → МЕДИЙНЫЕ МОНСТРЫ (all case forms)
    ("МЕДИА-МОНСТРЫ", "МЕДИЙНЫЕ МОНСТРЫ"),
    ("МЕДИА-МОНСТРОВ", "МЕДИЙНЫХ МОНСТРОВ"),
    ("МЕДИА-МОНСТРАМИ", "МЕДИЙНЫМИ МОНСТРАМИ"),
    ("МЕДИА-МОНСТРАМ", "МЕДИЙНЫМ МОНСТРАМ"),
    ("медиа-монстры", "медийные монстры"),
    ("медиа-монстров", "медийных монстров"),
    ("медиа-монстрами", "медийными монстрами"),
    ("медиа-монстрам", "медийным монстрам"),
    ("Медиа-монстры", "Медийные монстры"),
    ("Медиа-монстров", "Медийных монстров"),

    # P2: Левайн → Левин (name consistency, majority is Левин)
    ("Левайн", "Левин"),

    # P2: ТНО → НО (abbreviation for Национальный Обозреватель)
    ("ТНО:", "НО:"),
]

# File-specific replacements (context-dependent)
FILE_FIXES = {
    # P1: следователь → дознаватель in resources files (Orwell investigator role)
    "batch_resources_01.json": [
        ("следователь", "дознаватель"),
        ("следователя", "дознавателя"),
        ("следователю", "дознавателю"),
        ("следователем", "дознавателем"),
        ("следователе ", "дознавателе "),
        ("Следователь", "Дознаватель"),
        ("Следователя", "Дознавателя"),
    ],
    "batch_resources_02.json": [
        ("следователь", "дознаватель"),
        ("следователя", "дознавателя"),
        ("следователю", "дознавателю"),
        ("следователем", "дознавателем"),
        ("Следователь", "Дознаватель"),
        ("Мой следователь", "Мой дознаватель"),
    ],
    # P0: «Кольцо» as Circle Mall only in resources files
    "batch_resources_01.json": [
        ("следователь", "дознаватель"),
        ("следователя", "дознавателя"),
        ("следователю", "дознавателю"),
        ("следователем", "дознавателем"),
        ("следователе ", "дознавателе "),
        ("Следователь", "Дознаватель"),
        ("Следователя", "Дознавателя"),
        ("«Кольцо»", "«Круг»"),
        ("ФОС", "СИП"),
    ],
    "batch_resources_02.json": [
        ("следователь", "дознаватель"),
        ("следователя", "дознавателя"),
        ("следователю", "дознавателю"),
        ("следователем", "дознавателем"),
        ("Следователь", "Дознаватель"),
    ],
    # P2: Манипулятор → Инфлюенсер (only the Orwell tool name)
    "batch_level3_06_short.json": [
        ("Манипулятор", "Инфлюенсер"),
        ("манипулятор", "инфлюенсер"),
    ],
}


def apply_fixes(value, filename, stats):
    """Apply all relevant fixes to a translation value."""
    if not value or not isinstance(value, str):
        return value

    original = value

    # Apply global fixes
    for old, new in GLOBAL_FIXES:
        if old in value:
            value = value.replace(old, new)

    # Apply file-specific fixes
    if filename in FILE_FIXES:
        for old, new in FILE_FIXES[filename]:
            if old in value:
                value = value.replace(old, new)

    if value != original:
        stats['fixes'] += 1
        # Track what changed for reporting
        if original != value:
            stats['details'].append(f"  {original[:80]}...")
    return value


def main():
    print("=" * 60)
    print("CONSISTENCY FIXER: All translation batch files")
    print("=" * 60)

    # Collect all batch JSON files
    patterns = [
        os.path.join(TRANSLATED, "batch_level3_*.json"),
        os.path.join(TRANSLATED, "batch_resources_*.json"),
        os.path.join(TRANSLATED, "batch_0*.json"),
    ]
    all_files = []
    for pattern in patterns:
        all_files.extend(sorted(glob.glob(pattern)))

    total_fixes = 0
    files_fixed = 0

    for fpath in all_files:
        fname = os.path.basename(fpath)
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        stats = {'fixes': 0, 'details': []}

        for key in data:
            if data[key] and isinstance(data[key], str):
                data[key] = apply_fixes(data[key], fname, stats)

        if stats['fixes'] > 0:
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n  {fname}: {stats['fixes']} fixes")
            total_fixes += stats['fixes']
            files_fixed += 1

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {total_fixes} fixes in {files_fixed} files")
    print(f"{'=' * 60}")

    # Verification: grep for remaining issues
    print("\nVerification — scanning for remaining issues:")
    remaining = {
        "г. года": 0,
        "«Серкл»": 0,
        "«Серкл Молл»": 0,
        "«Кольцо»": 0,
        "паргезск": 0,
        "ФТП": 0,
        "МЕДИА-МОНСТР": 0,
        "Левайн": 0,
        "ТНО:": 0,
    }
    for fpath in all_files:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        for pattern in remaining:
            remaining[pattern] += content.count(pattern)

    all_clean = True
    for pattern, count in remaining.items():
        status = "CLEAN" if count == 0 else f"REMAINING: {count}"
        if count > 0:
            all_clean = False
        print(f"  {pattern}: {status}")

    if all_clean:
        print("\n  ALL ISSUES FIXED!")
    else:
        print("\n  Some issues remain — may need manual review")


if __name__ == "__main__":
    main()
