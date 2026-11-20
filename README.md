# spectrum-scope

达芬奇主波长示波器。抓监看画面的像素，按 CIE 1931 谱线轨迹把每个像素折算成主波长，按 1 nm 分箱统计，画成“波长 — 像素占比”曲线。左 700 nm，右 380 nm。

## 为什么是浮窗，不是原生示波器

达芬奇只有五种示波器（Waveform / Parade / Vectorscope / Histogram / CIE Chromaticity），没有波长轴那一种，也没有第三方插入 Scopes 面板的接口：

- Scopes 面板是写死的内部 Qt 控件，没留插件槽位。
- OFX 只能挂进节点树做图像处理，输出的是像素，不是 UI。
- Python / Lua 脚本 API 只有 Project / MediaPool / Timeline / Render，没有 UI 接口。
- Studio 18.5+ 的 Workflow Integration 能嵌面板，但面板同样拿不到监看像素，要帧得走渲染队列，一帧几百毫秒，做不到实时。

“能嵌进界面”和“能实时拿到像素”在达芬奇里是互斥的。所以这里选后者：抓屏 + 实时计算 + 无边框浮窗，手动贴到示波器栏下面。

## 原理

1. sRGB → 线性 → XYZ（D65）→ 色度坐标 (x, y)
2. 从 D65 白点 (0.3127, 0.3290) 向该点引射线，交 CIE 1931 光谱轨迹，交点波长就是主波长
3. 低纯度（近白/近灰/近黑）判为无彩，落在紫色线上的判为品红（无对应波长）
4. 主波长 1 nm 分箱，高斯核 σ=1.2 nm 平滑，归一化成 %/nm

注意 sRGB 三原色不是三条谱线（R≈611、G≈549、B≈464 nm，且通道大面积重叠），同色异谱信息在 RGB 里已经丢了。算出来的“主波长”是色相角度的等价物，不是真实发光光谱。

## 安装

Python 3.9+，Windows。

```
pip install -r requirements.txt
pip install keyboard      # 可选，装了才有全局热键
```

双击 `启动.bat`，或 `python scope.py`。

## 键位（FCP 映射）

| 动作 | 键 |
|---|---|
| 框选监看区域 | Ctrl+R |
| 暂停 / 继续 | Ctrl+P |
| 贴靠到达芬奇右下角 | Ctrl+D |
| 关闭 | Esc |

装了 keyboard 就是全局的，在达芬奇窗口里直接按；没装只能在浮窗上按。键位表在 `scope.py` 的 `KEYS`，`config.json` 里 `keys` 改成 `davinci` 即切成 F9 / F5 / F7。

## 帧率

默认跟随当前时间线帧率（`timelineFrameRate`），上限 240（`cap`，`cap_on` 设 false 即不设上限）。读不到时间线就退回 `fps`。帧率高时自动加大采样步长。

## 配置 config.json

| 键 | 含义 |
|---|---|
| region | 抓屏区域 [x, y, w, h] |
| pos | 窗口位置 |
| fps | 读不到时间线时的备用帧率 |
| follow | 是否跟随时间线 |
| cap_on / cap | 帧率上限开关与值 |
| keys | 键位预设 fcp / davinci |

## 已知限制

1. 抓的是屏幕像素。监看开了硬件覆盖会抓成全黑，关掉覆盖或换区域。
2. 框选区被其他窗口遮住的部分也会被算进去。
3. 算的是显示出来的颜色（已过输出变换），不是 LOG 原始数据。
4. 只在 Windows 上验证过；贴靠用的 Win32 API，其它平台会直接跳过。

## License

MIT
