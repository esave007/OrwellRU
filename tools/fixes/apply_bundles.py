"""Redraw the pictures with English text inside the asset bundles (Ignorance_Data/AssetBundles/PCIGN).

    python apply_bundles.py ORIG_PCIGN OUT_DIR

Many website pictures (logos, the government seal, banners, posters) live only in the bundles, some textures
have copies there besides sharedassets3.assets. Every bundle that holds a texture of ui_images.RENDERERS is
loaded from the original game files, its textures are redrawn by ui_images.py (ORWELL_IMAGES=base: only the
UI labels, see ui_images.BASE) and the bundle is written to OUT_DIR with LZ4 blocks like the original.
Bundles without such textures are not written. Everything is computed from the originals, so a second run
gives the same files.
"""
import os
import sys

import UnityPy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_images  # noqa: E402
from ui_images import RENDERERS, selected  # noqa: E402


def patch_bundle(path):
    """-> (bundle bytes, redrawn texture names), or (None, []) when nothing is redrawn"""
    env = UnityPy.load(path)
    textures = [o.read() for o in env.objects if o.type.name == "Texture2D"]

    class Siblings(dict):  # the original images of this bundle by name, decoded on demand
        def __missing__(self, name):
            self[name] = next(t.image for t in textures if t.m_Name == name)
            return self[name]

    ui_images.SIBLINGS = Siblings()
    # everything is drawn from the originals first (a picture can be made from another one), then replaced
    todo = [(tex, RENDERERS[tex.m_Name](tex.image)) for tex in textures if selected(tex.m_Name)]
    done = []
    for tex, img in todo:
        assert img.size == (tex.m_Width, tex.m_Height), tex.m_Name
        fmt = int(tex.m_TextureFormat)  # 3 RGB24, 4 RGBA32, 10 DXT1, 12 DXT5
        tex.set_image(img.convert("RGB" if fmt in (3, 10) else "RGBA"), target_format=fmt)
        tex.save()
        done.append(tex.m_Name)
    if not done:
        return None, []
    return env.file.save(packer="lz4"), done


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    total = 0
    for name in sorted(os.listdir(src), key=lambda n: (len(n), n)):
        path = os.path.join(src, name)
        if not os.path.isfile(path) or "." in name:  # the bundles have bare numeric names
            continue
        data, done = patch_bundle(path)
        if data is None:
            continue
        with open(os.path.join(out, name), "wb") as f:
            f.write(data)
        total += len(done)
        print(f"{name}: {len(done)} -> {', '.join(done)}")
    print(f"textures redrawn: {total}")


if __name__ == "__main__":
    main()
