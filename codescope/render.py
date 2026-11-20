import glob
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BG = (18, 18, 21)
GRID = (40, 40, 47)
AXIS = (118, 118, 128)
COL = {"R": (252, 92, 92), "G": (96, 220, 120), "B": (98, 148, 255), "Y": (226, 226, 232)}
_CJK = ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhl.ttc"]
_font = None


def font(size):
    global _font
    if _font is None:
        _font = ""
        for p in _CJK:
            if os.path.exists(p):
                _font = p
                break
        if not _font:
            g = sorted(glob.glob("/usr/share/fonts/**/NotoSansCJK*.ttc", recursive=True))
            _font = g[0] if g else ""
    try:
        return ImageFont.truetype(_font or "arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def zh(s, en):
    return s if _font else en


def curve(v, ph, log, peak):
    if log:
        s = np.log10(np.maximum(v, 1)) / max(np.log10(peak), 1e-6)
    else:
        s = v / peak
    return np.clip(s * ph, 0, ph)


def chart(res, bits, binw, w=760, h=300, log=False, ss=1):
    W, H = w * ss, h * ss
    pl, pb, pt, pr = 54 * ss, 30 * ss, 10 * ss, 14 * ss
    x0, y0, x1, y1 = pl, pt, W - pr, H - pb
    pw, ph = x1 - x0, y1 - y0

    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for i in range(6):
        gx = x0 + pw * i // 5
        d.line([(gx, y0), (gx, y1)], fill=GRID, width=ss)
    for i in range(5):
        gy = y0 + ph * i // 4
        d.line([(x0, gy), (x1, gy)], fill=GRID, width=ss)

    d.rectangle([x0, y0, x1, y1], outline=AXIS, width=1)
    vals = {k: np.asarray(res[k], np.float64) for k in "RGBY"}
    peak = max(float(v.max()) for v in vals.values()) or 1.0

    for k in "RGB":
        v = vals[k]
        nb = v.size
        hh = curve(v, ph, log, peak)
        xs = [x0 + i * pw / max(nb - 1, 1) for i in range(nb)]
        ys = [y1 - hh[i] for i in range(nb)]
        pts = list(zip(xs, ys)) + [(x1, y1), (x0, y1)]
        dark = tuple(int(c * 0.55) for c in COL[k])
        d.polygon(pts, fill=dark)
        d.line(list(zip(xs, ys)), fill=COL[k], width=ss)

    v = vals["Y"]
    nb = v.size
    hh = curve(v, ph, log, peak)
    xs = [x0 + i * pw / max(nb - 1, 1) for i in range(nb)]
    d.line(list(zip(xs, [y1 - hh[i] for i in range(nb)])), fill=COL["Y"], width=ss)

    f, fs = font(11 * ss), font(9 * ss)
    mx = 1 << bits
    for i in range(6):
        cx = x0 + pw * i // 5
        d.text((cx, y1 + 4 * ss), str(mx * i // 5), font=fs, fill=(155, 155, 165), anchor="ma")
    for i in range(5):
        cx = x0 + pw * i // 4
        d.text((cx, y1 + 15 * ss), f"{25*i}%", font=fs, fill=(96, 96, 106), anchor="ma")
    if binw > 1:
        d.text((x1, y1 + 15 * ss), zh(f"每格 {binw} 码值", f"{binw} codes/bin"),
               font=fs, fill=(118, 118, 130), anchor="ra")
    d.text((x0 - 5 * ss, y0 - 3 * ss), zh("像素数", "px"), font=fs, fill=(140, 140, 150), anchor="ls")
    d.text((x1 - 2 * ss, y0 - 3 * ss), zh(f"{bits} bit · 码值 0–{mx}", f"{bits} bit · code 0-{mx}"),
           font=fs, fill=(140, 140, 150), anchor="rs")
    lx = x0 + 10 * ss
    for k in "RGB":
        d.rectangle([lx, y1 - 13 * ss, lx + 11 * ss, y1 - 8 * ss], fill=COL[k])
        d.text((lx + 14 * ss, y1 - 15 * ss), k, font=f, fill=(200, 200, 210))
        lx += 36 * ss
    return im
