"""Add proper SDF Cyrillic glyphs to the game's TextMeshPro font assets.

The game's UI fonts (Ubuntu) and the website fonts have no Cyrillic, so every Russian letter
fell back to LiberationSans with hand-made pseudo-SDF glyphs (blurry, wrong metrics/spacing).
This script renders real SDF glyphs (see sdfgen.py) from the matching TTF (font_map.py),
appends them to each font atlas (atlas height is doubled when needed) and updates the
font asset, the atlas texture and the TMP materials (_TextureHeight).

Usage: fix_fonts.py <out_dir>
  ORWELL_DATA_IN  folder with the asset files to patch (default: <game>/Ignorance_Data)
  ORWELL_ORIG     folder with ORIGINAL game sharedassets3.assets / resources.assets
                  (+ their .resS and globalgamemanagers*), default: <repo>/backup.
                  Font objects in these two files are taken from the originals, because
                  the mod's installer already injected glyphs there.
"""
import os, sys, math
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttg import load, D
from sdfgen import GlyphMaker
from font_map import FONT_MAP
import struct

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))

CHARS = ("ЁАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюяё"
         "«»—–…№“”„‘’•")

FILES = ["sharedassets0.assets", "sharedassets1.assets", "sharedassets3.assets", "resources.assets"]
FONTS_DIR = REPO


def font_assets(env):
    """(path_id, name) of TMP font assets in a file, found by name without a typetree."""
    out = []
    for o in env.objects:
        if o.type.name != "MonoBehaviour" or o.byte_size < 3000:
            continue
        raw = o.get_raw_data()
        n = struct.unpack_from("<i", raw, 28)[0]
        if 0 < n < 100:
            name = raw[32:32 + n].decode("utf-8", "replace")
            if name in FONT_MAP:
                out.append((o.path_id, name))
    return out


# fonts whose asset/atlas the RU mod modified: take them from the original game files
FROM_BACKUP = {"sharedassets3.assets", "resources.assets"}


class Packer:
    def __init__(self, occ):
        self.occ = occ  # bool [H, W], True = used

    def place(self, w, h, gap=1):
        H, W = self.occ.shape
        ww, hh = w + 2 * gap, h + 2 * gap
        ii = np.pad(self.occ.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        s = ii[hh:, ww:] - ii[:-hh, ww:] - ii[hh:, :-ww] + ii[:-hh, :-ww]
        free = np.argwhere(s == 0)
        if not len(free):
            return None
        y, x = free[0]  # top-most, then left-most
        self.occ[y:y + hh, x:x + ww] = True
        return x + gap, y + gap


def find_materials(env, tex_pid):
    out = []
    for o in env.objects:
        if o.type.name != "Material":
            continue
        t = o.read_typetree()
        texs = dict((k, v) for k, v in t["m_SavedProperties"]["m_TexEnvs"])
        mt = texs.get("_MainTex", {}).get("m_Texture", {})
        if mt.get("m_FileID") == 0 and mt.get("m_PathID") == tex_pid:
            out.append((o, t))
    return out


def set_float(t, name, val):
    fl = t["m_SavedProperties"]["m_Floats"]
    for i, pair in enumerate(fl):
        if pair[0] == name:
            fl[i] = (name, val)
            return True
    return False


# Vertical metrics of LiberationSans SDF (per em): every Cyrillic line used to take them from
# the fallback font, and the scenes (baked chunk boxes, line spacings) only line up with them.
# Off: with the runtime fix (tools/runtime_fix) the chunk boxes follow the real text, and the game's
# own (tighter) metrics are what the English layout was made with -> less overflow.
MATCH_FALLBACK_LINE_METRICS = False
LIB_ASCENDER = 77.84375 / 86.0
LIB_DESCENDER = -18.21875 / 86.0


def match_fallback_line_metrics(fi):
    """Make a line of this font as tall as a line that mixes it with the Liberation fallback.

    TMP 1.0 advances a line by  max(Ascender) - min(Descender) + (LineHeight - (Ascender - Descender)
    + lineSpacing) * scale, where Ascender/Descender come from the font of each character and the
    gap from the primary font. Many of the game's Ubuntu assets have a positive Descender, so pure
    Ubuntu lines are ~20% tighter than what the scenes were laid out for.
    """
    pt = fi["PointSize"]
    asc = max(fi["Ascender"], LIB_ASCENDER * pt)
    desc = min(fi["Descender"], LIB_DESCENDER * pt)
    fi["LineHeight"] += (asc - fi["Ascender"]) + (fi["Descender"] - desc)
    fi["Ascender"], fi["Descender"] = asc, desc


def patch_font(env, objs, src_objs, font_pid, font_name, log):
    fobj = objs[font_pid]
    ft = (src_objs or objs)[font_pid].read_typetree()
    fi = ft["m_fontInfo"]
    tex_pid = ft["atlas"]["m_PathID"]
    tex_src = (src_objs or objs)[tex_pid].read()
    atlas = np.asarray(tex_src.image)[..., 3].copy()  # top-down
    H0, W = atlas.shape
    pad = int(fi["Padding"])
    rel, wght, subst = FONT_MAP[font_name]
    ttf = os.path.join(FONTS_DIR, rel)
    cap = None
    if subst:
        cap = next(g["height"] for g in ft["m_glyphInfoList"] if g["id"] == ord("H"))
    gm = GlyphMaker(ttf, fi["PointSize"], fi["Padding"], wght=wght, cap_height=cap)

    glyphs = [g for g in ft["m_glyphInfoList"]]
    have = {g["id"] for g in glyphs}
    todo = [c for c in CHARS if ord(c) not in have and gm.has(c)]
    cells = [(c,) + gm.render(c) for c in todo]

    def occupancy(h):
        occ = np.zeros((h, W), bool)
        for g in glyphs:
            x0, y0 = int(g["x"]) - pad - 1, int(g["y"]) - pad - 1
            x1, y1 = int(math.ceil(g["x"] + g["width"])) + pad + 1, int(math.ceil(g["y"] + g["height"])) + pad + 1
            occ[max(0, y0):y1, max(0, x0):x1] = True
        return occ

    Hn = H0
    while True:
        pk = Packer(occupancy(Hn))
        placed = []
        for c, m, cell in sorted(cells, key=lambda t: -t[2].shape[0]):
            pos = pk.place(cell.shape[1], cell.shape[0])
            if pos is None:
                break
            placed.append((c, m, cell, pos))
        if len(placed) == len(cells):
            break
        Hn *= 2
    new_atlas = np.zeros((Hn, W), np.uint8)
    new_atlas[:H0] = atlas
    for c, m, cell, (x, y) in placed:
        new_atlas[y:y + cell.shape[0], x:x + cell.shape[1]] = cell
        glyphs.append(dict(id=ord(c), x=float(x + pad), y=float(y + pad), width=m["width"], height=m["height"],
                           xOffset=m["xOffset"], yOffset=m["yOffset"], xAdvance=m["xAdvance"], scale=1.0))
    ft["m_glyphInfoList"] = glyphs
    fi["CharacterCount"] = len(glyphs)
    fi["AtlasHeight"] = float(Hn)
    if MATCH_FALLBACK_LINE_METRICS:
        match_fallback_line_metrics(fi)
    fobj.save_typetree(ft)

    # texture: Alpha8, rows stored bottom-up
    tobj = objs[tex_pid]
    tt = (src_objs or objs)[tex_pid].read_typetree()
    raw = np.ascontiguousarray(new_atlas[::-1]).tobytes()
    tt["m_Height"] = Hn
    tt["m_CompleteImageSize"] = len(raw)
    tt["image data"] = raw
    tt["m_StreamData"] = {"offset": 0, "size": 0, "path": ""}
    tt["m_MipCount"] = 1
    tobj.save_typetree(tt)

    mats = find_materials(env, tex_pid)
    for mo, mt in mats:
        set_float(mt, "_TextureHeight", float(Hn))
        set_float(mt, "_TextureWidth", float(W))
        mo.save_typetree(mt)
    log.append(f"{ft['m_Name']} <- {os.path.basename(rel)}{' w'+str(wght) if wght else ''}{' (subst)' if subst else ''}: +{len(placed)} glyphs, atlas {W}x{H0}->{W}x{Hn}, materials {[m[1]['m_Name'] for m in mats]}")
    return new_atlas


def main(out_dir):
    D_IN = os.environ.get("ORWELL_DATA_IN", D)
    orig = os.environ.get("ORWELL_ORIG", os.path.join(REPO, "backup"))
    os.makedirs(out_dir, exist_ok=True)
    log = []
    for fname in FILES:
        env = load(os.path.join(D_IN, fname))
        objs = {o.path_id: o for o in env.objects}
        src_objs = None
        if fname in FROM_BACKUP:
            benv = load(os.path.join(orig, fname))
            src_objs = {o.path_id: o for o in benv.objects}
        for pid, name in font_assets(env):
            a = patch_font(env, objs, src_objs, pid, name, log)
            Image.fromarray(a).save(os.path.join(out_dir, f"atlas_{fname}_{pid}.png"))
        data = list(env.files.values())[0].save()
        open(os.path.join(out_dir, fname), "wb").write(data)
        print(fname, "written", len(data), flush=True)
    print("\n".join(log))


if __name__ == "__main__":
    main(sys.argv[1])
