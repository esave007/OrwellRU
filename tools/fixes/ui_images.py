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


# Texture2D name -> renderer
RENDERERS = {
    "ibtn_showconflict": show_conflict,
    "listener_phone_equalizer_end": call_ended,
    "insider_rabanpc_wallpaper": peoples_voice_wallpaper,
}
