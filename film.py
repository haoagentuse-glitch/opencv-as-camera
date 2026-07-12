# film.py — 《最後一封訊息》時間軸與渲染主迴圈
#
# 用法：
#   python film.py               # 渲染全片 output/final.mp4
#   python film.py preview       # 每個 shot 中間點抽 1 frame 存 output/preview/ 供檢查構圖
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
GIRL = fx.load_image(asset("1.png"))        # 少女正面全身
BACK = fx.load_image(asset("2.png"))        # 少女背影
CITY = fx.load_image(asset("3.png"))        # 城市俯瞰（電線塔）
TOWER_IN = fx.load_image(asset("4.png"))    # 塔內終端機房
CRT = fx.load_image(asset("5.jpg"))         # CRT 終端畫面
GIRL_V = fx.load_video(asset("1.mp4"))      # 少女微動（頭髮/衣角）
BACK_V = fx.load_video(asset("2.mp4"))      # 背影微動
CITY_V = fx.load_video(asset("3.mp4"))      # 城市（雲飄）

BLACK = np.zeros((OUT_H, OUT_W, 3), np.uint8)


def cam(img, fx_, fy_, zoom):
    return fx.cam_frac(img, fx_, fy_, zoom, OUT_W, OUT_H)


# =====================================================================
# Shots — 簽名 (u, fi) -> frame；u=shot 內 0~1 進度，fi=shot 內 frame 序號
# =====================================================================

# ---- 0~10s 開場：黑 → 城市，極慢推近（雲用 3.mp4 自帶動態） ----

def sh_opening(u, fi):
    src = fx.pingpong(CITY_V, fi)
    zoom = fx.lerp(1.0, 1.15, fx.ease(u))
    frame = cam(src, 0.5, 0.45, zoom)
    return fx.fade(frame, min(u / 0.35, 1.0))


# ---- 10~18s 少女屋頂停格：只有頭髮衣角在動，鏡頭慢推 ----

def sh_girl_roof(u, fi):
    src = fx.pingpong(GIRL_V, fi)
    zoom = fx.lerp(1.02, 1.28, fx.ease(u))
    return cam(src, 0.5, fx.lerp(0.45, 0.38, u), zoom)


# ---- 18~28s 純剪接四連 Cut：腳 → 手 → 背影 → 天空 ----

def sh_cut_feet(u, fi):
    return cam(GIRL, 0.5, fx.lerp(0.93, 0.90, u), 3.6)


def sh_cut_hand(u, fi):
    return cam(GIRL, 0.56, 0.52, fx.lerp(4.2, 4.6, fx.ease(u)))


def sh_cut_back(u, fi):
    src = fx.pingpong(BACK_V, fi)
    return cam(src, 0.5, 0.40, fx.lerp(1.25, 1.35, u))


def sh_cut_sky(u, fi):
    src = fx.pingpong(CITY_V, fi)          # 上緣天空＋煙雲，雲自己會動
    return cam(src, 0.45, fx.lerp(0.18, 0.14, u), 2.2)


# ---- 28~38s 塔外推近 → 門縫打開見塔內 ----

def sh_tower_push(u, fi):
    """電線塔＝通訊塔，鏡頭從全景推向塔身"""
    e = fx.ease(u)
    return cam(CITY, fx.lerp(0.40, 0.20, e), fx.lerp(0.42, 0.33, e),
               fx.lerp(1.3, 2.6, e))


def sh_door_open(u, fi):
    """黑 → 中央門縫由細變寬，露出塔內"""
    inside = cam(TOWER_IN, 0.5, 0.5, fx.lerp(1.0, 1.12, u))
    mask = fx.door_mask(OUT_W, OUT_H, u * 0.9, soft=61)
    return fx.apply_mask(inside, mask)


# ---- 38~48s 終端四連 Cut → 螢幕 Mask Reveal ----

def sh_cut_terminal(u, fi):
    return cam(TOWER_IN, 0.45, 0.85, fx.lerp(2.2, 2.4, u))


def sh_cut_hand2(u, fi):
    """伸手——同一張手的賽璐璐換個更近的取景重拍，壓暗當室內"""
    frame = cam(GIRL, 0.56, 0.52, fx.lerp(5.0, 5.6, fx.ease(u)))
    return fx.fade(frame, 0.7)


def sh_cut_button(u, fi):
    frame = cam(TOWER_IN, 0.17, 0.88, fx.lerp(3.8, 4.2, u))
    return fx.fade(frame, 0.85)


def sh_screen_reveal(u, fi):
    """CRT 畫面從中心慢慢亮起"""
    frame = cam(CRT, 0.5, 0.5, 1.0)
    frame = fx.scanlines(frame, 0.3)
    mask = fx.radial_mask(OUT_W, OUT_H, fx.ease(u))
    lit = fx.apply_mask(frame, 0.15 + 0.85 * mask)
    return lit


# ---- 48~55s 快速 Montage：每張約 0.2s，特效強度隨進度加壓 ----

_MONTAGE = [
    lambda: cam(CITY, 0.5, 0.45, 1.0),
    lambda: cam(GIRL, 0.487, 0.115, 8.0),   # 眼睛特寫
    lambda: cam(CRT, 0.5, 0.5, 1.1),
    lambda: cam(BACK, 0.55, 0.18, 2.0),     # 天空
    lambda: cam(CITY, 0.25, 0.35, 2.2),     # 電線塔
    lambda: cam(TOWER_IN, 0.45, 0.85, 2.3),
    lambda: cam(GIRL, 0.56, 0.52, 4.5),     # 手
    lambda: cam(GIRL, 0.487, 0.115, 9.5),   # 眼睛更近
]


def sh_montage(u, fi):
    idx = fi // 5                            # 5 frames ≈ 0.21s 一張
    frame = _MONTAGE[idx % len(_MONTAGE)]()
    k = 0.3 + 0.7 * u                        # 強度爬升
    frame = fx.rgb_split(frame, int(2 + 8 * k))
    frame = fx.blur(frame, 3 if u < 0.5 else 5)
    frame = fx.shake(frame, 3 + 12 * k, seed=fi * 7 + 1)
    return frame


# ---- 55~60s CRT 一句話 → 推近 → 黑 ----

_MSG = "IS ANYONE STILL THERE?"


def sh_last_signal(u, fi):
    base = fx.fade(cam(CRT, 0.5, 0.52, fx.lerp(1.15, 1.45, fx.ease(u))), 0.35)
    # 打字機：前 55% 逐字，之後全句停格
    tw = min(u / 0.55, 1.0)
    (tw_w, _), _ = cv2.getTextSize(_MSG, cv2.FONT_HERSHEY_DUPLEX, 1.3, 2)
    frame = fx.typewriter(base, _MSG, tw, ((OUT_W - tw_w) // 2, OUT_H // 2),
                          scale=1.3)
    frame = fx.scanlines(frame, 0.35)
    if u > 0.82:                             # 最後 fade to black
        frame = fx.fade(frame, 1.0 - (u - 0.82) / 0.18)
    return frame


# =====================================================================
# 時間軸（秒）
# =====================================================================

SHOTS = [
    (0.0, 10.0, sh_opening),
    (10.0, 18.0, sh_girl_roof),
    (18.0, 20.5, sh_cut_feet),
    (20.5, 23.0, sh_cut_hand),
    (23.0, 25.5, sh_cut_back),
    (25.5, 28.0, sh_cut_sky),
    (28.0, 33.0, sh_tower_push),
    (33.0, 38.0, sh_door_open),
    (38.0, 40.5, sh_cut_terminal),
    (40.5, 42.5, sh_cut_hand2),
    (42.5, 44.5, sh_cut_button),
    (44.5, 48.0, sh_screen_reveal),
    (48.0, 55.0, sh_montage),
    (55.0, 60.0, sh_last_signal),
]


def post(frame, f):
    """全片統一的攝影台質感：vignette + 底片顆粒"""
    frame = fx.vignette(frame, 0.30)
    return fx.grain(frame, 3.0, seed=f)


def render_frame(f: int) -> np.ndarray:
    t = f / FPS
    for t0, t1, fn in SHOTS:
        if t0 <= t < t1:
            u = (t - t0) / (t1 - t0)
            fi = f - round(t0 * FPS)
            return post(fn(u, fi), f)
    return BLACK


def render(out_path: str) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    total = round(SHOTS[-1][1] * FPS)
    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"),
                             FPS, (OUT_W, OUT_H))
    if not writer.isOpened():
        sys.exit(f"VideoWriter 開不了輸出檔：{out_path}")
    for f in range(total):
        writer.write(render_frame(f))
        if f % 240 == 0:
            print(f"  frame {f}/{total}")
    writer.release()
    print(f"完成：{out_path}（{total} frames / {total / FPS:.1f}s）")


def preview() -> None:
    """每個 shot 的 25% / 75% 兩點各抽一格，存 output/preview/ 檢查構圖"""
    pdir = os.path.join(OUT_DIR, "preview")
    os.makedirs(pdir, exist_ok=True)
    for i, (t0, t1, fn) in enumerate(SHOTS):
        for tag, p in [("a", 0.25), ("b", 0.75)]:
            f = round((t0 + (t1 - t0) * p) * FPS)
            cv2.imwrite(os.path.join(pdir, f"s{i:02d}{tag}_{fn.__name__}.jpg"),
                        render_frame(f))
    print(f"preview 存於 {pdir}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        preview()
    else:
        render(os.path.join(OUT_DIR, "final.mp4"))
