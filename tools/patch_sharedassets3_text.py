#!/usr/bin/env python3
"""Patch sharedassets3.assets — UI text strings (Chat, Mail, etc.)."""
import os, sys, json
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile, find_and_replace_strings

PROJECT = Path(r"C:\Projects\OrwellRU")
BACKUP = PROJECT / "backup"

# Load translations
with open(PROJECT / "translated" / "batch_sharedassets3_ui.json", 'r', encoding='utf-8') as f:
    translations = json.load(f)
translations = {k: v for k, v in translations.items() if v and v != k}
print(f"Translations: {len(translations)}")

# Parse from existing patched file (has fonts already)
src = PROJECT / "patches" / "sharedassets3.assets"
if not src.exists():
    src = BACKUP / "sharedassets3.assets"
print(f"Parsing {src}...")
usf = UnitySerializedFile(str(src))
print(f"  Objects: {len(usf.objects)}")

replacements = {}
total = 0
for obj in usf.objects:
    if obj['type_index'] >= len(usf.types):
        continue
    if usf.types[obj['type_index']]['class_id'] != 114:
        continue
    raw = usf.get_object_data(obj['path_id'])
    if not raw or len(raw) < 20:
        continue
    new_raw, count = find_and_replace_strings(raw, translations)
    if count > 0:
        replacements[obj['path_id']] = new_raw
        total += count

print(f"Replacements: {total} in {len(replacements)} objects")
output = PROJECT / "patches" / "sharedassets3.assets"
usf.rebuild_with_replacements(replacements, str(output))
print(f"Saved: {output}")
