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
    return os.path.join(ROOT, "assets", name)


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
    # 雲改單向播放（pingpong 會在 5.2s 反向，讀起來像鏡頭回拉）
    idx = min(int(fi * (len(CITY_V) - 1) / (10 * FPS - 1)), len(CITY_V) - 1)
    src = CITY_V[idx]
    zoom = fx.lerp(1.0, 1.15, u)          # 等速前推，末段不減速、絕不回拉
    frame = cam(src, 0.5, 0.45, zoom)
    return fx.fade(frame, min(u / 0.35, 1.0))


# ---- 10~18s 少女屋頂停格：只有頭髮衣角在動，鏡頭慢推 ----

_GIRL_CLEAN = 48   # 1.mp4 乾淨前段上限；~frame50 之後裙擺融化破圖，避開


def sh_girl_roof(u, fi):
    # 靜態推進(0~1.5s) → 影片乾淨前段微動(1.5~4.5s) → 凍結最後乾淨格續推(4.5~8s)
    if fi < 1.5 * FPS:
        vi = 0
    elif fi < 4.5 * FPS:
        vi = int((fi - 1.5 * FPS) / (3 * FPS) * _GIRL_CLEAN)
    else:
        vi = _GIRL_CLEAN
    src = GIRL_V[min(vi, _GIRL_CLEAN)]
    # u^0.7：前段推快，約 13s(u=0.375) 把裙子（含破圖）推出畫面下緣，之後續推到胸像特寫
    p = u ** 0.7
    zoom = fx.lerp(1.10, 2.30, p)
    cy = fx.lerp(0.40, 0.18, p)
    return cam(src, 0.5, cy, zoom)


# ---- 18~25s 手 blur 進場，鏡頭逐漸拉遠到整個背影 ----

def sh_hand_to_back(u, fi):
    src = fx.pingpong(BACK_V, fi)                 # 背影，帶頭髮衣角微動
    e = fx.ease(u)
    zoom = fx.lerp(3.6, 1.28, e)                  # 手部特寫 → 全背影
    cx = fx.lerp(0.42, 0.50, e)                   # 手在身側 → 拉回人物中央
    cy = fx.lerp(0.56, 0.42, e)
    frame = cam(src, cx, cy, zoom)
    b = int(round(fx.lerp(27, 0, min(u / 0.45, 1.0))))  # 前 45% 由糊轉清，blur 進場
    return fx.blur(frame, b)


# ---- 25~28s 天空一拍 ----

def sh_cut_sky(u, fi):
    src = fx.pingpong(CITY_V, fi)          # 上緣天空＋煙雲，雲自己會動
    return cam(src, 0.45, fx.lerp(0.18, 0.14, u), 2.2)


# ---- 28~38s 塔外推近 → 門縫打開見塔內 ----

def sh_tower_push(u, fi):
    """電線塔＝通訊塔，鏡頭從全景推向塔身，末段逐漸沒入黑（睜眼前的閉眼）"""
    e = fx.ease(u)
    frame = cam(CITY, fx.lerp(0.40, 0.20, e), fx.lerp(0.42, 0.33, e),
                fx.lerp(1.3, 2.6, e))
    if u > 0.55:
        frame = fx.fade(frame, 1.0 - fx.ease((u - 0.55) / 0.45))
    return frame


def sh_eye_open(u, fi):
    """睜眼感：黑 → 眼瞼上下張開，慢起快開；邊張眼邊平移掃視塔內，手持晃動"""
    pan = fx.ease(u)
    cx = fx.lerp(0.30, 0.68, pan)                 # 橫向掃視
    cy = fx.lerp(0.44, 0.52, pan)
    zoom = fx.lerp(1.28, 1.05, u)
    inside = cam(TOWER_IN, cx, cy, zoom)               # 只保留平移掃視，去掉晃動
    mask = fx.eyelid_mask(OUT_W, OUT_H, u ** 1.9, soft=55)  # 慢起快開的睜眼曲線
    return fx.apply_mask(inside, mask)


# ---- 38~48s 終端四連 Cut → 螢幕 Mask Reveal ----

def sh_cut_terminal(u, fi):
    return cam(TOWER_IN, 0.45, 0.85, fx.lerp(2.2, 2.4, u))


def sh_cut_hand2(u, fi):
    """伸手——同一張手的賽璐璐換個更近的取景重拍，壓暗當室內、淺景深遮像素"""
    frame = cam(GIRL, 0.56, 0.52, fx.lerp(5.0, 5.6, fx.ease(u)))
    frame = fx.blur(frame, 5)
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
    t = fi / FPS                             # 0~4s
    idx = int(2.2 * t + 2.3 * t * t)         # 輪放越來越快（切換間隔隨時間縮短）
    frame = _MONTAGE[idx % len(_MONTAGE)]()
    frame = fx.rgb_split(frame, int(3 + 3 * t))
    frame = fx.blur(frame, int(2 + 2.2 * t))         # 畫面越來越糊
    amp = 16.0 * max(0.0, 1.0 - t / 1.1)             # 抖動前 1.1s 由大衰減到 0，之後平緩
    if amp > 0.2:
        frame = fx.shake(frame, amp, seed=fi * 7 + 1)
    return frame


# ---- 52~60s CRT 微光 → 推近 → 畫面停留 → 黑（無字） ----

def sh_last_signal(u, fi):
    frame = cam(CRT, 0.5, 0.52, fx.lerp(1.15, 1.5, fx.ease(u)))
    frame = fx.fade(frame, 0.5)
    frame = fx.scanlines(frame, 0.35)
    if u > 0.72:                             # 末段畫面停留後沒入黑
        frame = fx.fade(frame, 1.0 - fx.ease((u - 0.72) / 0.28))
    return frame


# ---- 60~69s 終端黑掉後浮出的 console 式片尾 ----

_CREDITS = [
    "> SIGNAL LOST",
    "",
    "  THE LAST SIGNAL",
    "",
    "  directed by",
    "    TSOU, HAO-CHE",
    "",
    "  rendered in pure opencv",
    "    numpy    python",
    "    os       math",
    "",
    "  with",
    "    claude",
    "",
    "  no one answered.",
]
_AMBER = (60, 200, 255)                       # 琥珀色映像管磷光（BGR）


def sh_credits(u, fi):
    frame = BLACK.copy()
    t = fi / FPS
    x0, y0, dy = 150, 132, 34
    last_shown = -1
    for i, line in enumerate(_CREDITS):
        appear = 0.4 + i * 0.42                # 逐行像終端機列印出來
        if t < appear:
            break
        a = min((t - appear) / 0.22, 1.0)      # 每行快速淡入
        col = tuple(int(c * a) for c in _AMBER)
        if line:
            cv2.putText(frame, line, (x0, y0 + i * dy),
                        cv2.FONT_HERSHEY_PLAIN, 1.5, col, 1, cv2.LINE_AA)
        last_shown = i
    # 閃爍游標，跟在最後印出的那行尾端
    if last_shown >= 0 and (fi // 11) % 2 == 0:
        cur = _CREDITS[last_shown]
        (tw, _), _ = cv2.getTextSize(cur, cv2.FONT_HERSHEY_PLAIN, 1.5, 1)
        cx = x0 + tw + 6
        cy = y0 + last_shown * dy
        cv2.rectangle(frame, (cx, cy - 15), (cx + 11, cy + 2), _AMBER, -1)
    frame = fx.scanlines(frame, 0.22)          # 保留一點映像管掃描線
    if u > 0.86:                               # 最後整體沒入黑
        frame = fx.fade(frame, 1.0 - (u - 0.86) / 0.14)
    return frame


# =====================================================================
# 時間軸（秒）
# =====================================================================

SHOTS = [
    (0.0, 10.0, sh_opening),
    (10.0, 18.0, sh_girl_roof),
    (18.0, 25.0, sh_hand_to_back),
    (25.0, 28.0, sh_cut_sky),
    (28.0, 33.0, sh_tower_push),
    (33.0, 38.0, sh_eye_open),
    (38.0, 40.5, sh_cut_terminal),
    (40.5, 42.5, sh_cut_hand2),
    (42.5, 44.5, sh_cut_button),
    (44.5, 48.0, sh_screen_reveal),
    (48.0, 52.0, sh_montage),
    (52.0, 60.0, sh_last_signal),
    (60.0, 69.0, sh_credits),
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
