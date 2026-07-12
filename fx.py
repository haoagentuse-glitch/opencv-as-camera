# fx.py — 賽璐璐攝影台：攝影機、疊加、遮罩、光學效果
# 全部是無狀態純函式；frame 一律 BGR uint8
import math

import cv2
import numpy as np


# ---------- 緩動與插值 ----------

def ease(t: float) -> float:
    """smoothstep 緩入緩出，t 取 0~1"""
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ---------- 素材載入 ----------

def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(path)
    return img


def load_video(path: str) -> list[np.ndarray]:
    """整支影片讀進記憶體，回傳 frame 清單"""
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    if not frames:
        raise FileNotFoundError(path)
    return frames


def pingpong(frames: list[np.ndarray], i: int) -> np.ndarray:
    """來回循環取格：0,1,...,n-1,n-2,...,1,0,1,... 避免 loop 接縫跳動"""
    n = len(frames)
    if n == 1:
        return frames[0]
    cycle = 2 * n - 2
    j = i % cycle
    return frames[j] if j < n else frames[cycle - j]


# ---------- 攝影機（本片一切運鏡的根） ----------

def camera(img: np.ndarray, cx: float, cy: float, zoom: float,
           out_w: int, out_h: int) -> np.ndarray:
    """以原圖座標 (cx, cy) 為中心、zoom 倍率取景，輸出 out_w x out_h。

    zoom=1.0 時取「能塞進原圖的最大 4:3（out 比例）窗」；越大越近。
    用 warpAffine 做次像素取樣——慢速推軌每格位移 << 1px，整數裁切會抖。
    取景窗自動夾在圖內，不會取到圖外黑邊。
    """
    h, w = img.shape[:2]
    aspect = out_w / out_h
    if w / h > aspect:
        base_w, base_h = h * aspect, float(h)
    else:
        base_w, base_h = float(w), w / aspect
    cw, ch = base_w / zoom, base_h / zoom
    cx = min(max(cx, cw / 2), w - cw / 2)
    cy = min(max(cy, ch / 2), h - ch / 2)
    s = out_w / cw
    m = np.array([[s, 0, out_w / 2 - s * cx],
                  [0, s, out_h / 2 - s * cy]], dtype=np.float64)
    interp = cv2.INTER_CUBIC if s > 1.0 else cv2.INTER_LINEAR
    return cv2.warpAffine(img, m, (out_w, out_h), flags=interp)


def cam_frac(img: np.ndarray, fx_: float, fy_: float, zoom: float,
             out_w: int, out_h: int) -> np.ndarray:
    """camera 的比例座標版：中心用 0~1 的圖內比例指定，素材解析度無關"""
    h, w = img.shape[:2]
    return camera(img, w * fx_, h * fy_, zoom, out_w, out_h)


# ---------- 明暗 ----------

def fade(frame: np.ndarray, k: float) -> np.ndarray:
    """k=0 全黑、k=1 原樣"""
    k = min(max(k, 0.0), 1.0)
    return cv2.convertScaleAbs(frame, alpha=k)


# ---------- 遮罩 ----------

def door_mask(w: int, h: int, t: float, soft: int = 31) -> np.ndarray:
    """門縫 wipe：中央直縫由細變寬，t=0 全黑、t=1 全開。回傳 float32 單通道 0~1"""
    mask = np.zeros((h, w), np.float32)
    half = max(1, int(w / 2 * ease(t)))
    cx = w // 2
    mask[:, max(0, cx - half):min(w, cx + half)] = 1.0
    if soft > 1:
        mask = cv2.GaussianBlur(mask, (soft | 1, soft | 1), 0)
    return mask


def radial_mask(w: int, h: int, t: float, cx_: float = 0.5, cy_: float = 0.5) -> np.ndarray:
    """圓形 reveal：從 (cx_,cy_) 比例位置向外展開，t=0 全黑、t=1 全亮"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - w * cx_) ** 2 + (yy - h * cy_) ** 2)
    r = ease(t) * math.hypot(w, h) * 0.75
    edge = max(w, h) * 0.15
    return np.clip((r - d) / edge + 1.0, 0.0, 1.0)


def apply_mask(frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """mask 外壓黑（mask 為 float32 0~1 單通道）"""
    return (frame.astype(np.float32) * mask[:, :, None]).astype(np.uint8)


# ---------- 光學效果 ----------

def rgb_split(frame: np.ndarray, px: int) -> np.ndarray:
    """色版錯位：R 左移、B 右移 px 像素"""
    if px <= 0:
        return frame
    out = frame.copy()
    out[:, :-px, 2] = frame[:, px:, 2]
    out[:, px:, 0] = frame[:, :-px, 0]
    return out


def shake(frame: np.ndarray, amp: float, seed: int) -> np.ndarray:
    """手持震動：整格平移，邊緣鏡射補"""
    if amp <= 0:
        return frame
    rng = np.random.RandomState(seed)
    dx, dy = rng.uniform(-amp, amp, 2)
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(frame, m, (frame.shape[1], frame.shape[0]),
                          borderMode=cv2.BORDER_REFLECT)


def blur(frame: np.ndarray, k: int) -> np.ndarray:
    if k <= 1:
        return frame
    return cv2.GaussianBlur(frame, (k | 1, k | 1), 0)


_SCAN_CACHE: dict[tuple[int, int], np.ndarray] = {}


def scanlines(frame: np.ndarray, strength: float = 0.25, period: int = 3) -> np.ndarray:
    """CRT 掃描線：每 period 行壓暗一行"""
    h = frame.shape[0]
    key = (h, period)
    if key not in _SCAN_CACHE:
        rows = np.zeros((h, 1, 1), np.float32)
        rows[::period] = 1.0
        _SCAN_CACHE[key] = rows
    factor = 1.0 - _SCAN_CACHE[key] * strength
    return np.clip(frame.astype(np.float32) * factor, 0, 255).astype(np.uint8)


_VIG_CACHE: dict[tuple[int, int, float], np.ndarray] = {}


def vignette(frame: np.ndarray, strength: float = 0.35) -> np.ndarray:
    """四角壓暗，統一「攝影台鏡頭」質感"""
    h, w = frame.shape[:2]
    key = (h, w, strength)
    if key not in _VIG_CACHE:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        _VIG_CACHE[key] = (1.0 - strength * np.clip(d - 0.55, 0, 1) ** 2)[:, :, None]
    return np.clip(frame.astype(np.float32) * _VIG_CACHE[key], 0, 255).astype(np.uint8)


def grain(frame: np.ndarray, sigma: float, seed: int) -> np.ndarray:
    """底片顆粒"""
    if sigma <= 0:
        return frame
    rng = np.random.RandomState(seed)
    noise = rng.normal(0, sigma, frame.shape[:2]).astype(np.float32)
    return np.clip(frame.astype(np.float32) + noise[:, :, None], 0, 255).astype(np.uint8)


def typewriter(frame: np.ndarray, text: str, t: float, org: tuple[int, int],
               scale: float = 1.2, color=(120, 255, 160), thickness: int = 2) -> np.ndarray:
    """打字機字幕：t=0~1 逐字浮現，游標閃爍"""
    n = int(len(text) * min(max(t, 0.0), 1.0) + 1e-6)
    shown = text[:n]
    out = frame.copy()
    font = cv2.FONT_HERSHEY_DUPLEX
    # 微光暈：先畫粗的暗色再畫亮字
    cv2.putText(out, shown, org, font, scale, tuple(c // 3 for c in color),
                thickness + 4, cv2.LINE_AA)
    cv2.putText(out, shown, org, font, scale, color, thickness, cv2.LINE_AA)
    return out
