from render import font

import numpy as np
from PIL import Image, ImageDraw

# CIE 1931 2° 观察者光谱轨迹坐标 (x,y) · 380-700nm / 5nm
LAMBDA = [
    (380, 0.17411, 0.00496),
    (385, 0.17401, 0.00498),
    (390, 0.1738, 0.00492),
    (395, 0.17356, 0.00492),
    (400, 0.17334, 0.0048),
    (405, 0.17302, 0.00478),
    (410, 0.17258, 0.0048),
    (415, 0.17209, 0.00483),
    (420, 0.17141, 0.0051),
    (425, 0.1703, 0.00579),
    (430, 0.16888, 0.0069),
    (435, 0.1669, 0.00856),
    (440, 0.16441, 0.01086),
    (445, 0.1611, 0.01379),
    (450, 0.15664, 0.0177),
    (455, 0.15099, 0.02274),
    (460, 0.14396, 0.0297),
    (465, 0.1355, 0.03988),
    (470, 0.12412, 0.0578),
    (475, 0.10959, 0.08684),
    (480, 0.09129, 0.1327),
    (485, 0.06871, 0.20072),
    (490, 0.04539, 0.29498),
    (495, 0.02346, 0.4127),
    (500, 0.00817, 0.53842),
    (505, 0.00386, 0.65482),
    (510, 0.01387, 0.75019),
    (515, 0.03885, 0.81202),
    (520, 0.0743, 0.8338),
    (525, 0.11416, 0.82621),
    (530, 0.15472, 0.80586),
    (535, 0.19288, 0.78163),
    (540, 0.22962, 0.75433),
    (545, 0.26578, 0.72432),
    (550, 0.3016, 0.69231),
    (555, 0.33736, 0.65885),
    (560, 0.3731, 0.62445),
    (565, 0.40874, 0.58961),
    (570, 0.44406, 0.55471),
    (575, 0.47877, 0.5202),
    (580, 0.51249, 0.48659),
    (585, 0.54479, 0.45443),
    (590, 0.57515, 0.42423),
    (595, 0.60293, 0.3965),
    (600, 0.62704, 0.37249),
    (605, 0.64823, 0.35139),
    (610, 0.66576, 0.33401),
    (615, 0.68008, 0.31975),
    (620, 0.6915, 0.30834),
    (625, 0.70061, 0.2993),
    (630, 0.70792, 0.29203),
    (635, 0.71403, 0.28593),
    (640, 0.71903, 0.28093),
    (645, 0.72303, 0.27695),
    (650, 0.72599, 0.27401),
    (655, 0.72827, 0.27173),
    (660, 0.72997, 0.27003),
    (665, 0.73109, 0.26891),
    (670, 0.73199, 0.26801),
    (675, 0.73272, 0.26728),
    (680, 0.73342, 0.26658),
    (685, 0.73405, 0.26595),
    (690, 0.73439, 0.26561),
    (695, 0.73459, 0.26541),
    (700, 0.73469, 0.26531),
]

_l = np.array([t[0] for t in LAMBDA], float)
_x = np.array([t[1] for t in LAMBDA])
_y = np.array([t[2] for t in LAMBDA])
WX, WY = 0.3127, 0.3290
_a = np.degrees(np.unwrap(np.radians(np.degrees(np.arctan2(-(_y - WY), _x - WX)) % 360)))
_bl = _a - _a[0]
B1 = _bl[-1]
M = np.array([[0.4124, 0.3576, 0.1913], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
EDGE = np.arange(380, 701, 1.0)
CTR = (EDGE[:-1] + EDGE[1:]) / 2


def s2l(c):
    c = np.asarray(c, np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.04045) / 1.055) ** 2.4)


def wl_rgb(w):
    if w < 440:   r, g, b = -(w - 440) / 60, 0, 1
    elif w < 490: r, g, b = 0, (w - 440) / 50, 1
    elif w < 510: r, g, b = 0, 1, -(w - 510) / 20
    elif w < 580: r, g, b = (w - 510) / 70, 1, 0
    elif w < 645: r, g, b = 1, -(w - 645) / 65, 0
    else:         r, g, b = 1, 0, 0
    f = 1.0 if 420 <= w <= 700 else (0.3 + 0.7 * (w - 380) / 40 if w < 420 else 0.15)
    return np.clip(np.array([r, g, b]) * f, 0, 1)


def analyse(rgb, step=2, smooth=1.2):
    img = np.asarray(rgb)[::step, ::step]
    lin = s2l(img).reshape(-1, 3)
    X, Y, Z = (lin @ M.T).T
    S = X + Y + Z + 1e-9
    x, y = X / S, Y / S
    dx, dy = x - WX, y - WY
    b = (np.degrees(np.arctan2(-dy, dx)) - _a[0]) % 360
    C = np.hypot(dx, dy)
    neu = (C < 0.012) | (Y < 0.0025)
    spec = (b <= B1) & ~neu
    n = b.size
    hist = np.histogram(np.interp(b[spec], _bl, _l), bins=EDGE)[0].astype(np.float32)
    k = np.exp(-0.5 * (np.arange(-4, 5) / smooth) ** 2)
    dens = np.convolve(hist, k / k.sum(), mode="same") / n * 100
    pk = CTR[int(np.argmax(dens))] if dens.max() > 0.02 else 0.0
    return dict(dens=dens, peak=pk, pur=(~neu & ~spec).sum() / n * 100,
                neu=neu.sum() / n * 100)


def wave_chart(dens, w, h, bg=(18, 18, 21)):
    """波长分布图：左 700nm 右 380nm，填充用对应光谱色。"""
    mx = len(dens)
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    pl, pb, pt, pr = 54, 30, 10, 14
    x0, y0, x1, y1 = pl, pt, w - pr, h - pb
    pw, ph = x1 - x0, y1 - y0
    for i in range(6):
        d.line([(x0 + pw * i // 5, y0), (x0 + pw * i // 5, y1)], fill=(40, 40, 47))
    for i in range(5):
        d.line([(x0, y0 + ph * i // 4), (x1, y0 + ph * i // 4)], fill=(40, 40, 47))
    d.rectangle([x0, y0, x1, y1], outline=(118, 118, 128))
    vm = max(float(dens.max()), 1e-6)
    xs = [x0 + i * pw / max(mx - 1, 1) for i in range(mx)]
    ys = [y1 - dens[i] / vm * ph for i in range(mx)]
    for i in range(mx - 1):
        wl = 700 - i * (700 - 380) / max(mx - 1, 1)
        c = wl_rgb(wl) * 0.55 * 255
        d.polygon([(xs[i], ys[i]), (xs[i + 1], ys[i + 1]), (xs[i + 1], y1), (xs[i], y1)],
                  fill=tuple(int(v) for v in c))
    d.line(list(zip(xs, ys)), fill=(235, 235, 240), width=1)
    f = font(9)
    for i, wl in enumerate(range(700, 379, -64)):
        d.text((x0 + pw * i / 5, y1 + 4), str(wl), font=f, fill=(155, 155, 165), anchor="ma")
    d.text((x0 - 5, y0 - 3), "像素密度", font=f, fill=(140, 140, 150), anchor="ls")
    d.text((x1 - 2, y0 - 3), "波长 nm（700 → 380，频率递增）", font=f, fill=(140, 140, 150), anchor="ra")
    return im
