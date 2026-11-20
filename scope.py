import json
import os
import sys

from resolve_link import Link

import numpy as np
from PIL import Image
from cie_table import LAMBDA

# ---------------- CIE 1931 ----------------
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


SPEC = np.array([wl_rgb(w) for w in CTR])


def analyse(rgb, step=2, smooth=1.2):
    img = rgb[::step, ::step]
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
                neu=neu.sum() / n * 100, mean=img.mean())


def render(dens, w=570, h=229):
    ymax = max(dens.max() * 1.14, 0.9)
    out = np.empty((h, w, 3), np.uint8)
    band = (np.arange(w) * 320 // w)
    out[:] = (20, 20, 23)
    for lo, hi, t in ((0, 120, (16, 26, 58)), (120, 200, (14, 36, 24)), (200, 320, (48, 18, 18))):
        x0, x1 = lo * w // 320, hi * w // 320
        out[:, x0:x1] = t
    hh = np.clip((dens[band] / ymax * (h - 1)).astype(int), 0, h - 1)
    col = (SPEC[band] * 255).astype(np.uint8)
    m = (h - 1 - np.arange(h)[:, None]) < hh[None, :]
    out[m] = col[np.nonzero(m)[1]]
    i = np.where(hh > 1)[0]
    out[(h - hh[i]).clip(0, h - 1), i] = (232, 232, 232)
    out[:, ::-1] = out[:, :].copy()
    return Image.fromarray(out)


# ---------------- GUI ----------------
CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
W, H = 600, 322


def load_cfg():
    try:
        return json.load(open(CFG, encoding="utf-8"))
    except Exception:
        return {"region": [1600, 560, 960, 540], "pos": [60, 860], "fps": 10,
                "follow": True, "cap_on": True, "cap": 240, "keys": "fcp"}


def save_cfg(c):
    json.dump(c, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def find_resolve():
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    hit = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        if u.IsWindowVisible(h):
            b = ctypes.create_unicode_buffer(512)
            u.GetWindowTextW(h, b, 512)
            if "DaVinci Resolve" in b.value:
                r = wintypes.RECT()
                u.GetWindowRect(h, ctypes.byref(r))
                if r.right - r.left > 800 and r.bottom - r.top > 500:
                    hit.append((r.left, r.top, r.right, r.bottom))
        return True

    u.EnumWindows(cb, 0)
    return hit[0] if hit else None


def main():
    import tkinter as tk
    try:
        import mss
        from PIL import ImageTk
    except ImportError as e:
        print("缺依赖：pip install numpy mss pillow  (", e, ")")
        return

    cfg = load_cfg()
    for k, v in (("fps", 10), ("follow", True), ("cap_on", True), ("cap", 240), ("autodock", True), ("keys", "fcp")):
        cfg.setdefault(k, v)
    link = Link()

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.geometry(f"{W}x{H}+{cfg['pos'][0]}+{cfg['pos'][1]}")
    cv = tk.Canvas(root, width=W, height=H, bg="#141417", highlightthickness=0, cursor="fleur")
    cv.pack()
    cv.create_rectangle(15, 56, 585, 285, outline="#2e2e34")
    img_item = cv.create_image(15, 56, anchor="nw")
    t1 = cv.create_text(15, 40, anchor="w", fill="#f0f0f0", text="主波长 —", font=("Microsoft YaHei", 11))
    t2 = cv.create_text(585, 40, anchor="e", fill="#8a8a92", text="", font=("Microsoft YaHei", 9))
    t3 = cv.create_text(300, 40, anchor="n", fill="#6d6d76", text="", font=("Microsoft YaHei", 8))
    for x, s, an in ((15, "700", "w"), (300, "550", "center"), (578, "380", "e")):
        cv.create_text(x, 294, anchor="n", fill="#8f8f97", text=s, font=("Consolas", 8))
    cv.create_text(15, 308, anchor="nw", fill="#6f6f77", text="波长 / nm", font=("Microsoft YaHei", 7))
    for x, s, tag in ((8, "选区域", "sel"), (62, "暂停", "pause"), (104, "贴靠", "dock"),
                      (152, "跟随时间线", "f1"), (232, "上限240", "f2")):
        cv.create_text(x, 4, anchor="nw", fill="#8a8a92", text=s, tags=(tag,), font=("Microsoft YaHei", 8))
    cv.create_text(590, 3, anchor="ne", fill="#c05050", text="✕", tags=("close",), font=("Segoe UI", 11))

    st = {"run": True, "photo": None, "org": [0, 0]}
    sct = mss.mss()

    def press(e):
        st["org"] = [e.x_root - root.winfo_x(), e.y_root - root.winfo_y()]

    def move(e):
        if st["org"]:
            root.geometry(f"+{e.x_root - st['org'][0]}+{e.y_root - st['org'][1]}")

    def pick(_=None):
        ov = tk.Toplevel(root)
        ov.overrideredirect(True)
        ov.attributes("-topmost", True, "-alpha", 0.28)
        ov.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
        c = tk.Canvas(ov, bg="black", highlightthickness=0, cursor="crosshair")
        c.pack(fill="both", expand=True)
        p = {}

        def down(e):
            p["x"], p["y"] = e.x_root, e.y_root
            p["r"] = c.create_rectangle(e.x, e.y, e.x, e.y, outline="#00e0ff", width=2)

        def drag(e):
            if "r" in p:
                c.coords(p["r"], p["x"], p["y"], e.x_root, e.y_root)

        def up(e):
            x0, y0 = min(p["x"], e.x_root), min(p["y"], e.y_root)
            w, h = abs(e.x_root - p["x"]), abs(e.y_root - p["y"])
            if w > 60 and h > 40:
                cfg["region"] = [x0, y0, w, h]
                save_cfg(cfg)
            ov.destroy()

        c.bind("<ButtonPress-1>", down); c.bind("<B1-Motion>", drag); c.bind("<ButtonRelease-1>", up)
        c.bind("<Escape>", lambda e: ov.destroy())

    def paint_toggles():
        cv.itemconfig("f1", fill="#d8d8d8" if cfg["follow"] else "#63636b",
                      text="跟随时间线" if cfg["follow"] else "跟随关闭")
        cv.itemconfig("f2", fill="#d8d8d8" if cfg["cap_on"] else "#63636b",
                      text=f"上限{cfg['cap']:g}" if cfg["cap_on"] else "上限关闭")

    def flip(key):
        cfg[key] = not cfg[key]
        save_cfg(cfg)
        paint_toggles()

    def toggle(_=None):
        st["run"] = not st["run"]
        cv.itemconfig("pause", text="继续" if not st["run"] else "暂停", fill="#d8d8d8")

    def dock(_=None):
        r = find_resolve()
        if r:
            root.geometry(f"+{max(r[2] - W - 26, 0)}+{max(r[3] - H - 34, 0)}")

    def quit_(_=None):
        cfg["pos"] = [root.winfo_x(), root.winfo_y()]
        save_cfg(cfg)
        root.destroy()

    cv.tag_bind("close", "<Button-1>", quit_)
    cv.tag_bind("sel", "<Button-1>", pick)
    cv.tag_bind("pause", "<Button-1>", toggle)
    cv.tag_bind("dock", "<Button-1>", dock)
    KEYS = {"fcp": {"region": "<Control-r>", "pause": "<Control-p>", "dock": "<Control-d>"},
            "davinci": {"region": "<F9>", "pause": "<F5>", "dock": "<F7>"}}
    kb = KEYS.get(cfg["keys"], KEYS["fcp"])
    cv.tag_bind("f1", "<Button-1>", lambda e: flip("follow"))
    cv.tag_bind("f2", "<Button-1>", lambda e: flip("cap_on"))
    cv.bind("<ButtonPress-1>", press)
    cv.bind("<B1-Motion>", move)
    root.bind(kb["region"], pick)
    root.bind(kb["pause"], toggle)
    root.bind(kb["dock"], dock)
    root.bind("<Escape>", quit_)

    def to_kb(k):
        return k.strip("<>").lower().replace("control", "ctrl").replace("-", "+")

    try:
        import keyboard
        keyboard.add_hotkey(to_kb(kb["region"]), lambda: root.after(0, pick))
        keyboard.add_hotkey(to_kb(kb["pause"]), lambda: root.after(0, toggle))
        keyboard.add_hotkey(to_kb(kb["dock"]), lambda: root.after(0, dock))
        cfg["_global"] = True
    except Exception:
        cfg["_global"] = False
    paint_toggles()
    if cfg.get("autodock", True):
        root.after(400, dock)

    def cur_fps():
        fr = link.fps() if cfg["follow"] else None
        base = fr if fr else float(cfg["fps"])
        fps = min(base, float(cfg["cap"]])
    return None
