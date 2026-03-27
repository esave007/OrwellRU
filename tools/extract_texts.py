#!/usr/bin/env python3
"""
Полная экстракция текстов из Orwell: Ignorance is Strength.
1. SmartLocalization ResX XML из TextAssets
2. Все строки из MonoBehaviours (raw byte parsing)
"""
import os, sys, json, re, struct, xml.etree.ElementTree as ET
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
from pathlib import Path

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")
ORIGINALS = PROJECT / "originals"


def extract_smartlocalization():
    """Extract SmartLocalization ResX XML from TextAssets."""
    res_path = GAME_DATA / "resources.assets"
    env = UnityPy.load(str(res_path))

    smartloc_dir = ORIGINALS / "smartloc"
    smartloc_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            data = obj.read()
            name = data.m_Name
            raw = data.m_Script
            if isinstance(raw, bytes):
                text = raw.decode('utf-8', errors='replace')
            else:
                text = str(raw)

            # Save raw XML
            ext = ".xml" if text.strip().startswith("<?xml") or text.strip().startswith("<!--") else ".txt"
            out_file = smartloc_dir / f"{name}{ext}"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(text)

            # Parse if it's ResX XML with data entries
            if "<data " in text:
                try:
                    root = ET.fromstring(text)
                    entries = {}
                    for data_elem in root.findall(".//data"):
                        key = data_elem.get("name", "")
                        value_elem = data_elem.find("value")
                        value = value_elem.text if value_elem is not None and value_elem.text else ""
                        entries[key] = value
                    results[name] = {
                        "path_id": obj.path_id,
                        "entries": entries,
                        "entry_count": len(entries)
                    }
                    print(f"  [SmartLoc] {name}: {len(entries)} entries (path_id={obj.path_id})")
                except ET.ParseError as e:
                    print(f"  [SmartLoc] {name}: XML parse error: {e}")
            else:
                print(f"  [TextAsset] {name}: {len(text)} chars (path_id={obj.path_id})")

    # Save parsed entries
    with open(smartloc_dir / "smartloc_parsed.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


def extract_strings_from_raw(raw_data, min_length=4):
    """Extract readable strings from raw bytes with their offsets."""
    strings = []
    i = 0
    while i < len(raw_data) - 4:
        # Unity strings are typically length-prefixed (4 bytes LE int + chars)
        # Try to read a length-prefixed string
        try:
            str_len = struct.unpack_from('<I', raw_data, i)[0]
            if 4 <= str_len <= 10000 and i + 4 + str_len <= len(raw_data):
                try:
                    s = raw_data[i+4:i+4+str_len].decode('utf-8')
                    # Check if it's mostly printable
                    printable_ratio = sum(1 for c in s if c.isprintable() or c in '\n\r\t') / len(s)
                    if printable_ratio > 0.85 and len(s.strip()) >= min_length:
                        # Check if it has actual words (not just binary garbage)
                        if re.search(r'[a-zA-Z]{2,}', s) or re.search(r'[\u0400-\u04FF]{2,}', s):
                            strings.append({
                                "offset": i,
                                "length": str_len,
                                "text": s
                            })
                            i += 4 + str_len
                            # Align to 4 bytes
                            padding = (4 - (str_len % 4)) % 4
                            i += padding
                            continue
                except (UnicodeDecodeError, ValueError):
                    pass
        except struct.error:
            pass
        i += 1

    return strings


def extract_monobehaviour_texts():
    """Extract all text from MonoBehaviours in resources.assets."""
    res_path = GAME_DATA / "resources.assets"
    env = UnityPy.load(str(res_path))

    all_objects = []
    text_objects = []

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue

        raw = obj.get_raw_data()
        strings = extract_strings_from_raw(raw, min_length=3)

        if not strings:
            continue

        # Filter: keep objects that have meaningful English text
        meaningful_strings = [s for s in strings
                            if len(s["text"].strip()) >= 3
                            and re.search(r'[a-zA-Z]{3,}', s["text"])]

        if meaningful_strings:
            entry = {
                "path_id": obj.path_id,
                "raw_size": len(raw),
                "string_count": len(meaningful_strings),
                "strings": meaningful_strings
            }
            text_objects.append(entry)

    print(f"  Total MonoBehaviours with text: {len(text_objects)}")
    return text_objects


def extract_monobehaviour_texts_sharedassets3():
    """Extract text from MonoBehaviours in sharedassets3.assets."""
    sa_path = GAME_DATA / "sharedassets3.assets"
    env = UnityPy.load(str(sa_path))

    text_objects = []
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue

        raw = obj.get_raw_data()
        strings = extract_strings_from_raw(raw, min_length=3)

        meaningful = [s for s in strings
                     if len(s["text"].strip()) >= 3
                     and re.search(r'[a-zA-Z]{3,}', s["text"])]

        if meaningful:
            text_objects.append({
                "path_id": obj.path_id,
                "raw_size": len(raw),
                "string_count": len(meaningful),
                "strings": meaningful
            })

    print(f"  Total MonoBehaviours with text in sharedassets3: {len(text_objects)}")
    return text_objects


def categorize_string(text):
    """Categorize a string by context."""
    text_lower = text.lower().strip()

    # UI elements
    if len(text) < 30 and any(kw in text_lower for kw in
        ["save", "load", "quit", "continue", "new game", "settings",
         "options", "back", "cancel", "ok", "yes", "no", "confirm",
         "episode", "chapter", "menu", "play", "start", "exit"]):
        return "UI"

    # Objectives / tasks
    if any(kw in text_lower for kw in
        ["objective", "datachunk", "update:", "commentary:", "new objective",
         "document updated", "flag:", "bookmark"]):
        return "TASK"

    # Character dialogue / chat
    if "CHAR_" in text or "call_" in text_lower:
        return "DIALOGUE"

    # Articles / news
    if any(kw in text for kw in
        ["National Beholder", "People's Voice", "Beholder", ".tna"]):
        return "ARTICLE"

    # Documents
    if any(kw in text_lower for kw in
        ["immigration", "therapy", "report", "e-ticket", "database",
         "booking", "certificate"]):
        return "DOCUMENT"

    # Long text = likely article or document
    if len(text) > 200:
        return "LONG_TEXT"

    # System / internal
    if text.startswith("INGAMEMENU") or text.startswith("MAINMENU") or text.startswith("PROFILER"):
        return "SYSTEM_KEY"

    return "OTHER"


def main():
    print("=" * 60)
    print("EXTRACTION: Orwell Ignorance is Strength")
    print("=" * 60)

    # 1. SmartLocalization
    print("\n--- SmartLocalization (TextAssets) ---")
    smartloc = extract_smartlocalization()

    # Count total SmartLoc entries
    total_smartloc = sum(v["entry_count"] for v in smartloc.values())
    print(f"  Total SmartLocalization entries: {total_smartloc}")

    # 2. MonoBehaviours from resources.assets
    print("\n--- MonoBehaviour texts (resources.assets) ---")
    resources_texts = extract_monobehaviour_texts()

    # Save
    with open(ORIGINALS / "assets" / "resources_monobehaviours.json", "w", encoding="utf-8") as f:
        json.dump(resources_texts, f, ensure_ascii=False, indent=2)

    # 3. MonoBehaviours from sharedassets3.assets
    print("\n--- MonoBehaviour texts (sharedassets3.assets) ---")
    sa3_texts = extract_monobehaviour_texts_sharedassets3()

    with open(ORIGINALS / "assets" / "sharedassets3_monobehaviours.json", "w", encoding="utf-8") as f:
        json.dump(sa3_texts, f, ensure_ascii=False, indent=2)

    # 4. Summary and categorization
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Flatten all strings
    all_strings = []
    for obj in resources_texts:
        for s in obj["strings"]:
            s["source"] = "resources.assets"
            s["source_path_id"] = obj["path_id"]
            s["category"] = categorize_string(s["text"])
            all_strings.append(s)

    for obj in sa3_texts:
        for s in obj["strings"]:
            s["source"] = "sharedassets3.assets"
            s["source_path_id"] = obj["path_id"]
            s["category"] = categorize_string(s["text"])
            all_strings.append(s)

    # Stats
    categories = {}
    for s in all_strings:
        cat = s["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nTotal strings extracted: {len(all_strings)}")
    print(f"SmartLocalization entries: {total_smartloc}")
    print(f"\nBy category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Save complete inventory
    with open(ORIGINALS / "all_strings_inventory.json", "w", encoding="utf-8") as f:
        json.dump(all_strings, f, ensure_ascii=False, indent=2)

    # Save human-readable inventory
    with open(ORIGINALS / "inventory.txt", "w", encoding="utf-8") as f:
        f.write(f"Orwell: Ignorance is Strength - Text Inventory\n")
        f.write(f"{'=' * 60}\n\n")
        f.write(f"Total strings: {len(all_strings)}\n")
        f.write(f"SmartLocalization entries: {total_smartloc}\n\n")
        f.write(f"By category:\n")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            f.write(f"  {cat}: {count}\n")
        f.write(f"\n{'=' * 60}\n\n")

        for cat in sorted(categories.keys()):
            f.write(f"\n--- {cat} ---\n\n")
            cat_strings = [s for s in all_strings if s["category"] == cat]
            for s in cat_strings[:50]:  # First 50 per category
                preview = s["text"][:120].replace('\n', '\\n').replace('\r', '\\r')
                f.write(f"  [{s['source']}:{s['source_path_id']}] {preview}\n")
            if len(cat_strings) > 50:
                f.write(f"  ... and {len(cat_strings) - 50} more\n")

    print(f"\nFiles saved:")
    print(f"  originals/smartloc/ - SmartLocalization XML files")
    print(f"  originals/assets/resources_monobehaviours.json")
    print(f"  originals/assets/sharedassets3_monobehaviours.json")
    print(f"  originals/all_strings_inventory.json")
    print(f"  originals/inventory.txt")


if __name__ == "__main__":
    main()
