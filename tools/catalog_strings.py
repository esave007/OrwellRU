#!/usr/bin/env python3
"""
Каталогизация ВСЕХ переводимых строк из resources.assets.
Создаёт JSON-файл с path_id, offsets, текстами для перевода.
Фильтрует технические строки (шейдеры, имена ассетов и т.д.).
"""
import os, sys, struct, json, re
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
from pathlib import Path

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")


# Patterns for strings we should NOT translate
SKIP_PATTERNS = [
    r'^TextMeshPro/',        # Shader names
    r'^Stencil ',            # Shader params
    r'^_\w+$',               # Internal field names like _Color
    r'^m_\w+$',              # Unity fields
    r'^[A-Z][a-z]+\.[a-z]+$', # File names
    r'^\w+\.\w+\.\w+$',     # Package names
    r'^image_\w+$',          # Image asset names
    r'^insider_\w+$',        # Internal IDs
    r'^website_\w+$',        # Website IDs
    r'^CHAR_\w+$',           # Character placeholders (but keep their context)
    r'^call_\w+$',           # Call IDs
    r'^data_\w+$',           # Data IDs
    r'^flag_\w+$',           # Flag IDs
    r'^\w+State\s',          # State class names
    r'^\w+Line\s',           # Line class names
    r'^[\w/]+\.tna\b',       # TNA file paths
    r'^[\w/]+\.mp3$',        # Audio files
    r'^www\.\w+',            # Website URLs
    r'^browser\.hist',       # Browser history labels
    r'^UnityEngine\.',       # Unity engine refs
    r'^\d+[A-Z]{2}\d+',     # Booking numbers
]

# Patterns for strings that ARE translatable
TRANSLATE_PATTERNS = [
    r'[A-Z][a-z].*\s[a-z]',  # Sentences
    r'\b(the|The|is|are|was|were|has|have|will|can|could|would|should)\b',  # English words
    r'[.!?]\s*$',             # Ends with punctuation
]

# Known technical prefixes for MonoBehaviour class names
TECH_PREFIXES = [
    "NewChatMessageState", "NewCommentaryState", "NewCommentaryLineState",
    "UpdateProfileState", "UpdateDocumentState", "DocumentViewedState",
    "NewObjectiveState", "ObjectiveSolvedState", "IfElseState",
    "EmptyState", "NewBookmarkState", "ObjectiveReappearedState",
    "UseUpdateStopState", "UseUpdateState", "StopState", "UseUpdateLeafState",
]


def is_technical(text):
    """Check if a string is technical/internal and shouldn't be translated."""
    text = text.strip()
    if not text:
        return True
    if len(text) < 3:
        return True

    for pattern in SKIP_PATTERNS:
        if re.match(pattern, text):
            return True

    # Pure identifiers (camelCase, snake_case, PascalCase without spaces)
    if re.match(r'^[a-zA-Z_]\w*$', text) and len(text) < 40:
        return True

    # All caps identifier
    if re.match(r'^[A-Z_]+$', text):
        return True

    # Asset paths
    if '/' in text and not ' ' in text:
        return True

    return False


def is_translatable(text):
    """Check if a string contains actual translatable English text."""
    text = text.strip()
    if len(text) < 4:
        return False

    # Must contain English words
    if not re.search(r'[a-zA-Z]{3,}', text):
        return False

    # Skip if it's all technical
    if is_technical(text):
        return False

    return True


def categorize(text):
    """Categorize a string for translation context."""
    t = text.strip()

    # UI/Menu
    if len(t) < 30:
        ui_words = ["save", "load", "quit", "continue", "start", "back", "menu",
                    "settings", "options", "yes", "no", "ok", "cancel", "exit",
                    "new game", "episode", "play"]
        if any(w in t.lower() for w in ui_words):
            return "ui"

    # Dialogue/Chat
    if "\n" in t and "CHAR_" in t:
        return "dialogue"

    # Commentary (handler/adviser speaking)
    if len(t) > 30 and any(x in t for x in ["CHAR_AMPLE", "CHAR_INTERVENTION"]):
        return "commentary"

    # News articles
    if any(x in t for x in ["National Beholder", "People's Voice", ".tna", "beholder"]):
        return "article"

    # Documents
    if any(x in t.lower() for x in ["e-ticket", "booking", "immigration",
                                      "therapy", "report", "certificate",
                                      "Trans-National Express"]):
        return "document"

    # Objectives/Tasks
    if any(x in t for x in ["objective", "Datachunk", "Update:", "Commentary:",
                              "Document", "Flag:", "Bookmark"]):
        return "task"

    # Chat messages (short dialogue lines)
    if len(t) < 200 and re.search(r'[.!?]', t):
        return "dialogue"

    # Long text
    if len(t) > 200:
        return "long_text"

    return "other"


def extract_strings_from_object(raw, min_length=3):
    """Extract all length-prefixed strings from MonoBehaviour raw data."""
    strings = []
    i = 0
    while i < len(raw) - 4:
        str_len = struct.unpack_from('<I', raw, i)[0]
        if min_length <= str_len <= 50000 and i + 4 + str_len <= len(raw):
            try:
                s = raw[i+4:i+4+str_len].decode('utf-8')
                printable_ratio = sum(1 for c in s if c.isprintable() or c in '\n\r\t') / max(len(s), 1)
                if printable_ratio > 0.8:
                    padding = (4 - (str_len % 4)) % 4
                    strings.append({
                        "offset": i,
                        "byte_length": str_len,
                        "padding": padding,
                        "total_bytes": 4 + str_len + padding,
                        "text": s,
                    })
                    i += 4 + str_len + padding
                    continue
            except (UnicodeDecodeError, ValueError):
                pass
        i += 1
    return strings


def main():
    print("=" * 60)
    print("STRING CATALOGING: resources.assets")
    print("=" * 60)

    env = UnityPy.load(str(GAME_DATA / "resources.assets"))

    translatable = []  # Strings to translate
    technical = []     # Technical strings (skipped)

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue

        raw = obj.get_raw_data()
        strings = extract_strings_from_object(raw)

        for s in strings:
            text = s["text"]
            if is_translatable(text):
                cat = categorize(text)
                entry = {
                    "id": f"{obj.path_id}_{s['offset']}",
                    "path_id": obj.path_id,
                    "offset": s["offset"],
                    "byte_length": s["byte_length"],
                    "padding": s["padding"],
                    "category": cat,
                    "original": text,
                    "translation": "",  # To be filled
                }
                translatable.append(entry)
            else:
                technical.append({
                    "path_id": obj.path_id,
                    "offset": s["offset"],
                    "text": text[:100]
                })

    # Deduplicate by text (keep first occurrence, note duplicates)
    seen_texts = {}
    unique = []
    duplicates = []
    for entry in translatable:
        text = entry["original"]
        if text in seen_texts:
            duplicates.append(entry)
            seen_texts[text]["duplicate_ids"] = seen_texts[text].get("duplicate_ids", [])
            seen_texts[text]["duplicate_ids"].append(entry["id"])
        else:
            seen_texts[text] = entry
            unique.append(entry)

    # Stats
    categories = {}
    for e in unique:
        cat = e["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nTotal strings found: {len(translatable)}")
    print(f"Unique strings: {len(unique)}")
    print(f"Duplicates: {len(duplicates)}")
    print(f"Technical (skipped): {len(technical)}")
    print(f"\nBy category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Save
    out_dir = PROJECT / "originals"

    # Full catalog (for import back)
    with open(out_dir / "translation_catalog.json", "w", encoding="utf-8") as f:
        json.dump(translatable, f, ensure_ascii=False, indent=2)

    # Unique strings for translation
    with open(out_dir / "unique_strings.json", "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    # By category for batch translation
    for cat in categories:
        cat_strings = [e for e in unique if e["category"] == cat]
        with open(out_dir / f"strings_{cat}.json", "w", encoding="utf-8") as f:
            json.dump(cat_strings, f, ensure_ascii=False, indent=2)
        print(f"  Saved strings_{cat}.json: {len(cat_strings)} entries")

    # Technical strings (for reference)
    with open(out_dir / "technical_strings.json", "w", encoding="utf-8") as f:
        json.dump(technical[:500], f, ensure_ascii=False, indent=2)

    # Human-readable overview
    with open(out_dir / "translation_overview.txt", "w", encoding="utf-8") as f:
        f.write(f"Translation Catalog Overview\n{'='*60}\n\n")
        f.write(f"Total: {len(translatable)} | Unique: {len(unique)} | Duplicates: {len(duplicates)}\n\n")
        for cat in sorted(categories.keys()):
            f.write(f"\n--- {cat.upper()} ({categories[cat]} strings) ---\n\n")
            cat_strings = [e for e in unique if e["category"] == cat]
            for e in cat_strings[:30]:
                preview = e["original"][:120].replace('\n', '\\n').replace('\r', '\\r')
                f.write(f"  [{e['id']}] {preview}\n")
            if len(cat_strings) > 30:
                f.write(f"  ... and {len(cat_strings) - 30} more\n")

    print(f"\nFiles saved to {out_dir}/")
    print("Ready for translation phase!")


if __name__ == "__main__":
    main()
