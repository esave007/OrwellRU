#!/usr/bin/env python3
"""
Экстракция всех текстов из Orwell: Ignorance is Strength.
Извлекает тексты из:
1. resources.assets (SmartLocalization)
2. sharedassets*.assets (TextMeshPro)
3. AssetBundles/PCIGN/* (TextMeshPro в бандлах)
4. Assembly-CSharp.dll (хардкод-строки) — отдельный скрипт
"""

import json
import os
import sys
import UnityPy
from pathlib import Path

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")
PROJECT = Path(r"C:\Projects\OrwellRU")
ORIGINALS = PROJECT / "originals"


def extract_monobehaviours(env, source_name):
    """Извлечь все MonoBehaviour с текстовыми полями из UnityPy environment."""
    results = []
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                tree = data.read_typetree()
                if tree is None:
                    continue
                # Ищем поля с текстом
                text_fields = {}
                for key, value in tree.items():
                    if isinstance(value, str) and len(value) > 1:
                        text_fields[key] = value
                if text_fields:
                    results.append({
                        "source": source_name,
                        "path_id": obj.path_id,
                        "type": "MonoBehaviour",
                        "class_name": tree.get("m_Name", ""),
                        "fields": text_fields,
                        "full_tree_keys": list(tree.keys())
                    })
            except Exception as e:
                # Некоторые MonoBehaviour не имеют typetree
                pass

    return results


def extract_textmeshpro(env, source_name):
    """Извлечь все TextMeshProUGUI объекты."""
    results = []
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                tree = data.read_typetree()
                if tree is None:
                    continue
                # TextMeshProUGUI имеет поле m_text
                if "m_text" in tree and isinstance(tree["m_text"], str):
                    m_text = tree["m_text"]
                    if len(m_text.strip()) > 0:
                        results.append({
                            "source": source_name,
                            "path_id": obj.path_id,
                            "type": "TextMeshProUGUI",
                            "m_Name": tree.get("m_Name", ""),
                            "m_text": m_text,
                            "m_text_length": len(m_text),
                        })
            except Exception:
                pass
    return results


def extract_from_assets():
    """Извлечь тексты из sharedassets*.assets и resources.assets."""
    all_texts = []

    # resources.assets
    res_path = GAME_DATA / "resources.assets"
    if res_path.exists():
        print(f"[*] Loading {res_path.name}...")
        env = UnityPy.load(str(res_path))
        monos = extract_monobehaviours(env, "resources.assets")
        tmps = extract_textmeshpro(env, "resources.assets")
        all_texts.extend(monos)
        all_texts.extend(tmps)
        print(f"    MonoBehaviours with text: {len(monos)}, TextMeshPro: {len(tmps)}")

    # sharedassets
    for i in range(5):
        sa_path = GAME_DATA / f"sharedassets{i}.assets"
        if sa_path.exists():
            print(f"[*] Loading {sa_path.name}...")
            env = UnityPy.load(str(sa_path))
            monos = extract_monobehaviours(env, f"sharedassets{i}.assets")
            tmps = extract_textmeshpro(env, f"sharedassets{i}.assets")
            all_texts.extend(monos)
            all_texts.extend(tmps)
            print(f"    MonoBehaviours with text: {len(monos)}, TextMeshPro: {len(tmps)}")

    return all_texts


def extract_from_bundles():
    """Извлечь тексты из всех AssetBundles."""
    bundles_dir = GAME_DATA / "AssetBundles" / "PCIGN"
    all_texts = []

    if not bundles_dir.exists():
        print("[!] AssetBundles directory not found")
        return all_texts

    bundle_files = sorted(bundles_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0)

    for bundle_path in bundle_files:
        if bundle_path.is_file():
            print(f"[*] Loading bundle {bundle_path.name}...")
            try:
                env = UnityPy.load(str(bundle_path))
                tmps = extract_textmeshpro(env, f"bundle_{bundle_path.name}")
                monos = extract_monobehaviours(env, f"bundle_{bundle_path.name}")
                all_texts.extend(tmps)
                all_texts.extend(monos)
                print(f"    TextMeshPro: {len(tmps)}, MonoBehaviours with text: {len(monos)}")
            except Exception as e:
                print(f"    [ERROR] {e}")

    return all_texts


def main():
    print("=" * 60)
    print("ЭКСТРАКЦИЯ ТЕКСТОВ: Orwell: Ignorance is Strength")
    print("=" * 60)

    # 1. Assets
    print("\n--- ASSETS ---")
    assets_texts = extract_from_assets()

    # Save assets texts
    out_assets = ORIGINALS / "assets" / "all_assets_texts.json"
    with open(out_assets, "w", encoding="utf-8") as f:
        json.dump(assets_texts, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Assets: {len(assets_texts)} items → {out_assets}")

    # 2. Bundles
    print("\n--- ASSET BUNDLES ---")
    bundle_texts = extract_from_bundles()

    # Save bundle texts
    out_bundles = ORIGINALS / "bundles" / "all_bundle_texts.json"
    with open(out_bundles, "w", encoding="utf-8") as f:
        json.dump(bundle_texts, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Bundles: {len(bundle_texts)} items → {out_bundles}")

    # Summary
    print("\n" + "=" * 60)
    print("ИТОГО:")
    print(f"  Assets: {len(assets_texts)} текстовых объектов")
    print(f"  Bundles: {len(bundle_texts)} текстовых объектов")
    print(f"  ВСЕГО: {len(assets_texts) + len(bundle_texts)}")
    print("=" * 60)

    # Detailed breakdown by source
    sources = {}
    for item in assets_texts + bundle_texts:
        src = item["source"]
        sources[src] = sources.get(src, 0) + 1

    print("\nПо источникам:")
    for src, count in sorted(sources.items()):
        print(f"  {src}: {count}")


if __name__ == "__main__":
    main()
