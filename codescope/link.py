import os
import sys
import time


class Link:
    """连接达芬奇脚本 API；连不上时降级成文件模式。"""

    def __init__(self):
        self.app = None
        self.err = ""
        self._probe = 0.0
        self._fps = None
        self._at = 0.0
        self.connect()

    def connect(self):
        self._probe = time.time()
        try:
            api = os.environ.get("RESOLVE_SCRIPT_API") or \
                r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
            mod = os.path.join(api, "Modules")
            if mod not in sys.path:
                sys.path.append(mod)
            import DaVinciResolveScript as dvr
            self.app = dvr.scriptapp("Resolve")
            self.err = "" if self.app else "Resolve 未响应"
        except Exception as e:
            self.app = None
            self.err = type(e).__name__

    def fps(self):
        now = time.time()
        if self.app is None:
            if now - self._probe > 6:
                self.connect()
            return None
        if now - self._at < 2 and self._fps is not None:
            return self._fps
        self._at = now
        try:
            s = self.app.GetProjectManager().GetCurrentProject().GetSetting("timelineFrameRate")
            self._fps = float(s) if s else None
        except Exception:
            self._fps = None
        return self._fps
