#!/usr/bin/env python3
"""
Apply SmartLocalization translation to resources.assets.
Replaces English values in the Language.en and Language TextAsset XMLs.

Pipeline: reads BACKUP via UnityPy for XML modification,
then constructs raw TextAsset bytes and applies via custom binary patcher.
This avoids chaining UnityPy saves (which corrupts MonoBehaviour objects).
"""
import os, sys, json, re, struct
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from unity_serialized_patcher import UnitySerializedFile

PROJECT = Path(r"C:\Projects\OrwellRU")
BACKUP = PROJECT / "backup"


def build_text_asset_raw(name: str, script: str) -> bytes:
    """Build raw TextAsset data: [name_len][name][pad][script_len][script][pad]"""
    name_bytes = name.encode('utf-8')
    script_bytes = script.encode('utf-8')

    data = bytearray()
    # Name
    data += struct.pack('<I', len(name_bytes))
    data += name_bytes
    data += b'\x00' * ((4 - len(name_bytes) % 4) % 4)
    # Script
    data += struct.pack('<I', len(script_bytes))
    data += script_bytes
    data += b'\x00' * ((4 - len(script_bytes) % 4) % 4)

    return bytes(data)


def main():
    print("=" * 60)
    print("APPLYING SmartLocalization TRANSLATION")
    print("=" * 60)

    # Load translations
    with open(PROJECT / "translated" / "smartloc" / "smartloc_ru.json", encoding="utf-8") as f:
        translations = json.load(f)

    print(f"Loaded {len(translations)} translation entries")

    # Use UnityPy to READ backup TextAssets and modify XML in memory
    print(f"\nReading BACKUP with UnityPy...")
    env = UnityPy.load(str(BACKUP / "resources.assets"))

    replacements = {}  # {path_id: new_raw_bytes}

    for asset_name in ["Language.en", "Language"]:
        print(f"\n--- {asset_name} ---")
        for obj in env.objects:
            if obj.type.name != "TextAsset":
                continue
            data = obj.read()
            if data.m_Name != asset_name:
                continue

            text = data.m_Script
            count = 0
            for key, russian in translations.items():
                if not russian:
                    continue
                pattern = rf'(<data name="{re.escape(key)}"[^>]*>\s*<value>)(.*?)(</value>)'
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    old_value = match.group(2)
                    if old_value and old_value != russian:
                        text = text[:match.start(2)] + russian + text[match.end(2):]
                        count += 1

            if count > 0:
                raw = build_text_asset_raw(data.m_Name, text)
                replacements[obj.path_id] = raw
                print(f"  {count} replacements, raw={len(raw)} bytes")
            break

    if not replacements:
        print("No SmartLoc changes to apply!")
        return

    # Apply via custom binary patcher
    src_path = PROJECT / "patches" / "resources.assets"
    if not src_path.exists():
        src_path = BACKUP / "resources.assets"
    print(f"\nApplying via custom patcher to {src_path}...")

    usf = UnitySerializedFile(str(src_path))
    out_path = PROJECT / "patches" / "resources.assets"
    usf.rebuild_with_replacements(replacements, str(out_path))

    print(f"Saved: {out_path} ({os.path.getsize(str(out_path))} bytes)")

    # Verify
    print("\n--- Verification ---")
    with open(out_path, 'rb') as f:
        raw = f.read()
    checks = ["Новая игра", "Меню", "Сохранить", "Загрузить", "Профиль", "Связи", "Закладки"]
    ok = sum(1 for c in checks if c.encode('utf-8') in raw)
    print(f"  {ok}/{len(checks)} verified OK")


if __name__ == "__main__":
    main()
