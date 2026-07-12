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
    return cv2.warpAffine(img, m, (out_w, out_h), flags=cv2.INTER_LINEAR)


# ---------- 明暗 ----------

def fade(frame: np.ndarray, k: float) -> np.ndarray:
    """k=0 全黑、k=1 原樣"""
    k = min(max(k, 0.0), 1.0)
    return cv2.convertScaleAbs(frame, alpha=k)
