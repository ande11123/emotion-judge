# -*- coding: utf-8 -*-
"""
英语语音情绪判断小工具（Streamlit）
把 Praat 测出的声学参数粘进来，自动判断情绪（平静/高兴/悲伤/愤怒）。

说明：本工具用"规则打分"做四类情绪判断，并给出粗略的唤醒度/效价（维度模型）。
      阈值基于语音情绪分析常用参考区间（简化自 GeMAPS / eGeMAPS 思路），
      结果仅供教学与研究参考，可自行修改下方 THRESHOLDS 调整口径。
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="英语语音情绪判断", layout="wide")

# ==================== 阈值标准（可自行调整） ====================
THRESHOLDS = {
    # 平均音高 F0（Hz）—— 分性别
    "f0": {"女": {"low": 180, "high": 250},
           "男": {"low": 95,  "high": 160}},
    # 音高标准差（Hz，代表音高起伏幅度）—— 分性别
    "f0_std": {"女": {"low": 12, "high": 30},
               "男": {"low": 10, "high": 25}},
    # 平均音量 Intensity（dB）—— 不分性别
    "intensity": {"low": 58, "high": 70},
    # 语速（音节/字 每秒）—— 不分性别
    "rate": {"slow": 3.0, "fast": 5.0},
}

EMO_CN = {"neutral": "平静", "happy": "高兴", "sad": "悲伤", "angry": "愤怒"}


def band(value, low, high):
    """把数值映射到 low / mid / high 三档。"""
    if value <= low:
        return "low"
    if value >= high:
        return "high"
    return "mid"


def judge(gender, f0, f0_std, intensity, rate=None):
    """规则打分，返回 (得分, 原因, 主情绪列表)。"""
    fb = band(f0, THRESHOLDS["f0"][gender]["low"], THRESHOLDS["f0"][gender]["high"])
    sb = band(f0_std, THRESHOLDS["f0_std"][gender]["low"], THRESHOLDS["f0_std"][gender]["high"])
    ib = band(intensity, THRESHOLDS["intensity"]["low"], THRESHOLDS["intensity"]["high"])

    rb = None
    if rate is not None:
        if rate <= THRESHOLDS["rate"]["slow"]:
            rb = "slow"
        elif rate >= THRESHOLDS["rate"]["fast"]:
            rb = "fast"
        else:
            rb = "mid"

    scores = {"neutral": 0, "happy": 0, "sad": 0, "angry": 0}
    reason = {"neutral": [], "happy": [], "sad": [], "angry": []}

    # 1) 音高高低
    if fb == "mid":
        scores["neutral"] += 2; reason["neutral"].append("音高中等")
    elif fb == "high":
        scores["happy"] += 2; scores["angry"] += 2
        reason["happy"].append("音高偏高"); reason["angry"].append("音高偏高")
    else:
        scores["sad"] += 2; reason["sad"].append("音高偏低")

    # 2) 音高起伏幅度
    if sb == "low":
        scores["neutral"] += 2; scores["sad"] += 1
        reason["neutral"].append("音高平稳"); reason["sad"].append("音高平稳")
    elif sb == "high":
        scores["happy"] += 2; scores["angry"] += 2
        reason["happy"].append("音高起伏大"); reason["angry"].append("音高起伏大")
    else:
        scores["neutral"] += 1; reason["neutral"].append("音高起伏中等")

    # 3) 音量
    if ib == "mid":
        scores["neutral"] += 2; reason["neutral"].append("音量中等")
    elif ib == "high":
        scores["happy"] += 2; scores["angry"] += 2
        reason["happy"].append("音量偏大"); reason["angry"].append("音量偏大")
    else:
        scores["sad"] += 2; reason["sad"].append("音量偏小")

    # 4) 语速（可选）
    if rb is not None:
        if rb == "mid":
            scores["neutral"] += 1; reason["neutral"].append("语速中等")
        elif rb == "fast":
            scores["happy"] += 1; scores["angry"] += 1
            reason["happy"].append("语速偏快"); reason["angry"].append("语速偏快")
        else:
            scores["sad"] += 1; reason["sad"].append("语速偏慢")

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    top = ranked[0][1]
    winners = [k for k, v in ranked if v == top]
    return scores, reason, winners, ranked


def arousal_level(f0, f0_std, intensity):
    """粗略唤醒度：高音高/大音量/大起伏 => 唤醒高。"""
    pts = 0
    pts += 2 if intensity >= THRESHOLDS["intensity"]["high"] else (1 if intensity > THRESHOLDS["intensity"]["low"] else 0)
    if f0 >= 200:
        pts += 2
    elif f0 >= 120:
        pts += 1
    if f0_std >= 25:
        pts += 1
    return "高" if pts >= 4 else ("中" if pts >= 2 else "低")


def valence(winners):
    """粗略效价：按主情绪给正面/中性/负面。"""
    if "happy" in winners and len(winners) == 1:
        return "正面"
    if set(winners) <= {"sad", "angry"}:
        return "负面"
    if set(winners) == {"happy", "angry"}:
        return "中性偏激动（需进一步区分）"
    return "中性"


def _to_gender(x):
    x = str(x).strip().lower()
    if x in ("男", "male", "m"):
        return "男"
    if x in ("女", "female", "f"):
        return "女"
    return None


def parse_paste(text):
    """把粘贴的多行数据解析成 [(性别, f0, f0_std, intensity, rate), ...] 和错误列表。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows = []
    for ln in lines:
        if "\t" in ln:
            cells = ln.split("\t")
        elif "," in ln:
            cells = ln.split(",")
        else:
            cells = ln.split()
        rows.append([c.strip() for c in cells])

    if rows and _to_gender(rows[0][0]) is None:
        rows = rows[1:]  # 第一行是表头，跳过

    parsed, errors = [], []
    for i, r in enumerate(rows, start=1):
        if len(r) < 4:
            errors.append(f"第 {i} 行列数不足（至少 4 列）")
            continue
        g = _to_gender(r[0])
        if g is None:
            errors.append(f"第 {i} 行性别无法识别：{r[0]}")
            continue
        try:
            f0 = float(r[1]); f0_std = float(r[2]); intensity = float(r[3])
        except ValueError:
            errors.append(f"第 {i} 行数值解析失败")
            continue
        rate = None
        if len(r) >= 5 and r[4] != "":
            try:
                rate = float(r[4])
            except ValueError:
                rate = None
        parsed.append((g, f0, f0_std, intensity, rate))
    return parsed, errors


# ==================== 界面 ====================
st.title("英语语音情绪判断工具")
st.caption("把 Praat 测出的参数粘进来 → 自动判断 平静 / 高兴 / 悲伤 / 愤怒（规则打分，仅供研究参考）")

mode = st.radio("选择模式", ["单条判断", "批量判断"], horizontal=True)

if mode == "单条判断":
    c1, c2 = st.columns(2)
    gender = c1.radio("说话人性别", ["女", "男"], horizontal=True)
    rate_check = c2.checkbox("我有语速数据（可选）")

    col1, col2 = st.columns(2)
    f0 = col1.number_input("平均音高 F0（Hz）", min_value=0.0, value=200.0, step=1.0)
    f0_std = col2.number_input("音高标准差（Hz，代表起伏）", min_value=0.0, value=20.0, step=1.0)
    intensity = col1.number_input("平均音量 Intensity（dB）", min_value=0.0, value=65.0, step=1.0)
    rate = col2.number_input("语速（字/秒）", min_value=0.0, value=4.0, step=0.1) if rate_check else None

    if st.button("判断情绪", type="primary"):
        scores, reason, winners, ranked = judge(gender, f0, f0_std, intensity, rate)
        label = " / ".join(EMO_CN[w] for w in winners)

        st.subheader(f"判断结果：{label}")
        st.metric("唤醒度（粗略）", arousal_level(f0, f0_std, intensity))
        st.markdown(f"**效价（粗略）**：{valence(winners)}")

        st.write("**为什么这么判**（主情绪的依据）：")
        for w in winners:
            st.write("- " + "、".join(reason[w]) + " → " + EMO_CN[w])

        st.write("**各情绪得分**：")
        df = pd.DataFrame([{"情绪": EMO_CN[k], "得分": v} for k, v in ranked])
        st.bar_chart(df.set_index("情绪"))
        st.caption("注：高兴和愤怒都属'高唤醒'，单靠均值参数区分有限；两者打平时按'高唤醒情绪'提示。")

else:
    st.markdown("""
    **粘贴格式**（每行一段语音，用 Tab、逗号或空格分隔，可含表头）：
    ```
    性别  平均音高Hz  音高标准差Hz  平均音量dB  语速字/秒
    女    240        30           68         4.5
    男    110        12           60         3.0
    ```
    - 性别写：男 / 女 / male / female
    - 前 4 列必填；第 5 列语速可省略
    """)
    text = st.text_area("把数据粘到这里", height=180, placeholder="女\t240\t30\t68\t4.5\n男\t110\t12\t60\t3.0")

    if st.button("批量判断", type="primary") and text.strip():
        parsed, errors = parse_paste(text)
        if parsed:
            results = []
            for g, f0v, f0s, inten, r in parsed:
                scores, reason, winners, ranked = judge(g, f0v, f0s, inten, r)
                results.append({
                    "性别": g, "音高Hz": f0v, "标准差Hz": f0s, "音量dB": inten,
                    "语速": r if r is not None else "",
                    "主情绪": " / ".join(EMO_CN[w] for w in winners),
                    "唤醒度": arousal_level(f0v, f0s, inten),
                    "效价": valence(winners),
                })
            st.success(f"共判断 {len(results)} 条")
            out = pd.DataFrame(results)
            st.dataframe(out, use_container_width=True)

            csv = out.to_csv(index=False).encode("utf-8-sig")
            st.download_button("下载结果 CSV", csv, "emotion_result.csv", "text/csv")
        if errors:
            st.warning("以下行未成功解析：\n" + "\n".join(errors))

with st.expander("Praat 里怎么取这些数（速查）"):
    st.markdown("""
    - **平均音高 F0**：Sound → `Analyse periodicity` → `To Pitch (filtered autocorrelation)` → 选中 Pitch → `Query > Get mean`
    - **音高标准差**：同一 Pitch 对象 → `Query > Get standard deviation`
    - **平均音量**：Sound → `To Intensity` → 选中 Intensity → `Query > Get mean`
    - **语速**：框选一句话 → `Query > Get duration` 得到秒数，再数这句话的字数，用 字数 ÷ 秒数 算出
    - 建议按"单句"取值，整段取平均会把情绪抹平。
    """)

with st.expander("判断逻辑（透明规则）"):
    st.markdown("""
    每个参数被分成"低 / 中 / 高"三档，再按下面的经验规则加分，取总分最高的情绪：

    | 特征 | 平静 | 高兴 | 悲伤 | 愤怒 |
    |---|---|---|---|---|
    | 音高 | 中 | 高 | 低 | 高 |
    | 音高起伏 | 小 | 大 | 小 | 大 |
    | 音量 | 中 | 大 | 小 | 大 |
    | 语速 | 中 | 快 | 慢 | 快 |

    阈值在代码顶部 `THRESHOLDS` 里，可自行调整。
    """)
