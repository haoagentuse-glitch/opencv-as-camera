# DECISIONS

- 結尾 CRT 文字用英文 "IS ANYONE STILL THERE?" ＋ cv2.putText｜證據：OpenCV putText 不支援 CJK，使用者拍板不引入 Pillow｜推翻條件：使用者想要中文 → 引入 Pillow 畫那一句或另供文字 PNG
- 輸出 4:3 960x720 無聲 mp4（mp4v）｜證據：使用者拍板；skeleton 實測 mp4v 可寫可讀｜推翻條件：播放器不吃 mp4v → ffmpeg 轉封裝 H.264（僅封裝不違反 OpenCV 限定）
- 運鏡用 warpAffine 次像素取樣，不用整數裁切+resize｜證據：60 秒慢推每格位移遠小於 1px，整數裁切會階梯抖動｜推翻條件：實看發現 warpAffine 造成畫質問題
- 三個 mp4 當預拍賽璐璐微動 loop，pingpong 循環取格｜證據：素材自帶頭髮/衣角/雲動態，正是劇本 10~18s 要的效果｜推翻條件：pingpong 來回感太明顯
- 蒙太奇 5 frames（約 0.21s）一 cut，特效強度隨進度線性爬升｜證據：劇本指定每張 0.2 秒｜推翻條件：使用者看片覺得節奏不對
