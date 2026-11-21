# 英语语音情绪判断工具

把 Praat 测出的声学参数（平均音高、音高标准差、平均音量、语速）粘进来，自动判断英语语音的情绪（平静 / 高兴 / 悲伤 / 愤怒），并给出粗略的唤醒度与效价。

## 功能
- 单条判断：填一组数值 → 判断一次
- 批量判断：粘贴多行数据 → 逐行判断，可下载结果 CSV
- 判断逻辑透明、阈值可在代码顶部 `THRESHOLDS` 中调整

## 在线使用
部署到 Streamlit Community Cloud 后，用浏览器或微信打开应用链接即可。

## 本地运行
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 说明
结果仅供教学与研究参考。情绪判断采用规则打分，特征集思路参考 GeMAPS / eGeMAPS；高兴与愤怒同属高唤醒情绪，单靠均值参数区分有限。
