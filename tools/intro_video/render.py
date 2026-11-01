"""Re-render Orwell 2 intro with Russian burned-in text.

Reads intro.mp4, replaces subtitle boxes (cues.json) and the animated
top captions (tracked in top.json), writes intro_ru.mp4 (both in the current directory).
Usage: render.py                      -> full encode (needs ffmpeg in PATH)
       render.py <f1,f2,...> <dir>    -> only dump these frame numbers as PNG for preview
cues.json: frame ranges, colours and old box geometry of every burned-in subtitle (from detect.py)
top.json:  per-frame bounding boxes of the animated captions at the top (from dtop2.py)
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1920, 1080
FONT = os.path.join(HERE, "..", "..", "fonts", "Ubuntu-Regular.ttf")
SUB_FONT = ImageFont.truetype(FONT, 35)
TOP_FONT = ImageFont.truetype(FONT, 34)
BOX = (11, 16, 26)
COL = {"p": (237, 162, 175), "w": (177, 197, 217)}
LINE_PITCH = 46
PAD_X, PAD_Y = 11, 10

cues = json.load(open(os.path.join(HERE, "cues.json"), encoding="utf-8"))
top = json.load(open(os.path.join(HERE, "top.json")))


def cap_metrics(font):
    b = font.getbbox("Н")
    return b[1], b[3]  # cap top offset, baseline offset (from draw origin)


SUB_CAP_TOP, SUB_BASE = cap_metrics(SUB_FONT)
SUB_CAP_H = SUB_BASE - SUB_CAP_TOP
TOP_CAP_TOP, TOP_BASE = cap_metrics(TOP_FONT)


def render_sub(cue):
    """Pre-render a cue: returns (x0, y0, rgba ndarray) covering old box and new text."""
    lines = cue["t"]
    n = len(lines)
    widths = [SUB_FONT.getlength(l) for l in lines]
    tw = max(widths)
    th = SUB_CAP_H + (n - 1) * LINE_PITCH
    cy = 966  # vertical centre of all original boxes
    ty0 = cy - th / 2  # cap top of first line
    bx0 = int(960 - tw / 2 - PAD_X)
    bx1 = int(960 + tw / 2 + PAD_X)
    by0 = int(ty0 - PAD_Y)
    by1 = int(ty0 + th + PAD_Y)
    ox0, oy0, ox1, oy1 = cue["box"]
    # always cover the old box completely (+2px for anti-aliased edges)
    x0, y0 = min(bx0, ox0 - 2), min(by0, oy0 - 2)
    x1, y1 = max(bx1, ox1 + 2), max(by1, oy1 + 2)
    im = Image.new("RGBA", (x1 - x0, y1 - y0), BOX + (255,))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        lx = 960 - widths[i] / 2 - x0
        ly = ty0 + i * LINE_PITCH - SUB_CAP_TOP - y0
        d.text((lx, ly), l, font=SUB_FONT, fill=COL[cue["c"]] + (255,))
    return x0, y0, np.asarray(im).astype(np.float32)


SUBS = []
for c in cues:
    SUBS.append((c["f"][0], c["f"][1]) + render_sub(c))


def text_layer(text, font, cap_top_y, alpha=1.0, cx=960):
    """Full-width RGBA strip for one centred line whose cap top is at cap_top_y."""
    w = font.getlength(text)
    im = Image.new("L", (W, 80), 0)
    ImageDraw.Draw(im).text((cx - w / 2, 20 - TOP_CAP_TOP), text, font=font, fill=int(255 * alpha))
    return im, int(round(cap_top_y)) - 20


def composite_white(frame, mask_img, y_off, gain=1.0):
    m = np.asarray(mask_img).astype(np.float32) / 255.0 * gain
    m = np.clip(m, 0, 1)
    h = m.shape[0]
    ys, ye = max(0, y_off), min(H, y_off + h)
    if ye <= ys:
        return
    m = m[ys - y_off:ye - y_off, :, None]
    reg = frame[ys:ye].astype(np.float32)
    frame[ys:ye] = (reg * (1 - m) + 255 * m).astype(np.uint8)


def erase_black(frame, y0, y1, x0, x1, pad=5):
    frame[max(0, y0 - pad):y1 + pad + 1, max(0, x0 - pad):x1 + pad + 1] = 0


def erase_interp(frame, y0, y1, x0, x1, pad=8):
    """Fill rectangle by vertical interpolation between rows just outside it (smooth gradient bg)."""
    y0, y1 = y0 - pad, y1 + pad
    x0, x1 = x0 - pad, x1 + pad
    above = frame[y0 - 4:y0].astype(np.float32).mean(axis=0)
    below = frame[y1 + 1:y1 + 5].astype(np.float32).mean(axis=0)
    n = y1 - y0 + 1
    t = np.linspace(0, 1, n)[:, None, None]
    fill = above[None] * (1 - t) + below[None] * t
    frame[y0:y1 + 1, x0:x1 + 1] = fill[:, x0:x1 + 1].astype(np.uint8)


def lines_at(f):
    """Classify tracked top-text lines for frame f."""
    res = {}
    for y0, y1, x0, x1, mx, cnt in top[f] if f < len(top) else []:
        if y0 >= 555 and f < 380:
            continue  # loading hexagons, keep
        if x0 < 760:
            res["L2"] = (y0, y1, x0, x1, mx)
        elif f < 433:
            res["L1"] = (y0, y1, x0, x1, mx)
        else:
            res["WEL"] = (y0, y1, x0, x1, mx)
    return res


L1_PREFIX, L1_A, L1_B = "ПОДКЛЮЧЕН", "ИЕ", "О."
L2_TEXT = "К ПОДСЕТИ ORWELL «УПРАВЛЕНИЯ»"
WEL_TEXT = "ДОБРО ПОЖАЛОВАТЬ, АГЕНТ."
MORPH0, MORPH1 = 350, 388


def draw_L1(frame, y0, alpha, f):
    full_a = L1_PREFIX + L1_A
    full_b = L1_PREFIX + L1_B
    # keep the prefix fixed: centre on the longer word so the root doesn't jump
    wa, wb = TOP_FONT.getlength(full_a), TOP_FONT.getlength(full_b)
    left = 960 - max(wa, wb) / 2
    k = 0.0 if f < MORPH0 else 1.0 if f >= MORPH1 else (f - MORPH0) / (MORPH1 - MORPH0)
    pre_w = TOP_FONT.getlength(L1_PREFIX)
    for text, a in ((L1_PREFIX, 1.0), (L1_A, 1 - k), (L1_B, k)):
        if a <= 0:
            continue
        x = left if text == L1_PREFIX else left + pre_w
        im = Image.new("L", (W, 80), 0)
        ImageDraw.Draw(im).text((x, 20 - TOP_CAP_TOP), text, font=TOP_FONT, fill=255)
        composite_white(frame, im, int(round(y0)) - 20, alpha * a)


def process_top(frame, f):
    if f < 12 or f > 529:
        return
    ls = lines_at(f)
    if f < 433:
        for k in ("L1", "L2"):
            if k in ls:
                y0, y1, x0, x1, _ = ls[k]
                erase_black(frame, y0, y1, x0, x1)
        if "L1" in ls:
            y0, _, _, _, mx = ls["L1"]
            draw_L1(frame, y0 + 1, mx / 255.0, f)
        if "L2" in ls:
            y0, _, _, _, mx = ls["L2"]
            im, off = text_layer(L2_TEXT, TOP_FONT, y0 + 2)
            composite_white(frame, im, off, mx / 255.0)
        return
    if "WEL" not in ls:
        return
    y0, y1, x0, x1, mx = ls["WEL"]
    erase_interp(frame, y0, y1, min(x0, 700), max(x1, 1220), pad=10)
    alpha = min(1.0, mx / 247.0)
    w = TOP_FONT.getlength(WEL_TEXT)
    im = Image.new("L", (int(w) + 40, 80), 0)
    ImageDraw.Draw(im).text((20, 20 - TOP_CAP_TOP), WEL_TEXT, font=TOP_FONT, fill=255)
    gain = alpha
    if 519 <= f <= 522:  # glow before collapse
        glow = im.filter(ImageFilter.GaussianBlur(6))
        im = Image.fromarray(np.clip(np.asarray(im).astype(np.float32) + np.asarray(glow) * 1.6, 0, 255).astype(np.uint8))
    if f >= 523:  # horizontal collapse into the logo seed
        orig_w = 300.0
        k = (x1 - x0) / orig_w
        nw = max(4, int(im.width * k))
        im = im.resize((nw, im.height), Image.BILINEAR)
        a = np.asarray(im).astype(np.float32)
        L = int((1 - k) * 36) + 1  # horizontal motion blur, grows as it collapses
        pad = np.pad(a, ((0, 0), (L, L)))
        cs = np.cumsum(pad, axis=1)
        a = (cs[:, L * 2:] - cs[:, :-L * 2]) / (2 * L)
        a = a[:, :im.width]
        im = Image.fromarray(np.clip(a * 1.6, 0, 255).astype(np.uint8))
    strip = Image.new("L", (W, 80), 0)
    strip.paste(im, (int(960 - im.width / 2), 0))
    composite_white(frame, strip, int(round(y0 + 2)) - 20, gain)


def process_subs(frame, f):
    for f0, f1, x0, y0, rgba in SUBS:
        if f0 <= f < f1:
            h, w = rgba.shape[:2]
            a = rgba[:, :, 3:4] / 255.0
            reg = frame[y0:y0 + h, x0:x0 + w].astype(np.float32)
            frame[y0:y0 + h, x0:x0 + w] = (reg * (1 - a) + rgba[:, :, :3] * a).astype(np.uint8)


def main():
    preview = len(sys.argv) > 1
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "intro.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    if preview:
        want = set(int(x) for x in sys.argv[1].split(",")); outdir = sys.argv[2]; fa, fb = min(want), max(want)
    else:
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y",
                                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                                "-i", "intro.mp4", "-map", "0:v", "-map", "1:a", "-c:a", "copy",
                                "-c:v", "libx264", "-profile:v", "baseline", "-level", "4.0", "-pix_fmt", "yuv420p",
                                "-preset", "slow", "-crf", "14", "-maxrate", "8M", "-bufsize", "16M",
                                "-movflags", "+faststart", "intro_ru.mp4"], stdin=subprocess.PIPE)
    f = 0
    size = W * H * 3
    while True:
        b = dec.stdout.read(size)
        if len(b) < size:
            break
        if preview and f > fb:
            break
        if preview and f not in want:
            f += 1
            continue
        frame = np.frombuffer(b, np.uint8).reshape(H, W, 3).copy()
        process_top(frame, f)
        process_subs(frame, f)
        if preview:
            Image.fromarray(frame).save(f"{outdir}/{f:04d}.png")
        else:
            enc.stdin.write(frame.tobytes())
        f += 1
    dec.stdout.close()
    if not preview:
        enc.stdin.close()
        enc.wait()
    print("frames", f)


main()
