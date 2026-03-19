#!/usr/bin/env python3
"""
Fix: Update _TextureHeight in all LiberationSans SDF materials.

When the atlas is expanded from 1024x1024 to 1024x2048 for Cyrillic glyphs,
the _TextureHeight property in TMP SDF materials must also be updated.

This property is used by the TMP SDF shader for:
- Screen-space gradient scale calculations
- Outline width computation
- Underlay/drop shadow positioning
- Glow effect calculations

Materials to update (all in resources.assets):
  path_id=9:  "LiberationSans SDF - Drop Shadow"
  path_id=10: "LiberationSans SDF - Metalic Green"
  path_id=11: "LiberationSans SDF - Outline"
  path_id=12: "LiberationSans SDF - Overlay"
  path_id=13: "LiberationSans SDF - Soft Mask"
  path_id=23: "LiberationSans SDF Material"
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import UnityPy

GAME_RESOURCES = r'C:\Steam\steamapps\common\Orwell Ignorance is Strength\Ignorance_Data\resources.assets'
OUTPUT = r'C:\Projects\OrwellRU\patches\resources.assets'
NEW_ATLAS_HEIGHT = 2048.0

LIBERATION_MATERIAL_IDS = {9, 10, 11, 12, 13, 23}

def main():
    print("=" * 60)
    print("FIX: Update _TextureHeight in LiberationSans SDF materials")
    print("=" * 60)

    # Load the currently deployed game file (which already has our font patch)
    env = UnityPy.load(GAME_RESOURCES)

    updated = 0
    for obj in env.objects:
        if obj.type.name == 'Material' and obj.path_id in LIBERATION_MATERIAL_IDS:
            mat = obj.read()
            name = getattr(mat, 'm_Name', '?')

            if hasattr(mat, 'm_SavedProperties') and hasattr(mat.m_SavedProperties, 'm_Floats'):
                for i, fp in enumerate(mat.m_SavedProperties.m_Floats):
                    key = fp[0] if isinstance(fp, (list, tuple)) else getattr(fp, 'first', '?')
                    val = fp[1] if isinstance(fp, (list, tuple)) else getattr(fp, 'second', 0)

                    if key == '_TextureHeight' and val != NEW_ATLAS_HEIGHT:
                        old_val = val
                        if isinstance(fp, (list, tuple)):
                            mat.m_SavedProperties.m_Floats[i] = (key, NEW_ATLAS_HEIGHT)
                        else:
                            fp.second = NEW_ATLAS_HEIGHT
                        print("  %s (id=%d): _TextureHeight %.0f -> %.0f" % (
                            name, obj.path_id, old_val, NEW_ATLAS_HEIGHT))
                        updated += 1

                mat.save()

    if updated > 0:
        print("\nUpdated %d materials. Saving..." % updated)
        with open(OUTPUT, 'wb') as f:
            f.write(env.file.save())
        print("Saved: %s (%d bytes)" % (OUTPUT, os.path.getsize(OUTPUT)))
    else:
        print("\nNo materials needed updating.")

    # Verify
    print("\nVerification:")
    env2 = UnityPy.load(OUTPUT)
    for obj in env2.objects:
        if obj.type.name == 'Material' and obj.path_id in LIBERATION_MATERIAL_IDS:
            mat = obj.read()
            name = getattr(mat, 'm_Name', '?')
            if hasattr(mat, 'm_SavedProperties') and hasattr(mat.m_SavedProperties, 'm_Floats'):
                for fp in mat.m_SavedProperties.m_Floats:
                    key = fp[0] if isinstance(fp, (list, tuple)) else getattr(fp, 'first', '?')
                    val = fp[1] if isinstance(fp, (list, tuple)) else getattr(fp, 'second', 0)
                    if key == '_TextureHeight':
                        status = "OK" if val == NEW_ATLAS_HEIGHT else "FAIL (%.0f)" % val
                        print("  %s (id=%d): _TextureHeight=%.0f %s" % (name, obj.path_id, val, status))

    print("\nDone!")

if __name__ == '__main__':
    main()
