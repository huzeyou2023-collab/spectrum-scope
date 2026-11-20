import numpy as np


def to_codes(img, bits, step=1):
    """任意位深图像 -> 指定位深的整数码值；step 先切再算，省内存。"""
    a = np.asarray(img)
    if step > 1:
        a = a[::step, ::step]
    if a.ndim == 2:
        a = np.stack([a, a, a], -1)
    if a.shape[-1] == 4:
        a = a[:, :, :3]
    if a.dtype == np.uint16:
        f = a.astype(np.float32) / 65535.0
    elif a.dtype == np.uint8:
        f = a.astype(np.float32) / 255.0
    else:
        f = a.astype(np.float32)
        if f.max() > 1.0:
            f /= 255.0
    m = (1 << bits) - 1
    return np.rint(np.clip(f, 0, 1) * m).astype(np.int32), m


def _fold(h, w):
    if w <= 1:
        return h
    k = (h.size // w) * w
    return h[:k].reshape(-1, w).sum(1)


def histogram(codes, bits, binw=1, step=1):
    """R/G/B/Y 四条直方图 + 参与统计的像素数。"""
    c = codes
    mx = 1 << bits
    n = c.shape[0] * c.shape[1]
    res = {"n": n, "step": step, "binw": binw}
    for i, ch in enumerate("RGB"):
        h = np.bincount(c[:, :, i].ravel(), minlength=mx).astype(np.float64)
        res[ch] = _fold(h, binw)
    y = 0.2126 * c[:, :, 0] + 0.7152 * c[:, :, 1] + 0.0722 * c[:, :, 2]
    hy = np.bincount(np.rint(y).ravel().astype(np.int64).clip(0, mx - 1), minlength=mx)
    res["Y"] = _fold(hy.astype(np.float64), binw)
    return res


def peak(h, bits, binw):
    if not len(h) or h.max() <= 0:
        return 0, 0.0
    i = int(np.argmax(h))
    return int(i * binw + binw / 2), float(h[i])


def auto_step(w, h):
    """按素材像素量给采样步长。"""
    mp = w * h / 1e6
    if mp <= 2.3:
        return 1
    if mp <= 9.5:
        return 2
    if mp <= 21:
        return 3
    return 4


def src_bits(img):
    mode = getattr(img, "mode", "")
    if "16" in mode or "32" in mode:
        return 16
    return 8


def binw_for(bits, sb):
    """每格宽度：让一格正好覆盖源素材的一个码值，图表才连续。"""
    if bits <= sb:
        return 1
    return 1 << (bits - sb)
