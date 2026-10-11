"""Russian versions of the game images with English text.

Every function takes the original texture (PIL image, as extracted from the game files) and returns the
Russian one of the same size, so no game artwork has to be stored in the repository. The font size and
position were matched to the original lettering (Ubuntu from the game, Arvo replaced by Bitter Italic as on
the websites).

- ibtn_showconflict           «SHOW CONFLICT ▸» -> «КОНФЛИКТ ▸»
- listener_phone_equalizer_end «connection ended.» -> «связь прервана.»
- insider_rabanpc_wallpaper    «THE PEOPLE'S VOICE / Speaking out loud what needs to be said»
                               -> «ГОЛОС НАРОДА / Говорим вслух то, что нужно сказать»
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FONTS = os.path.join(REPO, "fonts")
BITTER_ITALIC = os.path.join(FONTS, "google", "bitter", "Bitter-Italic[wght].ttf")


def _text_mask(text, font_file, size, w, h, x, base, spacing=0.0):
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font_file, size)
    for ch in text:
        d.text((x, base), ch, font=f, fill=255, anchor="ls")
        x += f.getlength(ch) + spacing
    return np.array(im).astype(float) / 255.0, x


def show_conflict(src):
    """RGB24 button: yellow Ubuntu Light 35 on black, the arrow is taken from the original."""
    a = np.array(src.convert("RGB")).astype(float)
    h, w = a.shape[:2]
    light = os.path.join(FONTS, "Ubuntu-Light.ttf")
    text, size, base, spacing = "КОНФЛИКТ", 35, 37, 0.5
    _, end = _text_mask(text, light, size, 2000, h, 0, base, spacing)
    text_w, gap, arrow_w = end - spacing, 19, 15
    x0 = round((w - (text_w + gap + arrow_w)) / 2)  # text + arrow centred on the button
    m, _ = _text_mask(text, light, size, w, h, x0, base, spacing)
    out = m[..., None] * np.array([240, 235, 90.0])
    arrow = a[:, 300:325]  # the arrow glyph sits at x 305..319 in the original
    ax = round(x0 + text_w + gap) - 5
    out[:, ax:ax + 25] = np.maximum(out[:, ax:ax + 25], arrow)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def call_ended(src):
    """RGBA strip: white dotted line + Ubuntu Regular 30, right-aligned like the original text."""
    a = np.array(src.convert("RGBA")).astype(float)
    h, w = a.shape[:2]
    regular = os.path.join(FONTS, "Ubuntu-Regular.ttf")
    text = "связь прервана."
    _, end = _text_mask(text, regular, 30, 2000, h, 0, 61)
    x0 = round(418.5 - end)
    m, _ = _text_mask(text, regular, 30, w, h, x0, 61)
    alpha = a[..., 3] / 255.0
    dash = np.zeros_like(alpha)
    dashes = [(7, 13), (20, 26), (33, 39), (46, 52), (59, 65), (72, 79), (86, 92), (99, 105), (112, 118),
              (125, 131), (138, 144), (151, 157)]  # the dots of the original, 13 px pitch
    for l, r in dashes:
        if r <= x0 - 9:
            dash[:, l - 1:r + 2] = alpha[:, l - 1:r + 2]
    x = 164
    while x + 6 <= x0 - 9:  # the Russian text is shorter: continue the dotted line up to it
        dash[:, x - 1:x + 8] = alpha[:, 150:159]
        x += 13
    out = np.zeros((h, w, 4))
    out[..., :3] = 255
    out[..., 3] = np.maximum(dash, m) * 255
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def _bitter(size, weight):
    f = ImageFont.truetype(BITTER_ITALIC, size)
    f.set_variation_by_axes([weight])
    return f


def peoples_voice_wallpaper(src):
    """The wallpaper is symmetric top/bottom (axis y = 397.5): the background under the English text is
    restored from the mirrored lower half, then the Russian text is drawn (4x supersampled)."""
    img = src.convert("RGBA")
    a = np.array(img).astype(float)
    b = a.copy()
    for y in range(160, 262):
        b[y] = a[795 - y]
    k = 4

    def draw(text, size, weight, cx, base, colour):
        im = Image.new("L", (img.width * k, 120 * k))
        ImageDraw.Draw(im).text((cx * k, 90 * k), text, font=_bitter(size * k, weight), fill=255, anchor="ms")
        m = np.array(im.resize((img.width, 120), Image.LANCZOS)).astype(float) / 255.0
        y0 = base - 90
        for i, c in enumerate(colour):
            b[y0:y0 + 120, :, i] = b[y0:y0 + 120, :, i] * (1 - m) + c * m

    draw("ГОЛОС НАРОДА", 54, 800, 515, 215, (253, 253, 253))  # cap height of the original title
    draw("Говорим вслух то, что нужно сказать", 23, 600, 512, 247, (231, 231, 231))
    return Image.fromarray(np.clip(b, 0, 255).astype(np.uint8), "RGBA")


# ---- website logos and pictures (resources.assets and the AssetBundles) --------------------------------
# The same picture is stored in several sizes (bookmark icon 260x260, site header, ...), so the renderers
# below work in coordinates relative to the image and measure the English lettering in the picture itself:
# the Russian text gets the same cap height, colour, centre and baseline.

def _font(name, size, **axes):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if axes:
        tags = {"weight": "wght", "width": "wdth", "optical size": "opsz"}
        values = []
        for ax in f.get_variation_axes():
            name = ax["name"].decode() if isinstance(ax["name"], bytes) else ax["name"]
            values.append(axes.get(tags.get(name.lower(), name.lower()), ax["default"]))
        f.set_variation_by_axes(values)
    return f


def _cap_height(font, ref="Н"):
    return -font.getbbox(ref, anchor="ls")[1]


def _ink_rows(a, bg, x0, x1, y0, y1, tol=60):
    """contiguous row blocks [(top, bottom)] with pixels differing from bg inside the box"""
    ink = np.abs(a[y0:y1, x0:x1, :3] - np.array(bg[:3], float)).sum(2) > tol
    rows = ink.any(1)
    blocks, start = [], None
    for i, r in enumerate(list(rows) + [False]):
        if r and start is None:
            start = i
        elif not r and start is not None:
            blocks.append((y0 + start, y0 + i - 1))
            start = None
    return blocks, ink


def _ink_box(a, bg, x0, x1, y0, y1, tol=60):
    _, ink = _ink_rows(a, bg, x0, x1, y0, y1, tol)
    ys, xs = np.where(ink)
    return x0 + xs.min(), y0 + ys.min(), x0 + xs.max(), y0 + ys.max()


def _darkest(a, box, bg):
    x0, y0, x1, y1 = box
    p = a[y0:y1 + 1, x0:x1 + 1, :3].reshape(-1, 3)
    d = np.abs(p - np.array(bg[:3], float)).sum(1)
    return p[d >= np.percentile(d, 95)].mean(0)  # the solid middle of the strokes, not the antialiasing


def _draw(b, text, font_file, cap, cx, base, colour, max_w=None, anchor="ms", k=4, spacing=0.0, ref="Н", **axes):
    """Draw text (4x supersampled) into the float array b: the size gives the letter ref (capital Н, or н for
    the x-height of a lowercase line) the height cap, reduced if the line is wider than max_w.
    anchor m/l/r + s: centre/left/right at the baseline."""
    f1 = _font(font_file, 100, **axes)
    size = cap / _cap_height(f1, ref) * 100
    def width(sz):
        f = _font(font_file, sz * k, **axes)
        return (f.getlength(text) + spacing * k * (len(text) - 1)) / k
    if max_w and width(size) > max_w:
        size *= max_w / width(size)
    f = _font(font_file, size * k, **axes)
    h, w = b.shape[:2]
    im = Image.new("L", (w * k, h * k))
    d = ImageDraw.Draw(im)
    tw = width(size)
    x = {"m": cx - tw / 2, "l": cx, "r": cx - tw}[anchor[0]] * k
    for ch in text:
        d.text((x, base * k), ch, font=f, fill=255, anchor="ls")
        x += f.getlength(ch) + spacing * k
    m = np.array(im.resize((w, h), Image.LANCZOS)).astype(float)[..., None] / 255.0
    b[..., :3] = b[..., :3] * (1 - m) + np.array(colour[:3], float) * m
    if b.shape[2] == 4:
        b[..., 3:] = np.maximum(b[..., 3:], 255 * m)
    return size


def _replace_line(b, a, box, bg, text, font_file, colour=None, max_w=None, pad=2, **axes):
    """Erase the English line in box (filled with bg) and draw the Russian one centred in its place."""
    x0, y0, x1, y1 = box
    colour = colour if colour is not None else _darkest(a, box, bg)
    cap = y1 - y0 + 1
    b[y0 - pad:y1 + pad + 1, x0 - pad:x1 + pad + 1, :3] = np.array(bg[:3], float)
    return _draw(b, text, font_file, cap, (x0 + x1 + 1) / 2, y1 + 1, colour, max_w, **axes)


def party_logo(src):
    """«THE PARTY» under the shield -> «ПАРТИЯ» (serif, the blue of the lettering)"""
    a = np.array(src.convert("RGB")).astype(float)
    h, w = a.shape[:2]
    bg = a[h - 12, w // 2]
    blocks, _ = _ink_rows(a, bg, 8, w - 8, int(h * 0.7), h - 8)
    box = _ink_box(a, bg, 8, w - 8, *blocks[-1][:1], blocks[-1][1] + 1)
    b = a.copy()
    _replace_line(b, a, box, bg, "ПАРТИЯ", "google/notoserif/NotoSerif[wdth,wght].ttf", wght=400)
    return Image.fromarray(np.clip(b, 0, 255).astype(np.uint8), "RGB")


def _sized(src, specs):
    """the spec for this texture size (the same picture is stored in several sizes)"""
    return specs[(src.width, src.height)]


def _out(b, mode):
    return Image.fromarray(np.clip(b, 0, 255).astype(np.uint8), mode)


def pargesian_army_logo(src):
    """«ARMY OF PARGES» on the ribbon -> «АРМИЯ ПАРГЕСА» (Lato Bold, dark green), within the inner plate"""
    # text box (x0, y0, x1, y1: cap height) and the inner width of the plate, measured in the originals
    box, max_w = _sized(src, {(650, 407): ((109, 261, 539, 298), 420), (260, 260): ((54, 150, 206, 162), 148)})
    a = np.array(src.convert("RGBA")).astype(float)
    bg = a[box[1] - 4, box[0]]
    b = a.copy()
    _replace_line(b, a, box, bg, "АРМИЯ ПАРГЕСА", "google/lato/Lato-Bold.ttf", max_w=max_w)
    return _out(b, "RGBA")


def _erase(b, box, pad=2):
    """Remove lettering from a gradient / low-poly background: every column of the box is interpolated
    between the pixels just above and just below it."""
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    top, bottom = b[y0 - 1, x0:x1 + 1].copy(), b[y1 + 1, x0:x1 + 1].copy()
    n = y1 - y0 + 2
    for i, y in enumerate(range(y0, y1 + 1), 1):
        b[y, x0:x1 + 1] = top + (bottom - top) * (i / n)


SERIF_ITALIC = "google/notoserif/NotoSerif-Italic[wdth,wght].ttf"
MERRIWEATHER = "google/merriweather/Merriweather[opsz,wdth,wght].ttf"
ROBOTO_SLAB = "google/robotoslab/RobotoSlab[wght].ttf"


def school_logo(src):
    """«PRAVA / Secondary» -> «ПРАВСКАЯ / средняя школа» (heavy serif / bold italic, the dark green)"""
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()
    green = (17, 87, 84)
    _erase(b, (81, 42, 179, 62))
    _erase(b, (69, 204, 190, 226))
    _draw(b, "ПРАВСКАЯ", MERRIWEATHER, 21, 130, 63, green, max_w=200, wght=900)
    _draw(b, "средняя школа", SERIF_ITALIC, 11, 130, 221, green, max_w=200, ref="н", wght=800)
    return _out(b, "RGB")


def prava_city_logo(src):
    """«CITY OF PRAVA» under the owl -> «ГОРОД ПРАВА» (light slab serif, navy)"""
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()
    _erase(b, (34, 221, 226, 239))
    _draw(b, "ГОРОД ПРАВА", ROBOTO_SLAB, 19, 130, 240, (21, 37, 82), max_w=200, wght=330)
    return _out(b, "RGB")


def immigration_logo(src):
    """«National Immigration / Database» on the brown bars -> «Национальная иммиграционная / база данных»
    (bold serif, white); the seal in the middle is redrawn by government_seal"""
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()
    _erase(b, (13, 12, 246, 34))
    _erase(b, (83, 229, 177, 245))
    # the site is called «Национальная иммиграционная база данных» in the game (bookmark caption); in one
    # line on the upper bar it gets too small to read, so two lines filling the bar (y 1..45)
    _draw(b, "Национальная", MERRIWEATHER, 14, 130, 21, (231, 229, 227), max_w=238, wght=700)
    _draw(b, "иммиграционная", MERRIWEATHER, 14, 130, 40, (231, 229, 227), max_w=238, wght=700)
    _draw(b, "база данных", MERRIWEATHER, 17, 130, 246, (231, 229, 227), max_w=234, wght=700)
    government_seal(src, 129.5, 129.5, 64.2, b=b, grow=8.0)  # the small brown seal (white ring r 64.2..69)
    return _out(b, "RGB")


def _fill(b, mask, iterations=400, init=True):
    """Fill the masked pixels smoothly from their surroundings (the masked area is relaxed towards the mean
    of its neighbours, the unmasked pixels stay as they are)."""
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return
    y0, y1, x0, x1 = max(ys.min() - 1, 0), ys.max() + 2, max(xs.min() - 1, 0), xs.max() + 2
    sub, m = b[y0:y1, x0:x1].copy(), mask[y0:y1, x0:x1]
    known = ~m
    if init:  # start from the mean of the surroundings (or from what the caller already put there)
        sub[m] = sub[known].mean(0) if known.any() else 0
    for _ in range(iterations):
        p = np.pad(sub, ((1, 1), (1, 1), (0, 0)), mode="edge")
        avg = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4
        sub[m] = avg[m]
    b[y0:y1, x0:x1] = sub


def _median_fill(b, mask, win=7):
    """Fill the masked pixels with the median colour of the unmasked pixels around them (an edge keeping
    fill for flat low-poly facets), from the outside in: pixels without unmasked neighbours wait for the
    next pass."""
    mask = mask.copy()
    h, w = mask.shape
    for _ in range(40):
        ys, xs = np.nonzero(mask)
        if not len(ys):
            break
        done = []
        for y, x in zip(ys, xs):
            y0, y1, x0, x1 = max(0, y - win), min(h, y + win + 1), max(0, x - win), min(w, x + win + 1)
            free = ~mask[y0:y1, x0:x1]
            if free.sum() >= 6:
                b[y, x] = np.median(b[y0:y1, x0:x1][free], axis=0)
                done.append((y, x))
        if not done:
            win += 3
            continue
        for y, x in done:
            mask[y, x] = False


def _facet_fill(b, mask, area, q=1.0, thr=3.0, ss=3, labels_out=None):
    """Rebuild a flat-shaded low-poly background under the masked pixels from its geometry instead of
    smudging it: the visible facets are the flat (low gradient) regions of `area`; each edge between two
    facets near the mask is fitted with a straight line, and since the facets are triangles (convex), a
    hidden pixel can only belong to a facet on whose side of all its fitted edges it lies. Of those it gets
    the nearest one (a vertex hidden under the letters), and the colour of that facet, fitted as a plane over
    its pixels next to the mask (the blurred wallpapers shade slightly). `ss`x`ss` samples per pixel
    antialias the rebuilt edges."""
    from scipy import ndimage
    from scipy.spatial import ConvexHull
    h, w = mask.shape
    s = ndimage.gaussian_filter(b[..., :3], (0.7, 0.7, 0))
    g = np.zeros((h, w))
    for c in range(3):
        g = np.maximum(g, np.hypot(ndimage.sobel(s[..., c], 0), ndimage.sobel(s[..., c], 1)) / 8)
    known = area & ~mask
    lab, n = ndimage.label(known & (g < thr))
    reach = max(6, int(30 * q))  # how far from the letters a facet still counts
    near = ndimage.binary_dilation(mask, iterations=reach)
    yy, xx = np.mgrid[0:h, 0:w]
    facets = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        reg = lab == i
        if reg.sum() < max(12, 40 * q * q) or not (reg & near).any():
            continue
        dist = ndimage.distance_transform_edt(~reg)
        local = reg & ndimage.binary_dilation(mask, iterations=reach + 10)
        py, px = np.nonzero(local)
        A = np.c_[px, py, np.ones(len(px))]
        vals = b[py, px]
        if len(px) > 300:  # a slight shading across the facet
            colour = [np.linalg.lstsq(A, vals[:, c], rcond=None)[0] for c in range(b.shape[2])]
        else:
            colour = [np.array([0.0, 0.0, np.median(vals[:, c])]) for c in range(b.shape[2])]
        grain = np.std(vals[:, :3].mean(1) - A @ np.mean([cf[:3] for cf in colour[:3]], 0))
        # convex (a triangle, maybe notched by the letters)? the plate around the wings is not, and its
        # edges say nothing about the hidden part
        ry, rx = np.nonzero(reg)
        hull = ConvexHull(np.c_[rx, ry])
        sy, sx = sl
        hy, hx = np.mgrid[sy, sx]
        inside = np.all(hull.equations[:, :2] @ np.array([hx.ravel(), hy.ravel()])
                        + hull.equations[:, 2:3] <= 0.5, axis=0).reshape(hx.shape)
        solidity = (reg | mask)[sl][inside].sum() / inside.sum()
        convex = solidity >= 0.7
        facets.append({"reg": reg, "dist": dist, "colour": colour, "grain": grain, "convex": convex,
                       "lo": np.percentile(vals, 2, 0), "hi": np.percentile(vals, 98, 0),
                       "cy": py.mean(), "cx": px.mean(), "edges": []})
    def add_edge(i, j, ex, ey, max_bend=1.6):
        if not (facets[i]["convex"] and facets[j]["convex"]):
            return
        m = np.c_[ex, ey].astype(float)
        mu = m.mean(0)
        u, sv, vt = np.linalg.svd(m - mu, full_matrices=False)
        spread = sv / np.sqrt(len(m))
        if spread[0] < 2.5 or spread[1] > max_bend:  # too short, or not straight
            return
        nrm = vt[1]
        for k in (i, j):
            f = facets[k]
            sign = np.sign((np.array([f["cx"], f["cy"]]) - mu) @ nrm) or 1.0
            f["edges"].append((nrm * sign, mu))
        paired.add((i, j))

    # the edge between two facets: the pixels within 4 px of both, if they lie on a line
    paired = set()
    grown = [ndimage.binary_dilation(f["reg"], iterations=4) for f in facets]
    for i in range(len(facets)):
        for j in range(i + 1, len(facets)):
            ey, ex = np.nonzero(grown[i] & grown[j] & ~mask)
            if len(ey) >= 8:
                add_edge(i, j, ex, ey)
    ys, xs = np.nonzero(mask)
    if not facets or not len(ys):
        return

    def assign(px, py):
        best = np.full(len(ys), np.inf)
        pick = np.zeros(len(ys), int)
        fallback = np.full(len(ys), np.inf)
        fpick = np.zeros(len(ys), int)
        for k, f in enumerate(facets):
            d = f["dist"][ys, xs]
            inside = np.ones(len(ys), bool)
            for nrm, mu in f["edges"]:
                inside &= (px - mu[0]) * nrm[0] + (py - mu[1]) * nrm[1] > -0.5
            better = inside & (d < best)
            best[better], pick[better] = d[better], k
            fb = d < fallback
            fallback[fb], fpick[fb] = d[fb], k
        pick[np.isinf(best)] = fpick[np.isinf(best)]
        return pick

    # an edge hidden entirely under the letters: straighten the nearest-facet border between the two facets
    pick = np.full(mask.shape, -1)
    pick[ys, xs] = assign(xs, ys)
    if labels_out is not None:
        labels_out["facets"], labels_out["mask"] = facets, mask
    for i in range(len(facets)):
        for j in range(i + 1, len(facets)):
            if (i, j) in paired:
                continue
            a_, b_ = pick == i, pick == j
            touch = (a_ & ndimage.binary_dilation(b_)) | (b_ & ndimage.binary_dilation(a_))
            ey, ex = np.nonzero(touch)
            if len(ey) >= 6:
                add_edge(i, j, ex, ey, max_bend=4.0)
    out = np.zeros((len(ys), b.shape[2]))
    noise = np.zeros(len(ys))
    offs = (np.arange(ss) + 0.5) / ss - 0.5
    for oy in offs:
        for ox in offs:
            px, py = xs + ox, ys + oy
            pick = assign(px, py)
            for k, f in enumerate(facets):
                sel = pick == k
                if sel.any():
                    noise[sel] += f["grain"]
                    for c in range(b.shape[2]):
                        cf = f["colour"][c]
                        out[sel, c] += np.clip(cf[0] * px[sel] + cf[1] * py[sel] + cf[2], f["lo"][c], f["hi"][c])
    # the grain of the printed texture, so the rebuilt part does not look smoother than the rest
    field = ndimage.gaussian_filter(np.random.default_rng(0).standard_normal((h, w)), 0.6)
    field /= field.std()
    out /= ss * ss
    out[:, :3] += (field[ys, xs] * noise / (ss * ss))[:, None]
    b[ys, xs] = np.clip(out, 0, 255)
    if labels_out is not None:
        full = np.full(mask.shape, -1)
        for k, f in enumerate(facets):
            full[f["reg"]] = k
        full[ys, xs] = assign(xs.astype(float), ys.astype(float))
        labels_out["labels"] = full


def _walls_fill(b, mask, area, edges, source=None, ss=4, blur=0.0):
    """Rebuild a flat-shaded low-poly background under the masked pixels from known facet edges: the colour
    of the visible facets (`source`, default `area`, without the soft pixels along the edges) flows into
    the masked pixels on a grid `ss` times finer, and the `edges` (pixel segments x0, y0, x1, y1), extended
    under the letters, are walls it cannot cross, so each facet keeps its straight borders; the samples
    are averaged back (antialiasing). `blur` softens the rebuilt part like a downscaled copy of the art."""
    from scipy import ndimage
    from PIL import ImageDraw
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return
    pad = 8
    x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
    x1, y1 = min(w, xs.max() + pad + 1), min(h, ys.max() + pad + 1)
    W, H = (x1 - x0) * ss, (y1 - y0) * ss
    canvas = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(canvas)
    for ax, ay, bx, by in edges:
        d.line([((ax - x0) * ss, (ay - y0) * ss), ((bx - x0) * ss, (by - y0) * ss)], fill=255, width=2)
    wall = np.array(canvas) > 0
    up = lambda m: np.repeat(np.repeat(m, ss, 0), ss, 1)
    crop = b[y0:y1, x0:x1]
    win = 9  # the window of the clean facet colour; the pixels it would take across an edge are left out
    near_wall = ndimage.binary_dilation(wall, iterations=(win // 2 + 2) * ss)[ss // 2::ss, ss // 2::ss]
    known = ((area if source is None else source) & ~mask)[y0:y1, x0:x1] & ~near_wall
    # the clean facet colour around each visible pixel (its grain is added back below)
    wsum = ndimage.uniform_filter(known.astype(float), win)
    smooth = np.stack([ndimage.uniform_filter(np.where(known, crop[..., c], 0), win) for c in range(b.shape[2])], -1)
    smooth /= np.maximum(wsum, 1e-6)[..., None]
    grain = np.median(np.abs(crop[..., :3].mean(2) - smooth[..., :3].mean(2))[known]) * 1.4 if known.any() else 0
    col = np.zeros((H, W, b.shape[2]))
    done = up(known) & ~wall
    col[done] = up(smooth)[done]
    todo = up(area[y0:y1, x0:x1] | mask[y0:y1, x0:x1]) & ~done & ~wall
    for _ in range(4 * (W + H)):
        if not todo.any():
            break
        acc = np.zeros_like(col)
        cnt = np.zeros((H, W))
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            src = np.roll(done, (dy, dx), (0, 1))
            if dy == 1: src[0] = False
            if dy == -1: src[-1] = False
            if dx == 1: src[:, 0] = False
            if dx == -1: src[:, -1] = False
            src &= todo
            acc[src] += np.roll(col, (dy, dx), (0, 1))[src]
            cnt[src] += 1
        new = cnt > 0
        if not new.any():
            break
        col[new] = acc[new] / cnt[new][:, None]
        done |= new
        todo &= ~new
    # the walls themselves and anything enclosed: the nearest reached sample
    idx = ndimage.distance_transform_edt(~done, return_distances=False, return_indices=True)
    col = col[idx[0], idx[1]]
    fill = col.reshape(y1 - y0, ss, x1 - x0, ss, -1).mean((1, 3))
    field = ndimage.gaussian_filter(np.random.default_rng(0).standard_normal(fill.shape[:2]), 0.6)
    fill[..., :3] += (field / field.std() * grain)[..., None]
    m = mask[y0:y1, x0:x1]
    if blur:
        fill = ndimage.gaussian_filter(np.where(m[..., None], fill, crop), (blur, blur, 0))
    crop[m] = np.clip(fill[m], 0, 255)


# the facet edges crossing the lettering of the government seal (all its copies share the art), in units of
# the disk radius from its centre; measured on the large header_image_government_logo with its letters
# rebuilt by _facet_fill; _walls_fill extends them under the letters
SEAL_EDGES = [
    (-0.0748, -0.9774, -0.2383, -0.7907), (-0.3542, -0.9136, -0.2499, -0.7896), (0.1333, -0.6557, 0.1768, -0.9681),
    (-0.2377, -0.7855, 0.1194, -0.6458), (0.5409, -0.7925, 0.1403, -0.6481), (-0.4713, -0.8446, -0.3293, -0.8017),
    (-0.3287, -0.7965, -0.2614, -0.7716), (-0.3217, -0.7884, -0.7386, -0.4806), (-0.7507, -0.4730, -0.8899, -0.4023),
    (0.5791, -0.7942, 0.5374, -0.3600), (0.1287, -0.6429, 0.2128, -0.5391), (-0.2499, -0.7652, -0.2603, -0.5159),
    (0.9090, -0.3652, 0.7461, -0.2777), (0.1310, -0.6441, 0.0823, -0.5745), (-0.6794, 0.0667, -0.9733, 0.1165),
    (0.7299, 0.0371, 0.9316, 0.2319), (0.9148, 0.2423, 0.4707, 0.3432),
    (-0.9646, 0.1426, -0.8614, 0.4330), (-0.4603, 0.3449, -0.6661, 0.7177), (0.9270, 0.2533, 0.7188, 0.6336),
    (0.2603, 0.5177, 0.5287, 0.8255), (-0.1519, 0.5617, -0.6023, 0.7704), (-0.2649, 0.6568, -0.4441, 0.7281),
]


def _erase_angular(b, mask, cx, cy, max_deg=40):
    """Fill the masked pixels along the circle around (cx, cy) through them: each one gets the colour
    interpolated between the nearest unmasked pixels at the same radius on both sides (the gaps between the
    letters of a round inscription), so the rings and facets of the seal keep their radius."""
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    r = np.hypot(xs - cx, ys - cy) + 1e-6
    th = np.arctan2(ys - cy, xs - cx)
    step = 0.7 / r  # ~0.7 px along the circle
    def find(sign):
        found = np.full(len(xs), -1.0)
        for k in range(1, int(np.radians(max_deg) / step.min()) + 1):
            t = th + sign * step * k
            px = np.clip(np.round(cx + r * np.cos(t)).astype(int), 0, w - 1)
            py = np.clip(np.round(cy + r * np.sin(t)).astype(int), 0, h - 1)
            free = (found < 0) & ~mask[py, px] & (step * k < np.radians(max_deg))
            found[free] = k
            if (found >= 0).all():
                break
        return found
    k1, k2 = find(-1), find(1)
    k1[k1 < 0], k2[k2 < 0] = 1, 1
    def at(sign, k):
        t = th + sign * step * k
        return b[np.clip(np.round(cy + r * np.sin(t)).astype(int), 0, h - 1),
                 np.clip(np.round(cx + r * np.cos(t)).astype(int), 0, w - 1)]
    p1, p2 = at(-1, k1), at(1, k2)
    t = (k1 / (k1 + k2))[:, None]
    b[ys, xs] = p1 * (1 - t) + p2 * t


def _erase_radial(b, mask, cx, cy, max_steps=60):
    """Fill the masked pixels along the radius of the circle (cx, cy): each one gets the colour interpolated
    between the nearest unmasked pixels inward and outward (keeps the low-poly facets of a round seal)."""
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    dx, dy = xs - cx, ys - cy
    r = np.hypot(dx, dy) + 1e-6
    ux, uy = dx / r, dy / r
    def find(sign):
        found = np.full(len(xs), -1.0)
        for k in range(1, max_steps):
            px = np.clip(np.round(xs + sign * ux * k).astype(int), 0, w - 1)
            py = np.clip(np.round(ys + sign * uy * k).astype(int), 0, h - 1)
            free = (found < 0) & ~mask[py, px]
            found[free] = k
        return found
    kin, kout = find(-1), find(1)
    kin[kin < 0], kout[kout < 0] = 1, 1
    pin = b[np.clip(np.round(ys - uy * kin).astype(int), 0, h - 1), np.clip(np.round(xs - ux * kin).astype(int), 0, w - 1)]
    pout = b[np.clip(np.round(ys + uy * kout).astype(int), 0, h - 1), np.clip(np.round(xs + ux * kout).astype(int), 0, w - 1)]
    t = (kin / (kin + kout))[:, None]
    b[ys, xs] = pin * (1 - t) + pout * t


def _arc_text(b, text, font_file, cap, cx, cy, r_base, centre_deg, top, colour, span=None, k=4, **axes):
    """Draw text along a circle: top=True reads clockwise over the top with the letters pointing outward
    (baseline at r_base), top=False reads left to right under the centre with the letters pointing inward
    (baseline at r_base, the outer side). span: arc length (px at r_base) the line is spread over by letter
    spacing (or squeezed into)."""
    f1 = _font(font_file, 100, **axes)
    size = cap / _cap_height(f1) * 100
    f = _font(font_file, size * k, **axes)
    widths = [f.getlength(ch) / k for ch in text]
    natural = sum(widths)
    spacing = 0.0
    if span:
        if natural > span:
            size *= span / natural
            f = _font(font_file, size * k, **axes)
            widths = [f.getlength(ch) / k for ch in text]
            natural = sum(widths)
        else:
            spacing = (span - natural) / max(1, len(text) - 1)
    total = natural + spacing * (len(text) - 1)
    pad = int(cap * 0.6) + 4
    sw, shh = int(total + 2 * pad), int(cap * 1.6 + 2 * pad)
    strip = Image.new("L", (sw * k, shh * k))
    d = ImageDraw.Draw(strip)
    base = shh - pad - cap * 0.3
    x = pad
    for ch, cw in zip(text, widths):
        d.text((x * k, base * k), ch, font=f, fill=255, anchor="ls")
        x += cw + spacing
    s = np.array(strip).astype(float) / 255.0
    # every output pixel (4x4 subsamples) -> position on the straight strip
    h, w = b.shape[:2]
    reach = r_base + (cap * 1.3 if top else 0) + 3, r_base - (0 if top else cap * 1.3) - 3
    y0, y1 = int(max(0, cy - reach[0] - 2)), int(min(h, cy + reach[0] + 3))
    x0, x1 = int(max(0, cx - reach[0] - 2)), int(min(w, cx + reach[0] + 3))
    gy, gx = np.mgrid[y0:y1, x0:x1].astype(float)
    cover = np.zeros(gx.shape)
    n = 4
    for sy in range(n):
        for sx in range(n):
            px, py = gx + (sx + 0.5) / n, gy + (sy + 0.5) / n
            r = np.hypot(px - cx, py - cy)
            th = np.degrees(np.arctan2(py - cy, px - cx))
            dth = (th - centre_deg + 180) % 360 - 180
            if top:
                u, v = np.radians(dth) * r_base, r - r_base
            else:
                u, v = -np.radians(dth) * r_base, r_base - r
            col = (pad + total / 2 + u) * k
            row = (base - v) * k
            ok = (col >= 0) & (col < sw * k - 1) & (row >= 0) & (row < shh * k - 1) & (np.abs(dth) < 170)
            ci, ri = np.clip(col.astype(int), 0, sw * k - 1), np.clip(row.astype(int), 0, shh * k - 1)
            cover += np.where(ok, s[ri, ci], 0.0)
    m = (cover / (n * n))[..., None]
    region = b[y0:y1, x0:x1]
    region[..., :3] = region[..., :3] * (1 - m) + np.array(colour, float) * m
    return size


def government_seal(src, cx, cy, R, b=None, dark=False, grow=1.5, text_in=118, ring_cut=None, band=None, blur=0.0):
    """«GOVERNMENT OF / THE NATION» around the winged seal -> «ПРАВИТЕЛЬСТВО / НАЦИИ».
    (cx, cy, R): centre and radius of the coloured disk (inside the white ring) in this texture; the text
    geometry is measured on header_image_government_logo (R 172.5): the upper line has its baseline at
    r 129 and capitals 21 high over 148 degrees, the lower one its baseline at r 151 and capitals 30 high,
    pointing to the centre. Only the letters are erased: the white components inside the text ring that do
    not reach the wings (inside r 121) or the outer ring."""
    from scipy import ndimage
    a = np.array(src.convert("RGBA")).astype(float)
    if b is None:
        b = a.copy()
    q = R / 172.5
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(xx - cx, yy - cy)
    ink = a[..., :3].max(2) < 90 if dark else a[..., :3].min(2) > 200  # dark letters on the light seal
    colour = (28, 28, 34) if dark else (255, 255, 255)
    ring_cut = ring_cut or R - 4 * q
    lab, n = ndimage.label(ink & (r < ring_cut))  # cut off from the ring (small seals blur them together)
    letters = np.zeros_like(ink)
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        comp = lab[sl] == i
        if r[sl][comp].min() > text_in * q:  # not a wing
            letters[sl] |= comp
    if band:  # small seal: the letters run together; take every light pixel of the text ring except the wings
        wings = np.zeros_like(ink)
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            comp = lab[sl] == i
            if r[sl][comp].min() <= text_in * q:
                wings[sl] |= comp
        letters = ink & (r > band[0]) & (r < band[1]) & ~ndimage.binary_dilation(wings)
    # grow over the antialiasing (and the drop shadow of the brown seal)
    letters = ndimage.binary_dilation(letters, iterations=max(4, round((grow + 3) * q))) & (r < ring_cut + 0.5)
    # the letters cast a dark shadow on the coloured seal: take the darker pixels next to them too
    lum = a[..., :3].mean(2)
    local = ndimage.median_filter(lum, size=max(5, int(15 * q)))
    near = ndimage.binary_dilation(letters, iterations=max(2, round(4 * q)))
    letters |= near & (np.abs(lum - local) > 18) & (r > text_in * q) & (r < ring_cut)
    if dark:  # the plain light plate
        _facet_fill(b, letters, r < ring_cut, q)
    else:  # the low-poly facets: rebuilt from their edges
        edges = [(cx + u0 * R, cy + v0 * R, cx + u1 * R, cy + v1 * R) for u0, v0, u1, v1 in SEAL_EDGES]
        plain = (r < ring_cut) & ~ndimage.binary_dilation(ink, iterations=2)
        _walls_fill(b, letters, r < ring_cut, edges, source=plain, blur=blur)
    font = ROBOTO_SLAB
    _arc_text(b, "ПРАВИТЕЛЬСТВО", font, 18 * q, cx, cy, 131 * q, -90, True, colour,
              span=np.radians(110) * 131 * q, wght=700)
    _arc_text(b, "НАЦИИ", font, 33 * q, cx, cy, 152 * q, 90, False, colour,
              span=np.radians(74) * 152 * q, wght=700)
    return b


# texture -> (cx, cy, R) of the coloured disk, fitted to the edge of the white ring in each texture
SEALS = {
    "header_image_government_logo": (183.5, 183.5, 172.5),
    "website_government": (130.0, 131.0, 93.5),
    "header_image_immigration_logo": (147.0, 147.0, 137.0),
    "insider_baytephone_wallpaper": (512.0, 439.0, 179.7),
}


def _seal_renderer(name, dark=False, grow=1.5):
    def render(src):
        cx, cy, R = SEALS[name]
        return _out(government_seal(src, cx, cy, R, dark=dark, grow=grow), "RGBA")
    render.__name__ = "government_seal_" + name
    return render


RALEWAY = "google/raleway/Raleway[wght].ttf"
SOURCE_SANS = "google/sourcesans3/SourceSans3[wght].ttf"


def tnb_logo(src):
    """«Fast. Precise. Honest.» under the TNB logo -> «Быстро. Точно. Честно.» (the TNB letters stay)"""
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()
    b[211:232, 22:238] = a[208, 22:238]  # plain light background under the logo square
    _draw(b, "Быстро. Точно. Честно.", RALEWAY, 15, 129.5, 228, (90, 90, 92), max_w=205, wght=600)
    return _out(b, "RGB")


def national_opinion_logo(src):
    """«The National Opinion» (Raleway light + bold) -> «Мнение Нации» (light + bold, same baseline); the
    column logo itself and the same plate in the picture of the column"""
    # (plate area to clear, plate colour sample, cap height, baseline, centre x)
    clear, sample, cap, base, cx = _sized(src, {
        # the Russian name is shorter: capitals 20% larger than the English ones, on the same centre line
        (515, 121): ((15, 38, 500, 92), (20, 250), 42, 81.5, 257.5),
        (1024, 764): ((486, 268, 944, 322), (250, 700), 40, 310.3, 714.5)})
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()
    x0, y0, x1, y1 = clear
    b[y0:y1, x0:x1] = a[sample]
    colour = (92, 94, 95)
    size = cap / _cap_height(_font(RALEWAY, 100, wght=300)) * 100
    w1 = _font(RALEWAY, size, wght=300).getlength("Мнение ")
    w2 = _font(RALEWAY, size, wght=700).getlength("Нации")
    x = cx - (w1 + w2) / 2
    _draw(b, "Мнение ", RALEWAY, cap, x, base, colour, anchor="ls", wght=300)
    _draw(b, "Нации", RALEWAY, cap, x + w1, base, colour, anchor="ls", wght=700)
    return _out(b, "RGB")


RUBIK = "google/rubik/Rubik[wght].ttf"


def police_badge(src):
    """«BONTON / POLICE» on the badge -> «БОНТОН / ПОЛИЦИЯ» (gold, both lines on arcs). The circles were
    fitted to the tops (upper line) and bottoms (lower line) of the original letters."""
    spec = _sized(src, {
        # (zone of the upper line, its circle cx, cy, R (outer edge), cap, arc angle),
        # (zone of the lower line, circle cx, cy, R (baseline, outer side), cap, arc angle)
        (261, 324): (((55, 25, 210, 73), 131, 200, 164, 20, 50), ((65, 221, 200, 258), 133, 61.3, 188.7, 19, 36)),
        (260, 260): (((85, 45, 180, 77), 130, 163, 109, 13, 46), ((90, 166, 172, 190), 131, 61, 123, 12, 35)),
    })
    from scipy import ndimage
    a = np.array(src.convert("RGBA")).astype(float)
    b = a.copy()
    gold = (a[..., 0] > 170) & (a[..., 1] > 130) & (a[..., 2] < 150)
    mask = np.zeros_like(gold)
    for (x0, y0, x1, y1), *_ in spec:
        mask[y0:y1, x0:x1] = gold[y0:y1, x0:x1]
    mask = ndimage.binary_dilation(mask, iterations=2)
    _fill(b, mask, iterations=300)
    gold_rgb = (209, 178, 88)
    (_, cx, cy, R, cap, deg), (_, cx2, cy2, R2, cap2, deg2) = spec
    _arc_text(b, "БОНТОН", RUBIK, cap, cx, cy, R - cap, -90, True, gold_rgb,
              span=np.radians(deg) * (R - cap), wght=700)
    _arc_text(b, "ПОЛИЦИЯ", RUBIK, cap2, cx2, cy2, R2, 90, False, gold_rgb,
              span=np.radians(deg2) * R2, wght=700)
    return _out(b, "RGBA")


MONTSERRAT = "google/montserrat/Montserrat[wght].ttf"


def weather_map(src):
    """Town names on the weather map: HILBERY / WADON / BONTON -> ХИЛБЕРИ / УЭЙДОН / БОНТОН (white bold
    capitals, centred under the dots like the English ones; the glow behind them is soft, so the letters are
    erased by smooth filling)."""
    from scipy import ndimage
    boxes = _sized(src, {
        (1024, 664): {"ХИЛБЕРИ": (390, 272, 472, 284), "УЭЙДОН": (572, 225, 643, 237), "БОНТОН": (404, 470, 483, 482)},
        (1024, 745): {"ХИЛБЕРИ": (391, 273, 472, 285), "УЭЙДОН": (571, 226, 645, 238), "БОНТОН": (404, 472, 485, 484)},
    })
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()
    light = a.min(2) > 150
    mask = np.zeros(light.shape, bool)
    for x0, y0, x1, y1 in boxes.values():
        mask[y0 - 2:y1 + 3, x0 - 2:x1 + 3] = light[y0 - 2:y1 + 3, x0 - 2:x1 + 3]
    _fill(b, ndimage.binary_dilation(mask, iterations=2), iterations=300)
    for text, (x0, y0, x1, y1) in boxes.items():
        _draw(b, text, MONTSERRAT, y1 - y0 + 1, (x0 + x1 + 1) / 2, y1 + 1, (250, 250, 250), wght=800, spacing=0.6)
    return _out(b, "RGB")


FIRA = "google/firasans/FiraSans-SemiBold.ttf"

# side banners of the news site: (erase boxes, lines (text, cap, baseline), anchor x, align, font, axes, colour)
BANNERS = {
    "dbanner_ads_ad_rhosen": ([(15, 924, 278, 1013)],
                              [("Создаём образы.", 26, 954), ("Бит за битом.", 27, 1002)],
                              146, "m", RALEWAY, {"wght": 500}, (216, 221, 221)),
    "dbanner_ads_ad_university": ([(14, 228, 274, 265)], [("Учись для будущего.", 24, 255)],
                                  18, "l", FIRA, {}, (80, 96, 123)),
    "dbanner_ads_ad_bank": ([(30, 202, 284, 287)], [("Надёжнее,", 23, 229), ("чем в сейфе.", 24, 276)],
                            36, "l", RALEWAY, {"wght": 600}, (44, 101, 128)),
    "dbanner_ads_ad_singular": ([(22, 44, 268, 199)],
                                [("В такой день", 35, 84), ("легко", 35, 139), ("влюбиться.", 34, 194)],
                                146, "m", RUBIK, {"wght": 400}, (254, 250, 251)),
}


def banner(name):
    boxes, lines, x, align, font, axes, colour = BANNERS[name]

    def render(src):
        from scipy import ndimage
        a = np.array(src.convert("RGB")).astype(float)
        b = a.copy()
        mask = np.zeros(a.shape[:2], bool)
        for x0, y0, x1, y1 in boxes:
            region = a[y0:y1, x0:x1]
            ink = np.abs(region - np.array(colour, float)).sum(2) < 200  # the lettering (its colour)
            mask[y0:y1, x0:x1] = ink
        _fill(b, ndimage.binary_dilation(mask, iterations=2), iterations=400)
        for text, cap, base in lines:
            _draw(b, text, font, cap, x, base, colour, max_w=258 if align == "m" else 270 - x,
                  anchor=align + "s", **axes)
        return _out(b, "RGB")
    render.__name__ = "banner_" + name
    return render


NOTO_SANS_ITALIC = "google/notosans/NotoSans-Italic[wdth,wght].ttf"


def _wrap(text, font_file, cap, max_w, **axes):
    """split text into lines no wider than max_w at the size giving capitals the height cap"""
    size = cap / _cap_height(_font(font_file, 100, **axes)) * 100
    f = _font(font_file, size, **axes)
    lines, line = [], ""
    for word in text.split():
        test = (line + " " + word).strip()
        if line and f.getlength(test) > max_w:
            lines.append(line)
            line = word
        else:
            line = test
    return lines + [line]


def _wire_title(b, text, font_file, cap, cx, base, colour=(40, 40, 40), seed=7, spacing=0.0, **axes):
    """«THE THOUGHT» style: outline capitals filled with a triangle mesh, centred on cx"""
    from scipy.spatial import Delaunay
    from scipy import ndimage
    k = 3
    h, w = b.shape[:2]
    f1 = _font(font_file, 100, **axes)
    size = cap / _cap_height(f1) * 100
    f = _font(font_file, size * k, **axes)
    widths = [f.getlength(ch) / k for ch in text]
    im = Image.new("L", (w * k, h * k))
    d = ImageDraw.Draw(im)
    x = cx - (sum(widths) + spacing * (len(text) - 1)) / 2
    for ch, cw in zip(text, widths):
        d.text((x * k, base * k), ch, font=f, fill=255, anchor="ls")
        x += cw + spacing
    M = np.array(im) > 127
    rng = np.random.RandomState(seed)
    # points: the outline (every ~9 px) and a jittered grid inside
    edge = M & ~ndimage.binary_erosion(M)
    ey, ex = np.nonzero(edge)
    pts = []
    taken = set()
    for yy, xx in zip(ey, ex):
        key = (yy // (6 * k), xx // (6 * k))
        if key not in taken:
            taken.add(key)
            pts.append((xx, yy))
    step = 8 * k
    dist = ndimage.distance_transform_edt(M)
    for yy in range(0, h * k, step):
        for xx in range(0, w * k, step):
            px, py = xx + rng.uniform(0, step), yy + rng.uniform(0, step)
            if 0 <= int(py) < h * k and 0 <= int(px) < w * k and dist[int(py), int(px)] > 3 * k:
                pts.append((px, py))
    pts = np.array(pts, float)
    tri = Delaunay(pts)
    lines = Image.new("L", (w * k, h * k))
    d = ImageDraw.Draw(lines)
    for t in tri.simplices:
        c = pts[t].mean(0)
        if M[int(c[1]), int(c[0])]:
            d.polygon([tuple(p) for p in pts[t]], outline=255)
    L = np.array(lines) > 0
    L |= edge
    m = np.array(Image.fromarray((L * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)).astype(float) / 255.0
    m = np.clip(m * 1.5, 0, 1)[..., None]
    b[..., :3] = b[..., :3] * (1 - m) + np.array(colour, float) * m


THOUGHT_QUOTE = ("«Если свобода вообще что-то значит, то это право говорить людям то, "
                 "чего они не хотят слышать».")


def thought_header(src):
    """The blog «The Thought» in the news pictures: the Orwell quote, its author, the wireframe title
    «THE THOUGHT» -> «МЫСЛЬ», the pale page text below and (day 4) the headline «THE THOUGHTS ARE FREE!»."""
    from scipy import ndimage
    dy = {(1024, 659): 0, (1024, 762): 84}[(src.width, src.height)]
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()

    def erase(box, tol=40):
        x0, y0, x1, y1 = box
        reg = a[y0:y1, x0:x1]
        bg = np.median(reg.reshape(-1, 3), axis=0)
        ink = np.abs(reg - bg).sum(2) > tol
        mask = np.zeros(a.shape[:2], bool)
        mask[y0:y1, x0:x1] = ink
        _fill(b, ndimage.binary_dilation(mask, iterations=2), iterations=200)

    # the quote and its author (Fira Sans Light Italic; capitals 22, lines 40 apart)
    erase((312, 128 + dy, 1000, 280 + dy), tol=150)
    ink = (86, 80, 72)
    for i, line in enumerate(_wrap(THOUGHT_QUOTE, NOTO_SANS_ITALIC, 22, 610, wght=300, wdth=88)):
        _draw(b, line, NOTO_SANS_ITALIC, 22, 321, 161 + dy + 40 * i, ink, anchor="ls", wght=300, wdth=88)
    _draw(b, "— Джордж Оруэлл", NOTO_SANS_ITALIC, 13, 956, 270 + dy, (114, 108, 101), anchor="rs", wght=300, wdth=88)
    # the title
    _erase(b, (52, 340 + dy, 963, 430 + dy), pad=3)  # vertical gradient: interpolate every column
    _wire_title(b, "МЫСЛЬ", MONTSERRAT, 85, 507, 428 + dy, spacing=48, wght=800)
    # the pale page below (Fira Sans)
    pale = (213, 222, 227)
    erase((245, 480 + dy, 900, min(a.shape[0], 652 + dy)), tol=12)
    _draw(b, "Обзор", "google/firasans/FiraSans-SemiBold.ttf", 25, 253, 512 + dy, pale, anchor="ls")
    _draw(b, "Добро пожаловать в блог «Мысль». Выберите запись ниже.", NOTO_SANS_ITALIC, 17, 253, 576 + dy,
          pale, anchor="ls", max_w=560, wght=600, wdth=88)
    _draw(b, "Запись 20 — Свобода несвободна!", NOTO_SANS_ITALIC, 17, 253, 642 + dy, pale, anchor="ls", wght=400, wdth=88)
    if dy:
        erase((240, 732, 905, 762), tol=12)
        _draw(b, "Запись 19 — Вне контроля (архив)", NOTO_SANS_ITALIC, 17, 253, 754, pale, anchor="ls", wght=400, wdth=88)
        # the headline on the white plate: right aligned, light
        plate = np.zeros(a.shape[:2], bool)
        plate[28:73, 360:1000] = a[28:73, 360:1000].mean(2) < 150
        _fill(b, ndimage.binary_dilation(plate, iterations=2), iterations=200)
        _draw(b, "МЫСЛИ СВОБОДНЫ!", "google/firasans/FiraSans-Light.ttf", 38, 979, 69, (73, 72, 69), anchor="rs")
    return _out(b, "RGB")


NOTO_SANS = "google/notosans/NotoSans[wdth,wght].ttf"


def parges_map(src):
    """Karen's site, the map: THE NATION / PARGES / BONTON / TRIFLITH -> НАЦИЯ / ПАРГЕС / БОНТОН / ТРИФЛИТ
    (Open Sans Bold like lettering; the small names on their plates)"""
    from scipy import ndimage
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()
    dark = a.mean(2) < 120
    mask = np.zeros(dark.shape, bool)
    for x0, y0, x1, y1 in ((116, 120, 222, 167), (63, 182, 277, 229), (372, 264, 578, 313)):
        mask[y0:y1, x0:x1] = dark[y0:y1, x0:x1]
    _fill(b, ndimage.binary_dilation(mask, iterations=3), iterations=400)
    for x0, y0, x1, y1 in ((92, 305, 155, 320), (470, 398, 535, 412)):  # plates: their own colour
        plate = np.median(a[y0:y1, x0:x1].reshape(-1, 3), axis=0)
        b[y0:y1, x0:x1] = plate
    _draw(b, "НАЦИЯ", NOTO_SANS, 40, 169.5, 206, (83, 78, 71), wght=700)
    _draw(b, "ПАРГЕС", NOTO_SANS, 42, 474.5, 310, (68, 65, 66), wght=700)
    _draw(b, "БОНТОН", NOTO_SANS, 10, 123, 318, (66, 60, 58), wght=700, spacing=0.4)
    _draw(b, "ТРИФЛИТ", NOTO_SANS, 10, 502, 410, (55, 55, 55), wght=700, spacing=0.4)
    return _out(b, "RGB")


def _draw_rotated(b, text, font_file, cap, x, base, colour, angle, max_w=None, anchor="ls", **axes):
    """_draw, rotated by angle degrees (counter-clockwise) around the anchor point (x, base)"""
    h, w = b.shape[:2]
    layer = np.zeros((h, w, 3))
    _draw(layer, text, font_file, cap, x, base, (255, 255, 255), max_w, anchor=anchor, **axes)
    im = Image.fromarray(layer[..., 0].astype(np.uint8)).rotate(angle, resample=Image.BICUBIC, center=(x, base))
    m = np.array(im).astype(float)[..., None] / 255.0
    b[..., :3] = b[..., :3] * (1 - m) + np.array(colour, float) * m


def save_parges(src):
    """«SAVE PARGES» -> «СПАСЁМ ПАРГЕС»: the poster (bookmark icon of the Vhart forum; white serif on the
    picture and the red band) and the sign in the riot picture (black slab serif, tilted)"""
    from scipy import ndimage
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()
    if src.size == (260, 260):
        mask = np.zeros(a.shape[:2], bool)
        mask[158:243, 36:226] = a[158:243, 36:226].min(2) > 150
        _fill(b, ndimage.binary_dilation(mask, iterations=2), iterations=300)
        serif = "google/notoserif/NotoSerif[wdth,wght].ttf"
        _draw(b, "СПАСЁМ", serif, 32, 125, 194, (250, 250, 250), max_w=225, wght=600, wdth=88)
        _draw(b, "ПАРГЕС", serif, 32, 131, 239, (250, 250, 250), max_w=225, wght=600, wdth=88)
    else:
        mask = np.zeros(a.shape[:2], bool)
        mask[28:76, 0:212] = a[28:76, 0:212].mean(2) < 170
        _fill(b, ndimage.binary_dilation(mask, iterations=2), iterations=300)
        _draw_rotated(b, "СПАСЁМ ПАРГЕС!", ROBOTO_SLAB, 21, 1, 71, (25, 25, 25), 6.0, max_w=212, wght=800)
    return _out(b, "RGB")


def _draw_slanted(b, text, font_file, cap, x, base, colour, slant=0.2, max_w=None, anchor="ms", **axes):
    """_draw with the letters slanted to the right (an italic made from an upright font): x' = x + slant*(base - y)"""
    h, w = b.shape[:2]
    layer = np.zeros((h, w, 3))
    _draw(layer, text, font_file, cap, x, base, (255, 255, 255), max_w, anchor=anchor, **axes)
    k = 4
    im = Image.fromarray(layer[..., 0].astype(np.uint8)).resize((w * k, h * k), Image.BICUBIC)
    # output (X, Y) takes input (X + slant*(Y - base), Y)
    im = im.transform(im.size, Image.AFFINE, (1, slant, -slant * base * k, 0, 1, 0), resample=Image.BICUBIC)
    m = np.array(im.resize((w, h), Image.LANCZOS)).astype(float)[..., None] / 255.0
    b[..., :3] = b[..., :3] * (1 - m) + np.array(colour, float) * m


def peoples_voice_sign(src):
    """the placard in the riot picture: «WE ARE THE / PEOPLE'S / VOICE» -> «МЫ — / ГОЛОС / НАРОДА»
    (white heavy slab italic on the maroon plate)"""
    from scipy import ndimage
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()
    mask = np.zeros(a.shape[:2], bool)
    mask[126:223, 168:326] = a[126:223, 168:326].min(2) > 150
    _fill(b, ndimage.binary_dilation(mask, iterations=3), iterations=400)
    white = (247, 245, 242)
    _draw_slanted(b, "МЫ —", ROBOTO_SLAB, 15, 247, 144, white, max_w=150, wght=900)
    _draw_slanted(b, "ГОЛОС", ROBOTO_SLAB, 21, 247, 177, white, max_w=150, wght=900)
    _draw_slanted(b, "НАРОДА", ROBOTO_SLAB, 30, 249, 219, white, max_w=145, wght=900)
    return _out(b, "RGB")


def _perspective_coeffs(dst, src):
    """coefficients for Image.transform(PERSPECTIVE) mapping output points dst to input points src"""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float))


def _draw_quad(b, text, font_file, quad, colour, k=4, **axes):
    """Draw text whose capital letters fill the quadrilateral quad (top-left, top-right, bottom-right,
    bottom-left: cap line and baseline), e.g. lettering seen in perspective."""
    h, w = b.shape[:2]
    f = _font(font_file, 200, **axes)
    cap = _cap_height(f)
    tw = f.getlength(text)
    desc = int(cap * 0.4)  # room below the baseline (the tail of Ц, Щ, Д)
    strip = Image.new("L", (int(tw) + 2, int(cap) + 2 + desc))
    ImageDraw.Draw(strip).text((1, cap + 1), text, font=f, fill=255, anchor="ls")
    sw = strip.size[0]
    dst = [(x * k, y * k) for x, y in quad]
    coeffs = _perspective_coeffs(dst, [(1, 1), (sw - 1, 1), (sw - 1, cap + 1), (1, cap + 1)])
    big = strip.transform((w * k, h * k), Image.PERSPECTIVE, tuple(coeffs), resample=Image.BICUBIC)
    m = np.array(big.resize((w, h), Image.LANCZOS)).astype(float)[..., None] / 255.0
    b[..., :3] = b[..., :3] * (1 - m) + np.array(colour, float) * m


def border_sign(src):
    """the border crossing: «THE NATION» on the canopy (seen in perspective) -> «НАЦИЯ»"""
    from scipy import ndimage
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    top_edge = 118 - (xx - 215) * (18 / 285)  # the light upper edge of the canopy
    area = (xx > 225) & (xx < 576) & (yy > top_edge + 7) & (yy < 167)
    mask = area & (a.min(2) > 150)
    _fill(b, ndimage.binary_dilation(mask, iterations=2) & area, iterations=300)
    # cap line and baseline of the English text: x 233 -> 569, top 136 -> 114, bottom 163 -> 150
    _draw_quad(b, "НАЦИЯ", "google/montserrat/Montserrat[wght].ttf",
               [(300, 131.6), (520, 117.2), (520, 151.9), (300, 160.4)], (226, 222, 222), wght=800)
    return _out(b, "RGB")


def movie_poster(src):
    """«A Hundred Grey Shadows» poster (Timelines and the news site): the title «СОТНЯ СЕРЫХ / ТЕНЕЙ» (serif
    italic, as in the texts of the mod: «Сотня серых теней»), «14 ФЕВРАЛЯ 2018» and the credits; the studio
    name Rhubarb Productions stays"""
    from scipy import ndimage
    # q: scale against the 1024x800 layout, (dx, dy): its shift
    q = {(1024, 800): 1.0, (862, 1024): 1.275}[src.size]  # scale against the 1024x800 layout
    a = np.array(src.convert("RGB")).astype(float)
    b = a.copy()
    if q == 1:
        title, bottom = (40, 156, 70, 600), (676, 750, 110, 550)
        t1, t2, cx, valentine, credits, ccx = (40, 82), (40, 152.5), 336, (27, 708), (14, 746), 330.5
    else:
        title, bottom = (50, 201, 60, 800), (866, 959, 100, 780)
        t1, t2, cx, valentine, credits, ccx = (51, 105), (51, 195), 400, (35, 907), (18, 955), 423
    mask = np.zeros(a.shape[:2], bool)
    for y0, y1, x0, x1 in (title, bottom):
        mask[y0:y1, x0:x1] = a[y0:y1, x0:x1].mean(2) < 85
    # only the strokes: the large dark facets of the hair under the title stay (opening keeps blobs)
    mask &= ~ndimage.binary_opening(mask, structure=np.ones((11, 11)))
    # the larger poster has a light halo around the letters: grow over it
    _median_fill(b, ndimage.binary_dilation(mask, iterations=2 if q == 1 else 5), win=5)
    ink = (42, 42, 40)
    serif = "google/notoserif/NotoSerif-Italic[wdth,wght].ttf"
    _draw(b, "СОТНЯ СЕРЫХ", serif, t1[0], cx, t1[1], ink, max_w=560 * q, wght=400)
    _draw(b, "ТЕНЕЙ", serif, t2[0], cx, t2[1], ink, wght=400)
    _draw(b, "14 ФЕВРАЛЯ 2018", "google/lato/Lato-Bold.ttf", valentine[0], ccx, valentine[1], (44, 44, 42))
    _draw(b, "СЦЕНАРИЙ И РЕЖИССУРА: СУМИШИ АРАН", "google/lato/Lato-Bold.ttf", credits[0], ccx, credits[1],
          (64, 64, 63), max_w=425 * q)
    return _out(b, "RGB")


# Texture2D name -> renderer
RENDERERS = {
    "ibtn_showconflict": show_conflict,
    "listener_phone_equalizer_end": call_ended,
    "insider_rabanpc_wallpaper": peoples_voice_wallpaper,
    "website_party": party_logo,
    "header_image_party_emblem": party_logo,
    "website_pargesianarmy": pargesian_army_logo,
    "website_pargesianarmy_home_image_pargesianarmy_logo": pargesian_army_logo,
    "website_school": school_logo,
    "website_prava": prava_city_logo,
    "website_immigration": immigration_logo,
}
RENDERERS.update({name: _seal_renderer(name) for name in SEALS})
RENDERERS["website_beholder"] = tnb_logo
RENDERERS["header_image_police_logo"] = police_badge
RENDERERS["website_police"] = police_badge
RENDERERS.update({name: banner(name) for name in BANNERS})
RENDERERS["website_beholder_thought_image_beholder_thought"] = thought_header
RENDERERS["website_karenssite_latestcases_image_karenssite_story2"] = parges_map
RENDERERS["website_vhart"] = save_parges
RENDERERS["website_timelines_ilyawantstoleave_image_timelines_movieposter"] = movie_poster
RENDERERS["website_beholder_movie1_image_beholder_movieposter"] = movie_poster
RENDERERS["website_beholder_home_image_beholder_movieposter"] = movie_poster
RENDERERS["website_beholder_terrorists_image_beholder_border"] = border_sign
RENDERERS["website_socialite_davidjohns_image_socialite_riot"] = peoples_voice_sign
RENDERERS["website_blabber_ilyawantstoleave_image_blabber_riot"] = save_parges
RENDERERS["website_beholder_headlinesday4ninacaughtupdate_image_beholder_thought"] = thought_header
RENDERERS["website_beholder_weatherwarning_image_beholder_badweather"] = weather_map
RENDERERS["website_beholder_headlinesday2_image_beholder_badweather"] = weather_map
RENDERERS["website_beholder_opinion2_image_beholder_tnbcolumnlogo"] = national_opinion_logo
RENDERERS["website_beholder_headlinesday3Aupdate_image_beholder_opinion2"] = national_opinion_logo
RENDERERS["header_image_immigration_logo"] = _seal_renderer("header_image_immigration_logo", grow=4.0)
# Ampleford's PC: the light version of the seal with dark letters (fitted to the outer edge, 184 on the reference)
SEALS["insider_amplesfordspc_wallpaper"] = (512.0, 396.0, 174.8 * 172.5 / 184)
RENDERERS["insider_amplesfordspc_wallpaper"] = _seal_renderer("insider_amplesfordspc_wallpaper", dark=True, grow=2.5)

# the other original textures of the file being patched, by name (set by apply_bundles.py), for pictures made
# from another one
SIBLINGS = {}


def locked_phone(src):
    """The locked phone screen: its wallpaper (insider_baytephone_wallpaper, same bundle) scaled by 1.286 from
    x 179.5 and blurred (sigma 4.23; fitted, mean squared error 0.17). The same blur of the difference between
    the translated and the original wallpaper is added, so the blurred seal reads «ПРАВИТЕЛЬСТВО / НАЦИИ»."""
    from scipy import ndimage
    wall = SIBLINGS["insider_baytephone_wallpaper"]
    o = np.array(wall.convert("RGB")).astype(float)
    t = np.array(RENDERERS["insider_baytephone_wallpaper"](wall).convert("RGB")).astype(float)
    a = np.array(src.convert("RGB")).astype(float)
    h, w = a.shape[:2]
    scale, x0, y0, sigma = 1.28599, 179.463, 0.0, 4.2333
    yy, xx = np.mgrid[0:h, 0:w]
    sy, sx = y0 + yy / scale, x0 + xx / scale
    d = np.stack([ndimage.map_coordinates(t[..., c] - o[..., c], [sy, sx], order=1, mode="nearest")
                  for c in range(3)], -1)
    return _out(a + ndimage.gaussian_filter(d, (sigma, sigma, 0)), "RGB")


RENDERERS["insider_baytephone_desktopencrypterror_image_insider_baytephone_desktopencrypted"] = locked_phone
RENDERERS["insider_baytephone_desktopencrypt_image_insider_baytephone_desktopencrypted"] = locked_phone

# the same pictures again under other names (pixel for pixel the same textures, on other pages of the sites)
COPIES = {
    "header_image_pargesianarmy_logo": "website_pargesianarmy_home_image_pargesianarmy_logo",
    "website_blabber_ilyawantstoleavewithkaren_image_blabber_riot": "website_blabber_ilyawantstoleave_image_blabber_riot",
    "website_blabber_rabanmarried_image_blabber_riot": "website_blabber_ilyawantstoleave_image_blabber_riot",
    "website_blabber_karenmarried_image_blabber_riot": "website_blabber_ilyawantstoleave_image_blabber_riot",
    "website_timelines_ilya_image_timelines_movieposter": "website_timelines_ilyawantstoleave_image_timelines_movieposter",
    "website_beholder_headlinesday3A_image_beholder_nationalopinion2": "website_beholder_headlinesday3Aupdate_image_beholder_opinion2",
    "website_beholder_headlinesday3B_image_beholder_opinion2": "website_beholder_headlinesday3Aupdate_image_beholder_opinion2",
    "website_beholder_headlinesday3Bupdate_image_beholder_opinion2": "website_beholder_headlinesday3Aupdate_image_beholder_opinion2",
    "website_beholder_opinion1_image_beholder_tnbcolumnlogo": "website_beholder_opinion2_image_beholder_tnbcolumnlogo",
    "website_beholder_opinion2malldestroyed_image_beholder_tnbcolumnlogo": "website_beholder_opinion2_image_beholder_tnbcolumnlogo",
    "website_beholder_terrorists_image_beholder_olegsoldier": "website_beholder_terrorists_image_beholder_border",
}
RENDERERS.update({copy: RENDERERS[name] for copy, name in COPIES.items()})

# the UI labels the game needs translated; everything else (logos, seals, banners, posters, maps: text inside the
# pictures) is optional, the installer offers it as a choice (ORWELL_IMAGES=base builds the files without it)
BASE = {"ibtn_showconflict", "listener_phone_equalizer_end"}
OPTIONAL = set(RENDERERS) - BASE


def selected(name):
    """Is this texture redrawn in the current build (ORWELL_IMAGES=base: only the UI labels)?"""
    if name not in RENDERERS:
        return False
    return name in BASE or os.environ.get("ORWELL_IMAGES", "all") != "base"
