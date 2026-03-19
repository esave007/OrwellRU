#!/usr/bin/env python3
"""Find untranslated strings from level3_clean_strings.json."""

import json
import re
import os

PROJECT = "C:/Projects/OrwellRU"

BATCH_FILES = [
    os.path.join(PROJECT, "translated", "batch_level3_01.json"),
    os.path.join(PROJECT, "translated", "batch_level3_03.json"),
    os.path.join(PROJECT, "translated", "batch_level3_auto.json"),
]

SOURCE_FILE = os.path.join(PROJECT, "originals", "level3_clean_strings.json")
OUTPUT_FILE = os.path.join(PROJECT, "originals", "level3_untranslated.json")


def is_technical(text: str) -> bool:
    """Filter out technical/non-translatable strings."""
    stripped = text.strip().rstrip('\r\n')

    # Pure numbers (with optional punctuation/spaces)
    if re.match(r'^[\d\s.,:%/$\-+]+$', stripped):
        return True

    # Single character
    if len(stripped) <= 1:
        return True

    # Starts with CAM ID
    if stripped.startswith("CAM ID"):
        return True

    # Just a @username (e.g. "@PeoplesVoice")
    if re.match(r'^@\w+$', stripped):
        return True

    # Technical IDs: purely alphanumeric with underscores, no spaces, looks like an ID
    if re.match(r'^[a-zA-Z0-9_]+$', stripped) and '_' in stripped:
        return True

    # Empty or whitespace only
    if not stripped:
        return True

    return False


def categorize(text: str) -> str:
    length = len(text)
    if length > 200:
        return "long (articles/dialogues)"
    elif length >= 50:
        return "medium"
    else:
        return "short (UI/labels)"


def main():
    # Load all translation keys from batch files
    translated_keys = set()
    for path in BATCH_FILES:
        if not os.path.exists(path):
            print(f"WARNING: batch file not found: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        translated_keys.update(data.keys())
        print(f"Loaded {len(data)} keys from {os.path.basename(path)}")

    print(f"\nTotal unique translation keys: {len(translated_keys)}")

    # Load source strings
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        source = json.load(f)

    print(f"Total strings in level3_clean_strings.json: {len(source)}")

    # Find untranslated
    untranslated_raw = []
    already_translated = 0
    for entry in source:
        text = entry["text"]
        if text in translated_keys:
            already_translated += 1
        else:
            untranslated_raw.append(text)

    print(f"Already translated: {already_translated}")
    print(f"Not in any batch file: {len(untranslated_raw)}")

    # Filter out technical strings
    filtered_out = 0
    untranslated = []
    seen = set()
    for text in untranslated_raw:
        if text in seen:
            continue
        seen.add(text)
        if is_technical(text):
            filtered_out += 1
            continue
        untranslated.append({
            "text": text,
            "length": len(text),
            "category": categorize(text),
        })

    print(f"Filtered out (technical/numbers/IDs): {filtered_out}")
    print(f"Deduplicated untranslated (unique texts): {len(untranslated)}")

    # Sort by category then length
    category_order = {"long (articles/dialogues)": 0, "medium": 1, "short (UI/labels)": 2}
    untranslated.sort(key=lambda x: (category_order.get(x["category"], 9), -x["length"]))

    # Stats by category
    print("\n=== UNTRANSLATED BY CATEGORY ===")
    cats = {}
    for item in untranslated:
        cat = item["category"]
        cats[cat] = cats.get(cat, 0) + 1
    for cat in ["long (articles/dialogues)", "medium", "short (UI/labels)"]:
        print(f"  {cat}: {cats.get(cat, 0)}")
    print(f"  TOTAL: {len(untranslated)}")

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(untranslated, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to: {OUTPUT_FILE}")

    # Print samples
    print("\n=== SAMPLE UNTRANSLATED (first 10) ===")
    for item in untranslated[:10]:
        preview = item["text"][:80].replace('\r', '\\r').replace('\n', '\\n')
        print(f"  [{item['category']}] ({item['length']} chars) {preview}...")


if __name__ == "__main__":
    main()
