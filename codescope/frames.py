import os
import time

from PIL import Image

STILL_EXT = (".png", ".tif", ".dpx")


class Grabber:
    """从达芬奇取当前帧的原始像素，不截屏。"""

    def __init__(self, tmpdir):
        self.tmp = tmpdir
        os.makedirs(tmpdir, exist_ok=True)
        self.msg = ""

    def still(self, app):
        """导出当前时间线帧到临时文件，返回 (路径, 说明)。"""
        try:
            proj = app.GetProjectManager().GetCurrentProject()
            tl = proj.GetCurrentTimeline()
        except Exception:
            return None, "读不到当前时间线"
        if tl is None:
            return None, "没有打开的时间线"
        fn = getattr(tl, "ExportCurrentFrameAsStill", None)
        if fn is None:
            return None, "这个版本的脚本 API 没有导出帧的接口"
        for ext in STILL_EXT:
            path = os.path.join(self.tmp, "frame_%d%s" % (int(time.time() * 1000), ext))
            try:
                if not fn(path):
                    continue
            except Exception as e:
                self.msg = type(e).__name__
                continue
            if os.path.exists(path) and os.path.getsize(path) > 1024:
                return path, ""
        return None, self.msg or "导出失败（换 .tif 试试，或检查渲染设置）"

    @staticmethod
    def meta(app):
        out = {}
        try:
            proj = app.GetProjectManager().GetCurrentProject()
            tl = proj.GetCurrentTimeline()
            for k in ("timelineFrameRate", "timelineResolutionWidth", "timelineResolutionHeight",
                      "timelineColorSpace", "colorScienceMode"):
                try:
                    v = proj.GetSetting(k)
                    if v:
                        out[k] = v
                except Exception:
                    pass
            out["product"] = app.GetProductName()
            out["timeline"] = tl.GetName()
            out["frame"] = tl.GetCurrentFrame()
        except Exception:
            pass
        return out

    @staticmethod
    def load(path):
        img = Image.open(path)
        img.load()
        return img
