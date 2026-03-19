#!/usr/bin/env python3
"""Patch level2 — intro screen (3 strings)."""
import os, sys
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile, find_and_replace_strings

GAME = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")

translations = {
    "Intro playback error. Please check Communityhub.": "Ошибка воспроизведения. Проверьте Communityhub.",
    "Press ESC to skip": "Нажмите ESC для пропуска",
    "Skipping Intro (-noIntro argument is set).": "Пропуск заставки (аргумент -noIntro).",
}

# Backup
src = GAME / "level2"
backup = PROJECT / "backup" / "level2"
if not backup.exists():
    import shutil
    shutil.copy2(str(src), str(backup))
    print(f"Backed up level2")

usf = UnitySerializedFile(str(backup))
print(f"Objects: {len(usf.objects)}")

replacements = {}
total = 0
for obj in usf.objects:
    if obj['type_index'] >= len(usf.types): continue
    if usf.types[obj['type_index']]['class_id'] != 114: continue
    raw = usf.get_object_data(obj['path_id'])
    if not raw or len(raw) < 20: continue
    new_raw, count = find_and_replace_strings(raw, translations)
    if count > 0:
        replacements[obj['path_id']] = new_raw
        total += count

print(f"Replacements: {total} in {len(replacements)} objects")
output = PROJECT / "patches" / "level2"
usf.rebuild_with_replacements(replacements, str(output))
print(f"Saved: {output}")
