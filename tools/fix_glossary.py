#!/usr/bin/env python3
"""Auto-fix glossary issues in all batch_level3_*.json files.
Fixes: dates without г., Safety Bill, лайк terminology.
Run after receiving new batch files from translation agents."""
import json, re, sys, glob, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

PROJECT = 'C:/Projects/OrwellRU'

def fix_batch(filepath):
    """Fix glossary issues in a batch file. Returns (fixes_count, entries_count)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fixes = 0
    new_data = {}
    for k, v in data.items():
        new_v = v

        # 1. Fix dates without г.
        new_v = re.sub(
            r'((?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})(?!\s*г\.)',
            r'\1 г.',
            new_v
        )

        # 2. Fix Safety Bill
        new_v = new_v.replace('Закон о безопасности', 'Пакет мер безопасности')

        # 3. Fix лайк → отметок «Нравится» (in counter contexts)
        # "N лайков" → "N отметок «Нравится»"
        new_v = re.sub(r'(\d+)\s+лайков', r'\1 отметок «Нравится»', new_v)
        new_v = re.sub(r'(\d+)\s+лайка', r'\1 отметки «Нравится»', new_v)
        new_v = re.sub(r'(\d+)\s+лайк(?!\w)', r'\1 отметка «Нравится»', new_v)
        # Label "Лайки:" → "Отметки «Нравится»:"
        new_v = new_v.replace('Лайки:', 'Отметки «Нравится»:')

        if new_v != v:
            fixes += 1
        new_data[k] = new_v

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    return fixes, len(data)


if __name__ == '__main__':
    print("=" * 60)
    print("GLOSSARY FIX: Auto-correcting all batch files")
    print("=" * 60)

    total_fixes = 0
    for fpath in sorted(glob.glob(f'{PROJECT}/translated/batch_level3_*.json')):
        fname = os.path.basename(fpath)
        fixes, entries = fix_batch(fpath)
        status = f"{fixes} fixes" if fixes > 0 else "clean"
        print(f"  {fname}: {entries} entries, {status}")
        total_fixes += fixes

    print(f"\nTotal fixes: {total_fixes}")
