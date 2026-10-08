"""TMP-compatible SDF glyph generator (matches TextMeshPro 1.x 'SDF' atlases).

Glyph metrics are taken unhinted at PointSize px; the distance field is computed
from a 16x supersampled render. Value = 0.5 + d / (2 * (padding + 1)), d in px, inside > 0.
"""
import math
import numpy as np
import freetype
from scipy.ndimage import distance_transform_edt, map_coordinates

SS = 16


class GlyphMaker:
    def __init__(self, ttf, point_size, padding, wght=None, cap_height=None):
        """wght: weight for variable fonts; cap_height: if set, scale the face so that 'H'
        is exactly this tall in px (used for substitute fonts of another family)."""
        self.pad = int(padding)
        self.gs = padding + 1  # _GradientScale
        size = point_size
        if cap_height:
            probe = self._face(ttf, 100, wght)
            probe.load_char("H", freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP)
            size = 100 * cap_height / (probe.glyph.metrics.height / 64)
        self.pt = size
        self.lo = self._face(ttf, size, wght)
        self.hi = self._face(ttf, size * SS, wght)

    @staticmethod
    def _face(ttf, size, wght):
        f = freetype.Face(ttf)
        if wght is not None:
            info = f.get_variation_info()
            coords = [wght if a.tag == "wght" else a.default for a in info.axes]
            f.set_var_design_coords(coords)
        f.set_char_size(0, int(round(size * 64)), 72, 72)
        return f

    def has(self, ch):
        return self.lo.get_char_index(ord(ch)) != 0

    def metrics(self, ch):
        self.lo.load_char(ch, freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP)
        m = self.lo.glyph.metrics
        return dict(width=m.width / 64, height=m.height / 64, xOffset=m.horiBearingX / 64,
                    yOffset=m.horiBearingY / 64, xAdvance=m.horiAdvance / 64)

    def cell_size(self, ch):
        m = self.metrics(ch)
        return int(math.ceil(m["width"])) + 2 * self.pad, int(math.ceil(m["height"])) + 2 * self.pad

    def render(self, ch):
        """Returns (metrics, cell ndarray uint8 [h, w]) where cell includes padding on all sides."""
        m = self.metrics(ch)
        cw, chh = self.cell_size(ch)
        self.hi.load_char(ch, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING)
        g = self.hi.glyph
        bm = g.bitmap
        rows, cols = bm.rows, bm.width
        margin = (self.pad + 3) * SS
        mask = np.zeros((rows + 2 * margin, cols + 2 * margin), bool)
        if rows and cols:
            buf = np.array(bm.buffer, np.uint8).reshape(rows, bm.pitch)[:, :cols]
            mask[margin:margin + rows, margin:margin + cols] = buf >= 128
        din = distance_transform_edt(mask)
        dout = distance_transform_edt(~mask)
        sd = np.where(mask, din - 0.5, -(dout - 0.5)) / SS  # target px, inside positive
        # target pixel centres in glyph space (y up)
        u = np.arange(cw) + 0.5
        v = np.arange(chh) + 0.5
        gx = m["xOffset"] - self.pad + u
        gy = m["yOffset"] + self.pad - v
        # hi-res array coords
        c = gx * SS - g.bitmap_left - 0.5 + margin
        r = g.bitmap_top - gy * SS - 0.5 + margin
        R, C = np.meshgrid(r, c, indexing="ij")
        d = map_coordinates(sd, [R, C], order=1, mode="constant", cval=-(self.gs + 1))
        val = np.clip(0.5 + d / (2 * self.gs), 0, 1)
        return m, np.round(val * 255).astype(np.uint8)
