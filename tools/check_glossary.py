#!/usr/bin/env python3
"""Check all translation batches for glossary compliance with Orwell 1."""
import json, re, sys, glob, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

PROJECT = 'C:/Projects/OrwellRU'

# Glossary rules (per Orwell 1 official Russian localization)
FORBIDDEN = {
    'лайк': 'Использовать "отметок «Нравится»" (по глоссарию Orwell 1)',
    'Закон о безопасности': 'Использовать "Пакет мер безопасности"',
}

def check_dates(value):
    """Check that dates with years have г. suffix."""
    issues = []
    # Find Russian month + year without г.
    pattern = r'((?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})(?!\s*г\.)'
    matches = re.findall(pattern, value)
    for m in matches:
        issues.append(f'Дата без "г.": "{m}"')
    return issues

def check_batch(filepath):
    """Check a batch file for glossary issues."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fname = os.path.basename(filepath)
    total_issues = 0

    for key, value in data.items():
        if not value:
            continue
        issues = []

        # Check forbidden terms
        for term, msg in FORBIDDEN.items():
            if term.lower() in value.lower():
                issues.append(f'{msg} (нашёл "{term}")')

        # Check dates
        issues.extend(check_dates(value))

        if issues:
            total_issues += len(issues)
            print(f'\n  [{fname}] Key: {key[:60]}...')
            for issue in issues:
                print(f'    ⚠ {issue}')

    return total_issues

# Check all batch files
print("=" * 60)
print("GLOSSARY CHECK: Orwell 1 compliance")
print("=" * 60)

total = 0
for fpath in sorted(glob.glob(f'{PROJECT}/translated/batch_level3_*.json')):
    fname = os.path.basename(fpath)
    issues = check_batch(fpath)
    status = "OK" if issues == 0 else f"{issues} issues"
    print(f'\n{fname}: {status}')
    total += issues

print(f'\n{"=" * 60}')
print(f'Total issues: {total}')
if total == 0:
    print('All batches pass glossary check!')
