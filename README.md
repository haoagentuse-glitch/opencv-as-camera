# 最後一封訊息 · The Last Signal

用**純 OpenCV**（外加 NumPy）把 5 張圖與 3 段微動素材，拼成一支 **69 秒**的賽璐璐風格短片。
沒有逐格作畫——全靠**攝影機運鏡、蒙太奇剪接、Layer 疊合、Mask 遮罩、停格**，讓少量素材扮演大量鏡頭。

> 一座沒有人的城市。一位少女走進停止運作的通訊塔，打開舊終端，收到一封來自過去的訊息。畫面停留。黑。

風格取向：賽璐璐 × 攻殼機動隊 × 今敏 × 宮崎駿式留白。4:3、960×720、無聲。

## 核心概念

早期賽璐璐動畫很少為每個鏡頭重畫——攝影師把同一張賽璐璐放在不同背景、不同鏡位下反覆拍攝。
這個實驗把這套「靠攝影與剪接創造鏡頭」的成本控制手法，用 OpenCV 重現：**一張圖，靠裁切／縮放／閾值／色偏／遮罩，就能變成全身鏡、特寫、剪影、電視畫面等多個鏡頭。**

## 執行

```bash
python -m venv venv
# Windows: venv\Scripts\activate    /  macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

python film.py            # 渲染全片 → output/final.mp4
python film.py preview    # 每個鏡頭抽 1 格存 output/preview/，供檢查構圖
```

`output/` 不進版控，執行後在本機生成。

## 時間軸

| 秒 | 鏡頭 | 手法 |
|---|---|---|
| 0–10 | 黑 → 城市，等速前推 | Fade in + Camera Zoom（雲用影片自帶動態） |
| 10–18 | 少女屋頂停格 | 靜態推進 → 乾淨影片微動 → 凍結續推 |
| 18–25 | 手 blur 進場，拉遠到整個背影 | 由糊轉清 + Camera Pull-back |
| 25–28 | 天空一拍 | 裁切上緣天空 |
| 28–33 | 通訊塔推近，末段沒入黑 | Camera Push + Fade to black |
| 33–38 | 睜眼式開場，邊張眼邊平移掃視 | Eyelid Mask（慢起快開）+ Pan |
| 38–48 | 終端四連 Cut → 螢幕亮起 | Hard Cut + Radial Mask Reveal |
| 48–52 | 快速蒙太奇，每張約 0.2s | RGB Split + Blur + Shake + Hard Cut |
| 52–60 | CRT 微光推近 → 畫面停留 → 黑 | Zoom + Scanlines + Fade |
| 60–69 | Console 式片尾 | 逐行列印 + 閃爍游標 |

## 架構

```
film.py   時間軸（Shot 清單）＋渲染主迴圈＋VideoWriter
fx.py     無狀態特效／運鏡函式庫
腳本.md   原始劇本與分鏡構想
assets/   靜態圖與微動素材（1–5 .png/.jpg、1–3 .mp4）
```

`fx.py` 提供的技法：`camera`／`cam_frac`（次像素運鏡）、`ease`／`lerp`（緩動）、`pingpong`（微動 loop）、`fade`、`blur`、`rgb_split`、`shake`、`scanlines`、`vignette`、`grain`、`typewriter`，以及三種遮罩 `door_mask`／`eyelid_mask`／`radial_mask` ＋ `apply_mask`。

## 幾個設計決定

- **運鏡用 `warpAffine` 次像素取樣**，不用整數裁切 + resize——60 秒慢推每格位移遠小於 1px，整數裁切會階梯抖動。
- **三段 mp4 當預拍的賽璐璐微動 loop**，`pingpong` 循環取格；素材自帶頭髮／衣角／雲的動態，正好是「停格但有微動」要的效果。
- **屋頂鏡頭避開素材中段破圖**：midjourney 生成影片中段裙擺會融化，只取乾淨前段微動再凍結；同時鏡頭前段推快，約 13s 把下半身連裙子推出畫面下緣，收成胸像／臉部特寫。
- **蒙太奇的節奏是動態的**：抖動前段大、約 1s 後衰減到 0；切換越來越快、blur 越來越重，色偏同步加強。

## 素材說明

`*.png` / `*.jpg` / `*.mp4` 為 midjourney 生成的概念素材，僅供此實驗展示用途。程式碼本身以 MIT 授權。

## 授權

程式碼採 [MIT License](LICENSE)。
