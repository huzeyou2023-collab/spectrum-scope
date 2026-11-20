import json
import os
import sys
import time

import numpy as np
import tkinter as tk
from PIL import Image, ImageTk

from codes import auto_step, binw_for, histogram, peak, src_bits, to_codes
from frames import Grabber
from link import Link
from render import chart
from wave import analyse, wave_chart

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "config.json")
W, H = 800, 430
SPACES = {"bt2100-pq": (10, "BT.2100 PQ"), "bt2100-hlg": (10, "BT.2100 HLG"),
          "rec709": (8, "Rec.709 SDR"), "bt2020-12": (12, "BT.2020 12 bit")}


def load_cfg():
    try:
        c = json.load(open(CFG, encoding="utf-8"))
    except Exception:
        c = {}
    for k, v in (("bits", 10), ("binw", 0), ("step", 0), ("log", False),
                 ("space", "bt2100-pq"), ("axis", "code"), ("file", ""), ("auto", False)):
        c.setdefault(k, v)
    return c


def save_cfg(c):
    json.dump({k: v for k, v in c.items() if not k.startswith("_")},
              open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    cfg = load_cfg()
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    if argv:
        cfg["file"] = argv[0]

    link = Link()
    grab = Grabber(os.path.join(HERE, "_tmp"))

    root = tk.Tk()
    root.title("码值 / 波长分析 — CodeScope")
    root.configure(bg="#141417")
    root.attributes("-topmost", True)
    root.geometry(f"{W}x{H}+{cfg.get('x', 80)}+{cfg.get('y', 200)}")

    cv = tk.Canvas(root, width=W, height=H, bg="#141417", highlightthickness=0)
    cv.pack(fill="both", expand=True)

    info = cv.create_text(10, 26, anchor="nw", fill="#8f8f97", text="", font=("Microsoft YaHei", 9))
    hero = cv.create_text(10, 8, anchor="nw", fill="#f2f2f2", text="等待取帧", font=("Microsoft YaHei", 12))
    img_item = cv.create_image(10, 54, anchor="nw")
    foot = cv.create_text(10, 392, anchor="nw", fill="#7d7d88", text="", font=("Consolas", 9))

    def bar(x, key, text):
        return cv.create_text(x, 61, anchor="nw", text=text, tags=(key,), fill="#9a9aa4",
                              font=("Microsoft YaHei", 9))

    b_space = bar(10, "space", "")
    b_bits = bar(152, "bits", "")
    b_axis = bar(214, "axis", "")
    b_bin = bar(300, "bin", "")
    b_step = bar(378, "step", "")
    b_log = bar(478, "log", "")
    b_go = bar(530, "go", "● 取一帧")
    b_auto = bar(612, "auto", "")
    b_save = bar(692, "save", "存 PNG")
    b_csv = bar(760, "csv", "CSV")

    st = {"photo": None, "res": None, "img": None, "t": 0.0, "mp": (0, 0), "wave": 0}

    def paint():
        s = SPACES.get(cfg["space"], (10, cfg["space"]))
        cv.itemconfig(b_space, text=f"色彩空间 {s[1]} ▾")
        cv.itemconfig(b_bits, text=f"{cfg['bits']} bit ▾")
        cv.itemconfig(b_axis, text="波长+码值" if cfg["axis"] == "dual" else "码值轴")
        cv.itemconfig(b_bin, text=("每格 %s ▾" % (cfg["binw"] or "自动")))
        cv.itemconfig(b_step, text=f"步长 {'自动' if cfg['step'] == 0 else cfg['step']} ▾")
        cv.itemconfig(b_log, text="对数" if cfg["log"] else "线性",
                      fill="#e0e0e6" if cfg["log"] else "#7a7a84")
        cv.itemconfig(b_auto, text="● 自动" if cfg["auto"] else "○ 自动",
                      fill="#e0e0e6" if cfg["auto"] else "#7a7a84")

    def cycle(key, values):
        cur = cfg[key]
        cfg[key] = values[(values.index(cur) + 1) % len(values)] if cur in values else values[0]
        save_cfg(cfg)
        paint()
        shot()

    def space_next(_=None):
        keys = list(SPACES)
        cfg["space"] = keys[(keys.index(cfg["space"]) + 1) % len(keys)]
        cfg["bits"] = SPACES[cfg["space"]][0]
        save_cfg(cfg)
        paint()
        shot()

    def shot(_=None):
        t0 = time.time()
        src = ""
        if cfg["file"]:
            try:
                img = grab.load(cfg["file"])
                src = os.path.basename(cfg["file"])
            except Exception as e:
                cv.itemconfig(hero, text=f"读文件失败：{type(e).__name__}")
                return
        else:
            if link.app is None:
                link.connect()
            if link.app is None:
                cv.itemconfig(hero, text="没连上达芬奇：拖一个帧文件进来，或开偏好设置里的外部脚本")
                return
            path, msg = grab.still(link.app)
            if not path:
                cv.itemconfig(hero, text=f"取帧失败：{msg}")
                return
            img = grab.load(path)
            m = grab.meta(link.app)
            src = "时间线 %s 帧 %s" % (m.get("timeline", "?"), m.get("frame", "?"))

        w, h = img.size
        st["mp"] = (w, h)
        st["img"] = img
        step = cfg["step"] or auto_step(w, h)
        sb = src_bits(img)
        binw = cfg["binw"] or binw_for(cfg["bits"], sb)
        st["binw"] = binw
        codes, mx = to_codes(img, cfg["bits"], step)
        res = histogram(codes, cfg["bits"], binw, step)
        st["res"] = res
        if cfg["axis"] == "dual":
            rgb = np.asarray(img.convert("RGB"))[::step, ::step]
            wv = analyse(rgb, step=1)
            pic = Image.new("RGB", (W - 20, 300), (18, 18, 21))
            pic.paste(wave_chart(wv["dens"], W - 20, 140), (0, 0))
            pic.paste(chart(res, cfg["bits"], binw, W - 20, 152, log=cfg["log"], pct=99.5), (0, 148))
            st["wave"] = wv["peak"]
        else:
            pic = chart(res, cfg["bits"], binw, W - 20, 300, log=cfg["log"],
                        pct=None if cfg["log"] else 99.5)
            st["wave"] = 0
        st["photo"] = ImageTk.PhotoImage(pic)
        cv.itemconfig(img_item, image=st["photo"])

        r, g, b = (peak(res[k], cfg["bits"], binw) for k in "RGB")
        st["t"] = (time.time() - t0) * 1000
        area = res["n"]
        cv.itemconfig(hero, text=f"{src} · {w}×{h}")
        cv.itemconfig(info, text=f"采样 {area/1e6:.2f} M px / 共 {w*h/1e6:.1f} M（步长 {step}）"
                                 f" · 每格 {binw} 码值 · 源 {sb} bit · 耗时 {st['t']:.0f} ms")
        wtxt = f"主波长 {st['wave']:.0f} nm     " if st.get("wave") else ""
        cv.itemconfig(foot, text=f"{wtxt}峰  R {r[0]} / G {g[0]} / B {b[0]}     "
                                 f"满格 {b[1]:.0f} px     {cfg['bits']} bit  0–{mx}")

    def save(_=None):
        if st["res"] is None:
            return
        p = os.path.join(HERE, "codescope_%s.png" % time.strftime("%H%M%S"))
        chart(st["res"], cfg["bits"], st["binw"], 1520, 600, log=cfg["log"],
              pct=None if cfg["log"] else 99.5).save(p)
        cv.itemconfig(foot, text=f"已存 {os.path.basename(p)}")

    def csv(_=None):
        if st["res"] is None:
            return
        res = st["res"]
        p = os.path.join(HERE, "codescope_%s.csv" % time.strftime("%H%M%S"))
        n = res["n"] or 1
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("code,R,G,B,Y,R%,G%,B%,Y%\n")
            for i in range(len(res["R"])):
                fh.write("%d,%d,%d,%d,%d,%.4f,%.4f,%.4f,%.4f\n" % (
                    i * st["binw"], res["R"][i], res["G"][i], res["B"][i], res["Y"][i],
                    res["R"][i] / n * 100, res["G"][i] / n * 100,
                    res["B"][i] / n * 100, res["Y"][i] / n * 100))
        cv.itemconfig(foot, text=f"已存 {os.path.basename(p)}")

    def auto_tick():
        if cfg["auto"]:
            shot()
        root.after(1200 if not cfg["auto"] else 600, auto_tick)

    def toggle(key):
        cfg[key] = not cfg[key]
        save_cfg(cfg)
        paint()

    cv.tag_bind("space", "<Button-1>", space_next)
    cv.tag_bind("bits", "<Button-1>", lambda e: cycle("bits", [8, 10, 12]))
    cv.tag_bind("axis", "<Button-1>", lambda e: cycle("axis", ["code", "dual"]))
    cv.tag_bind("bin", "<Button-1>", lambda e: cycle("binw", [0, 1, 2, 4, 8, 16]))
    cv.tag_bind("step", "<Button-1>", lambda e: cycle("step", [0, 1, 2, 3, 4]))
    cv.tag_bind("log", "<Button-1>", lambda e: (toggle("log"), shot()))
    cv.tag_bind("auto", "<Button-1>", lambda e: toggle("auto"))
    cv.tag_bind("go", "<Button-1>", shot)
    cv.tag_bind("save", "<Button-1>", save)
    cv.tag_bind("csv", "<Button-1>", csv)

    root.bind("<Control-r>", shot)
    root.bind("<Control-p>", lambda e: toggle("auto"))
    root.bind("<Escape>", lambda e: root.destroy())
    try:
        import keyboard
        keyboard.add_hotkey("ctrl+r", lambda: root.after(0, shot))
    except Exception:
        pass

    paint()
    root.after(300, shot)
    auto_tick()
    root.mainloop()


if __name__ == "__main__":
    main()
