#!/usr/bin/env python3
"""Inspect all bundles + read TextAsset properly."""
import os, sys
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
from pathlib import Path
from collections import Counter

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")


def inspect_all_bundles():
    """Check ALL 32 bundles for text content."""
    bundles_dir = GAME_DATA / "AssetBundles" / "PCIGN"
    bundle_files = sorted(bundles_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0)

    total_types = Counter()
    bundles_with_mono = []

    for bf in bundle_files:
        env = UnityPy.load(str(bf))
        types = Counter()
        for obj in env.objects:
            types[obj.type.name] += 1
            total_types[obj.type.name] += 1

        has_mono = types.get("MonoBehaviour", 0)
        has_text = types.get("TextAsset", 0)
        if has_mono or has_text:
            bundles_with_mono.append((bf.name, dict(types)))
            print(f"Bundle {bf.name}: MonoBehaviour={has_mono}, TextAsset={has_text}, total types={dict(types)}")

    print(f"\nTotal across all bundles:")
    for t, c in total_types.most_common():
        print(f"  {t}: {c}")

    print(f"\nBundles with MonoBehaviour or TextAsset: {len(bundles_with_mono)}")
    return bundles_with_mono


def read_textassets():
    """Read TextAsset objects from resources.assets."""
    res_path = GAME_DATA / "resources.assets"
    env = UnityPy.load(str(res_path))

    print("\n=== TextAsset objects in resources.assets ===")
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            try:
                data = obj.read()
                name = data.m_Name if hasattr(data, 'm_Name') else "?"
                # Try different ways to get text
                text = None
                if hasattr(data, 'm_Script'):
                    raw = data.m_Script
                    if isinstance(raw, bytes):
                        text = raw.decode('utf-8', errors='replace')
                    else:
                        text = str(raw)
                elif hasattr(data, 'text'):
                    text = data.text

                if text:
                    preview = text[:200].replace('\n', '\\n')
                    print(f"\n  [{name}] (path_id={obj.path_id}, {len(text)} chars)")
                    print(f"    {preview}")
                else:
                    print(f"\n  [{name}] (path_id={obj.path_id}) - no text found")
                    print(f"    attrs: {[a for a in dir(data) if not a.startswith('_')]}")
            except Exception as e:
                print(f"  [TextAsset ERROR] path_id={obj.path_id}: {e}")


def read_monobehaviours_raw():
    """Try to read MonoBehaviour raw bytes from resources.assets to find SmartLocalization."""
    res_path = GAME_DATA / "resources.assets"
    env = UnityPy.load(str(res_path))

    print("\n=== MonoBehaviour raw scan in resources.assets (first 20) ===")
    count = 0
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour" and count < 20:
            try:
                raw = obj.get_raw_data()
                # Look for readable ASCII strings
                text = raw.decode('utf-8', errors='replace')
                # Check if it contains known SmartLocalization keys
                if any(key in text for key in ["MAINMENU", "INGAMEMENU", "SmartLocalization",
                                                  "PROFILER", "LISTENER", "WE PROTECT"]):
                    preview = text[:300].replace('\n', '\\n').replace('\r', '\\r')
                    print(f"\n  [MonoBehaviour path_id={obj.path_id}] MATCH! ({len(raw)} bytes)")
                    print(f"    {preview}")
                    count += 1
            except Exception as e:
                pass

    # Also scan for any english text in all MonoBehaviours
    print("\n=== Scanning ALL MonoBehaviours for English text patterns ===")
    english_patterns = [b"Episode", b"Continue", b"Are you sure", b"Nation",
                       b"PROTECT", b"Orwell", b"objective", b"Save", b"Load"]
    matches = 0
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                raw = obj.get_raw_data()
                for pattern in english_patterns:
                    if pattern in raw:
                        text = raw.decode('utf-8', errors='replace')
                        # Find the context around the match
                        idx = text.find(pattern.decode())
                        start = max(0, idx - 20)
                        end = min(len(text), idx + 80)
                        snippet = text[start:end].replace('\n', '\\n').replace('\r', '\\r')
                        print(f"  path_id={obj.path_id}: ...{snippet}...")
                        matches += 1
                        break
            except Exception:
                pass

    print(f"\nTotal MonoBehaviours with English text: {matches}")


def main():
    print("=" * 60)
    print("DETAILED ASSET INSPECTION")
    print("=" * 60)

    read_textassets()
    read_monobehaviours_raw()
    print("\n" + "=" * 60)
    print("BUNDLE INSPECTION (ALL 32)")
    print("=" * 60)
    inspect_all_bundles()


if __name__ == "__main__":
    main()
