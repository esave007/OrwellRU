#!/usr/bin/env python3
"""Инспекция структуры Unity assets — какие типы объектов есть."""
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
import sys
sys.stdout.reconfigure(encoding='utf-8')

import UnityPy
from pathlib import Path
from collections import Counter

GAME_DATA = Path(r"C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data")


def inspect_file(filepath):
    """Inspect object types in a Unity file."""
    print(f"\n=== {filepath.name} ({filepath.stat().st_size // 1024} KB) ===")
    env = UnityPy.load(str(filepath))

    type_counts = Counter()
    for obj in env.objects:
        type_counts[obj.type.name] += 1

    for type_name, count in type_counts.most_common():
        print(f"  {type_name}: {count}")

    # Try to read a few MonoBehaviours to see their structure
    mono_count = 0
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour" and mono_count < 3:
            try:
                data = obj.read()
                # Check if typetree is available
                try:
                    tree = data.read_typetree()
                    if tree:
                        keys = list(tree.keys())[:10]
                        print(f"  [MonoBehaviour path_id={obj.path_id}] typetree keys: {keys}")
                        # Check for text fields
                        for k, v in tree.items():
                            if isinstance(v, str) and len(v) > 3:
                                preview = v[:80].replace('\n', '\\n')
                                print(f"    {k} = \"{preview}\"")
                        mono_count += 1
                except Exception as e:
                    # Try raw read
                    print(f"  [MonoBehaviour path_id={obj.path_id}] no typetree: {e}")
                    mono_count += 1
            except Exception as e:
                print(f"  [MonoBehaviour ERROR] {e}")
                mono_count += 1

    # Check TextAsset
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            try:
                data = obj.read()
                text = data.text if hasattr(data, 'text') else str(data.script)
                name = data.name if hasattr(data, 'name') else "?"
                preview = text[:100].replace('\n', '\\n') if text else "(empty)"
                print(f"  [TextAsset] {name}: \"{preview}\"")
            except Exception as e:
                print(f"  [TextAsset ERROR] {e}")

    return type_counts


def inspect_bundle(filepath):
    """Inspect a single bundle."""
    print(f"\n=== Bundle: {filepath.name} ===")
    try:
        env = UnityPy.load(str(filepath))
        type_counts = Counter()
        for obj in env.objects:
            type_counts[obj.type.name] += 1

        for type_name, count in type_counts.most_common():
            print(f"  {type_name}: {count}")

        # Sample MonoBehaviours
        mono_count = 0
        for obj in env.objects:
            if obj.type.name == "MonoBehaviour" and mono_count < 2:
                try:
                    data = obj.read()
                    tree = data.read_typetree()
                    if tree:
                        # Look for m_text or any text field
                        text_fields = {k: v for k, v in tree.items()
                                      if isinstance(v, str) and len(v) > 5}
                        if text_fields:
                            print(f"  [MonoBehaviour path_id={obj.path_id}]")
                            for k, v in list(text_fields.items())[:3]:
                                preview = v[:100].replace('\n', '\\n')
                                print(f"    {k} = \"{preview}\"")
                            mono_count += 1
                except Exception:
                    pass

    except Exception as e:
        print(f"  [ERROR] {e}")


def main():
    print("INSPECTING GAME ASSETS")
    print("=" * 60)

    # Inspect main assets
    for name in ["resources.assets", "sharedassets0.assets", "sharedassets1.assets",
                  "sharedassets2.assets", "sharedassets3.assets", "sharedassets4.assets"]:
        path = GAME_DATA / name
        if path.exists():
            inspect_file(path)

    # Inspect first 3 bundles to understand structure
    print("\n\nINSPECTING BUNDLES (first 5)")
    print("=" * 60)
    bundles_dir = GAME_DATA / "AssetBundles" / "PCIGN"
    bundle_files = sorted(bundles_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0)

    for bf in bundle_files[:5]:
        inspect_bundle(bf)


if __name__ == "__main__":
    main()
