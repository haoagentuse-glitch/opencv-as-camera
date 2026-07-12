# film.py — 《最後一封訊息》時間軸與渲染主迴圈
import os
import sys

import cv2
import numpy as np

import fx

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "output")
OUT_W, OUT_H, FPS = 960, 720, 24


def asset(name: str) -> str:
    return os.path.join(ROOT, name)


print("載入素材…")
CITY_V = fx.load_video(asset("3.mp4"))      # 城市俯瞰，雲自帶動態
GIRL_V = fx.load_video(asset("1.mp4"))      # 少女正面，頭髮衣角微動
V_H, V_W = CITY_V[0].shape[:2]              # 624x624


# ---------- Shots ----------
# 每個 shot fn 簽名：(u, fi) -> frame
#   u  = 該 shot 內 0~1 進度
#   fi = 該 shot 內 local frame index（餵給 pingpong）

def shot_opening_city(u: float, fi: int) -> np.ndarray:
    """0~5s：黑 fade in，城市極慢推近"""
    src = fx.pingpong(CITY_V, fi)
    zoom = fx.lerp(1.0, 1.12, fx.ease(u))
    frame = fx.camera(src, V_W / 2, V_H * 0.45, zoom, OUT_W, OUT_H)
    return fx.fade(frame, min(u / 0.5, 1.0))  # 前半段 fade in


def shot_girl_roof(u: float, fi: int) -> np.ndarray:
    """5~10s：少女屋頂停格，鏡頭慢推"""
    src = fx.pingpong(GIRL_V, fi)
    zoom = fx.lerp(1.0, 1.18, fx.ease(u))
    return fx.camera(src, V_W / 2, V_H * 0.42, zoom, OUT_W, OUT_H)


SHOTS = [
    (0.0, 5.0, shot_opening_city),
    (5.0, 10.0, shot_girl_roof),
]


# ---------- 渲染 ----------

def render(shots, out_path: str) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    total_frames = round(shots[-1][1] * FPS)
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"),
                             FPS, (OUT_W, OUT_H))
    if not writer.isOpened():
        sys.exit(f"VideoWriter 開不了輸出檔：{out_path}")
    for f in range(total_frames):
        t = f / FPS
        for t0, t1, fn in shots:
            if t0 <= t < t1:
                u = (t - t0) / (t1 - t0)
                fi = f - round(t0 * FPS)
                frame = fn(u, fi)
                break
        else:
            frame = np.zeros((OUT_H, OUT_W, 3), np.uint8)
        writer.write(frame)
        if f % 120 == 0:
            print(f"  frame {f}/{total_frames}")
    writer.release()
    print(f"完成：{out_path}（{total_frames} frames / {total_frames / FPS:.1f}s）")


if __name__ == "__main__":
    render(SHOTS, os.path.join(OUT_DIR, "skeleton.mp4"))
