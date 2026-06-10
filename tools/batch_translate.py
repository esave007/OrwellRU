#!/usr/bin/env python3
"""
Batch translate strings and save to translation template.
Processes a JSON batch file with {original: translation} pairs
and updates the translation_template.json.
"""
import os, sys, json
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
PROJECT = Path(r"C:\Projects\OrwellRU")


def apply_batch(batch_file, template_file):
    """Apply batch translations to template."""
    with open(batch_file, 'r', encoding='utf-8') as f:
        batch = json.load(f)

    with open(template_file, 'r', encoding='utf-8') as f:
        template = json.load(f)

    # Build lookup
    applied = 0
    for entry in template:
        orig = entry['original']
        if orig in batch and batch[orig]:
            entry['translation'] = batch[orig]
            applied += 1

    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    print(f"Applied {applied} translations out of {len(batch)} in batch")

    # Stats
    total = len(template)
    translated = sum(1 for e in template if e.get('translation'))
    print(f"Template: {translated}/{total} translated ({translated*100//total}%)")

    return applied


if __name__ == "__main__":
    batch_file = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT / "translated" / "batch_01.json")
    template_file = str(PROJECT / "translated" / "translation_template.json")
    apply_batch(batch_file, template_file)
