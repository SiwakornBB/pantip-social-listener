import streamlit as st
import pandas as pd
import plotly.express as px
import re
import json
import google.generativeai as genai

# -------------------- Streamlit Page Config --------------------
st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.title("📊 Dashboard")

# -------------------- Helper Functions --------------------

def extract_aspects_from_summary(summary_text):
    """
    Extract aspect names from the AI summary.
    Ignores unwanted aspects like 'Sentiment' and 'N/A'.
    """
    aspect_pattern = re.compile(r"\*\*(.+?)\*\*:")
    aspects = []
    for line in summary_text.splitlines():
        match = aspect_pattern.match(line)
        if match and "สรุปโดยย่อ" not in match.group(1):
            aspects.append(match.group(1).strip())
    aspects = [a for a in aspects if a not in ["อารมณ์ (Sentiment)", "Sentiment", "N/A"]]
    return aspects

def extract_all_comments_by_forum(forums_text):
    """
    Extracts all comments from each forum thread.
    Returns a list of (forum_title, comments_list).
    """
    forums_comments = []
    for forum_text in forums_text:
        lines = forum_text.split('\n')
        title = lines[0]
        if title.startswith("หัวข้อ : "):
            title = title.replace("หัวข้อ : ", "", 1)
        comments = [line.split(":", 1)[-1].strip() for line in lines if line.startswith("คอมเมนต์ที่")]
        forums_comments.append((title, comments))
    return forums_comments

def get_aspect_sentiment_for_forums(forums_comments, aspects, model):
    """
    Uses the LLM to analyze each comment for aspect and sentiment.
    Returns a list of dicts with comment, aspect, and sentiment.
    """
    all_results = []
    for idx, (title, comments) in enumerate(forums_comments):
        if not comments:
            continue
        prompt = (
            f"หัวข้อกระทู้: {title}\n"
            "คุณคือ AI วิเคราะห์ความคิดเห็นใน Pantip\n"
            "สำหรับแต่ละคอมเมนต์ด้านล่าง ให้ระบุ Aspect (เลือกจาก: " +
            ", ".join(aspects) +
            ") ที่เกี่ยวข้องมากที่สุด และระบุอารมณ์ (Sentiment) จาก 3 ตัวเลือกนี้เท่านั้นว่าเป็น positive, neutral, หรือ negative\n"
            "ตอบกลับเป็น JSON list เท่านั้น ห้ามอธิบายเพิ่ม เช่น:\n"
            '[{"comment": "...", "aspect": "...", "sentiment": "..."}]\n\n'
            "Comments:\n"
        )
        for i, comment in enumerate(comments, 1):
            prompt += f"{i}. {comment}\n"
        response = model.generate_content(prompt)
        st.write(f"## DEBUG: LLM raw response (forum {idx+1})")
        st.write(response.text)
        json_text = response.text.strip()
        if not json_text:
            continue
        if not json_text.startswith("["):
            match = re.search(r"(\[.*\])", json_text, re.DOTALL)
            if match:
                json_text = match.group(1)
            else:
                continue
        try:
            result = json.loads(json_text)
            all_results.extend(result)
        except Exception as e:
            st.error(f"JSON decode error: {e}")
            continue
    return all_results

def clean_aspect_names(aspects):
    """
    Cleans aspect names to keep only the Thai part before any parenthesis.
    Removes English-only aspects and duplicates.
    """
    cleaned = []
    for a in aspects:
        th = re.sub(r"\s*\(.*?\)", "", a).strip()
        if re.search(r"[\u0E00-\u0E7F]", th) and th not in ["", "N/A"]:
            cleaned.append(th)
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for x in cleaned:
        if x not in seen:
            seen.add(x)
            result.append(x)
    # Add "ไม่ถูกจัดประเภท" if not already present
    if "ไม่ถูกจัดประเภท" not in result:
        result.append("ไม่ถูกจัดประเภท")
    return result

# -------------------- Main UI Logic --------------------

# Check for required session state
if "all_forums_text" not in st.session_state or not st.session_state["all_forums_text"]:
    st.warning("⚠️ กรุณาไปที่หน้าแรกเพื่อดึงข้อมูลกระทู้ก่อน")
    st.stop()

forums = st.session_state["all_forums_text"]

st.header("สรุปข้อมูลเบื้องต้น")
st.write(f"จำนวนกระทู้ที่ดึงมา: **{len(forums)}**")

# Show table of threads and comment counts
data = []
for i, forum_text in enumerate(forums):
    lines = forum_text.split('\n')
    title = lines[0]
    if title.startswith("หัวข้อ : "):
        title = title.replace("หัวข้อ : ", "", 1)
    num_comments = sum(1 for line in lines if line.startswith("คอมเมนต์ที่"))
    data.append({
        "Thread": f"{i+1}. {title[:40]}{'...' if len(title) > 40 else ''}",
        "Comments": num_comments
    })
df = pd.DataFrame(data)
st.subheader("รายละเอียดกระทู้")
st.dataframe(df, use_container_width=True)
st.subheader("จำนวนคอมเมนต์ต่อกระทู้")
fig = px.bar(df, x="Thread", y="Comments", labels={"Thread": "กระทู้", "Comments": "จำนวนคอมเมนต์"})
st.plotly_chart(fig, use_container_width=True)

# --- Summary Reference Section ---
st.markdown("---")
st.header("📄 สรุปจาก AI (อ้างอิง)")

if "llm_summary" in st.session_state and st.session_state["llm_summary"]:
    with st.expander("🤖 ดูสรุปจาก AI ที่ใช้เป็นฐานในการวิเคราะห์", expanded=False):
        st.markdown(st.session_state["llm_summary"])
        if "summary_generated_at" in st.session_state:
            st.caption(f"สรุปเมื่อ: {st.session_state['summary_generated_at']}")
else:
    st.info("📝 ยังไม่มีสรุปจาก AI - กรุณาไปที่หน้าแรกเพื่อสรุปกระทู้ก่อน")

# --- Aspect & Sentiment Extraction and Visualization ---
st.markdown("---")
st.header("🔎 วิเคราะห์ Aspect และ Sentiment (ระดับคอมเมนต์)")

# Only show the button if we have a summary and API key
if "input_for_llm" in st.session_state and st.session_state.get("input_for_llm") and st.session_state.get("all_forums_text"):
    if st.button("🚀 INITIALIZE: วิเคราะห์ Aspect & Sentiment ของคอมเมนต์"):
        # Check for API key and model
        if "api_key" not in st.session_state or not st.session_state["api_key"]:
            st.error("❌ กรุณาใส่ API Key ที่หน้าแรกก่อน")
            st.stop()
        try:
            genai.configure(api_key=st.session_state["api_key"])
            model_choice = st.session_state.get("model_choice", "gemini-2.5-flash")
            model = genai.GenerativeModel(model_choice)
        except Exception as e:
            st.error(f"❌ ไม่สามารถตั้งค่าโมเดล AI: {e}")
            st.stop()

        with st.spinner("🔎 กำลังดึง Aspect จากสรุป..."):
            aspects = extract_aspects_from_summary(st.session_state.get("llm_summary", ""))
            aspects = clean_aspect_names(aspects)
            st.write("## DEBUG: Aspects ที่ใช้กับ LLM")
            st.write(aspects)
            if not aspects:
                st.error("❌ ไม่พบ Aspect ในสรุป กรุณาสรุปใหม่")
                st.stop()
        with st.spinner("💬 กำลังดึงคอมเมนต์ทั้งหมด..."):
            forums_comments = extract_all_comments_by_forum(st.session_state["all_forums_text"])
            if not forums_comments:
                st.error("❌ ไม่พบคอมเมนต์ในข้อมูล")
                st.stop()
        with st.spinner("🤖 กำลังวิเคราะห์ Aspect & Sentiment ของคอมเมนต์ด้วย AI..."):
            aspect_sentiment_results = get_aspect_sentiment_for_forums(forums_comments, aspects, model)
            if not aspect_sentiment_results:
                st.error("❌ ไม่สามารถวิเคราะห์ Aspect & Sentiment ได้ กรุณาลองใหม่")
                st.stop()
            st.session_state["comment_aspect_sentiment"] = aspect_sentiment_results
            st.success("✅ วิเคราะห์ Aspect & Sentiment ของคอมเมนต์เสร็จสิ้น!")

# --- Visualization Section ---
if "comment_aspect_sentiment" in st.session_state and st.session_state["comment_aspect_sentiment"]:
    df_aspect = pd.DataFrame(st.session_state["comment_aspect_sentiment"])
    st.subheader("Pie Chart: สัดส่วน Sentiment ของแต่ละ Aspect (แสดงแบบกระชับ)")

    # Sort aspects so "ไม่ถูกจัดประเภท" is always last
    aspects_order = [a for a in df_aspect["aspect"].unique() if a != "ไม่ถูกจัดประเภท"]
    if "ไม่ถูกจัดประเภท" in df_aspect["aspect"].unique():
        aspects_order.append("ไม่ถูกจัดประเภท")

    sentiment_color_map = {"positive": "green", "negative": "red", "neutral": "gray"}
    sentiment_thai = {"positive": "POSITIVE", "negative": "NEGATIVE", "neutral": "NEUTRAL"}
    sentiment_color_html = {"positive": "#21ba45", "negative": "#db2828", "neutral": "#767676"}

    n_cols = 3
    for i in range(0, len(aspects_order), n_cols):
        cols = st.columns(n_cols)
        for j, aspect in enumerate(aspects_order[i:i+n_cols]):
            with cols[j]:
                st.markdown(
                    f"<div style='text-align:center;font-weight:bold;height:2.2em;line-height:1.1em;display:flex;align-items:center;justify-content:center;margin-bottom:0em;margin-top:0em'>{aspect}</div>",
                    unsafe_allow_html=True
                )
                df_aspect_sub = df_aspect[df_aspect["aspect"] == aspect]
                sentiment_counts = df_aspect_sub["sentiment"].value_counts().reset_index()
                sentiment_counts.columns = ["sentiment", "count"]

                # Find dominant sentiment (NEGATIVE wins ties, but if positive==negative, set to neutral)
                if not sentiment_counts.empty:
                    max_count = sentiment_counts["count"].max()
                    dominant_sentiments = sentiment_counts[sentiment_counts["count"] == max_count]["sentiment"].tolist()
                    if "positive" in dominant_sentiments and "negative" in dominant_sentiments and len(dominant_sentiments) == 2:
                        dominant_sentiment = "neutral"
                    elif "negative" in dominant_sentiments:
                        dominant_sentiment = "negative"
                    elif "positive" in dominant_sentiments:
                        dominant_sentiment = "positive"
                    else:
                        dominant_sentiment = dominant_sentiments[0]
                    color = sentiment_color_html.get(dominant_sentiment, "#767676")
                    st.markdown(
                        f"<div style='text-align:center;font-weight:bold;color:{color};margin-bottom:0.05em'>{sentiment_thai[dominant_sentiment]}</div>",
                        unsafe_allow_html=True
                    )

                fig = px.pie(
                    sentiment_counts,
                    names="sentiment",
                    values="count",
                    color="sentiment",
                    color_discrete_map=sentiment_color_map,
                )
                fig.update_traces(
                    textinfo='percent+label',
                    textposition='inside',
                    marker=dict(line=dict(width=0)),
                    domain=dict(x=[0,1], y=[0,1])
                )
                fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0), height=220)
                st.plotly_chart(fig, use_container_width=True, key=f"pie_{aspect}_{i}_{j}")

    # --- Stacked Bar Chart: Sentiment counts per aspect ---
    sentiment_order = ["positive", "negative", "neutral"]

    bar_df = df_aspect.groupby(["aspect", "sentiment"]).size().reset_index(name="count")
    bar_df["aspect"] = pd.Categorical(bar_df["aspect"], categories=aspects_order, ordered=True)
    bar_df["sentiment"] = pd.Categorical(bar_df["sentiment"], categories=sentiment_order, ordered=True)

    fig_vbar = px.bar(
        bar_df,
        x="aspect",
        y="count",
        color="sentiment",
        color_discrete_map=sentiment_color_map,
        labels={"aspect": "Aspect", "count": "จำนวนคอมเมนต์", "sentiment": "Sentiment"},
        title="จำนวนคอมเมนต์แต่ละ Sentiment ในแต่ละ Aspect (Vertical Stacked Bar)"
    )
    fig_vbar.update_layout(
        barmode="stack",
        xaxis_title="Aspect",
        yaxis_title="จำนวนคอมเมนต์",
        showlegend=True,
        height=350
    )
    fig_vbar.update_traces(texttemplate=None, textposition=None)

    # Add only one sum number on top of each bar
    total_counts = df_aspect.groupby("aspect")["comment"].count().reindex(aspects_order, fill_value=0)
    for i, aspect in enumerate(aspects_order):
        fig_vbar.add_annotation(
            x=aspect,
            y=total_counts[aspect],
            text=str(total_counts[aspect]),
            showarrow=False,
            font=dict(size=14, color="black"),
            yshift=2,
            yanchor="bottom"
        )

    st.plotly_chart(fig_vbar, use_container_width=True)

    # --- Overall Sentiment Horizontal Bar ---
    overall_counts = df_aspect["sentiment"].value_counts().reindex(sentiment_order, fill_value=0)
    overall_df = pd.DataFrame({
        "Sentiment": sentiment_order,
        "Count": [overall_counts[s] for s in sentiment_order]
    })

    fig_overall = px.bar(
        overall_df,
        x="Count",
        y="Sentiment",
        orientation="h",
        color="Sentiment",
        color_discrete_map=sentiment_color_map,
        title="อารมณ์โดยรวมของ Keyword (ตามจำนวนคอมเมนต์)",
        labels={"Count": "จำนวนคอมเมนต์", "Sentiment": "Sentiment"}
    )
    fig_overall.update_layout(showlegend=False, xaxis_title="จำนวนคอมเมนต์", yaxis_title="Sentiment")
    st.plotly_chart(fig_overall, use_container_width=True)

    # --- Single Horizontal Stacked Bar: Overall Sentiment Distribution ---
    total_comments = overall_counts.sum()
    bar_data = pd.DataFrame({
        "Sentiment": sentiment_order,
        "Count": [overall_counts[s] for s in sentiment_order],
        "Percent": [f"{(overall_counts[s]/total_comments*100):.1f}%" if total_comments > 0 else "0.0%" for s in sentiment_order]
    })

    fig_single_bar = px.bar(
        bar_data,
        x="Count",
        y=["รวมทุก Aspect"] * len(bar_data),
        color="Sentiment",
        color_discrete_map=sentiment_color_map,
        orientation="h",
        text="Percent",
        labels={"Count": "จำนวนคอมเมนต์", "Sentiment": "Sentiment"},
        title="อารมณ์โดยรวมของ Keyword (ตามสัดส่วน)"
    )
    fig_single_bar.update_layout(
        barmode="stack",
        showlegend=False,
        xaxis_title="จำนวนคอมเมนต์",
        yaxis_title="",
        yaxis=dict(showticklabels=False),
        height=300
    )
    fig_single_bar.update_traces(textposition="auto")
    st.plotly_chart(fig_single_bar, use_container_width=True)

    # Download CSV button
    csv = df_aspect.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="⬇️ ดาวน์โหลดผล Aspect & Sentiment เป็น CSV",
        data=csv,
        file_name="aspect_sentiment_output.csv",
        mime="text/csv"
    )

    st.dataframe(df_aspect)
else:
    st.info("กด INITIALIZE เพื่อเริ่มวิเคราะห์ Aspect & Sentiment ของคอมเมนต์")
    aspects_order = []

# --- New Comment Browser Section ---
st.markdown("---")
st.markdown("### 🗂️ เรียกดูคอมเมนต์ตาม Aspect พร้อมตัวเลือกการเรียงลำดับ")

if "comment_aspect_sentiment" in st.session_state and st.session_state["comment_aspect_sentiment"]:
    df_aspect = pd.DataFrame(st.session_state["comment_aspect_sentiment"])
    aspects_order = [a for a in df_aspect["aspect"].unique() if a != "ไม่ถูกจัดประเภท"]
    if "ไม่ถูกจัดประเภท" in df_aspect["aspect"].unique():
        aspects_order.append("ไม่ถูกจัดประเภท")

    # Select aspect
    selected_aspect = st.selectbox(
        "เลือก Aspect ที่ต้องการดูคอมเมนต์",
        aspects_order,
        index=0 if aspects_order else None
    )

    # Select sentiment sort order
    sort_options = {
        "Positive → Negative → Neutral": ["positive", "negative", "neutral"],
        "Negative → Positive → Neutral": ["negative", "positive", "neutral"],
        "Neutral → Positive → Negative": ["neutral", "positive", "negative"]
    }
    selected_sort = st.selectbox(
        "เรียงลำดับคอมเมนต์ตาม Sentiment",
        list(sort_options.keys()),
        index=0
    )
    sort_order = sort_options[selected_sort]

    # Filter and sort comments
    df_browser = df_aspect[df_aspect["aspect"] == selected_aspect]
    df_browser["sentiment"] = pd.Categorical(df_browser["sentiment"], categories=sort_order, ordered=True)
    df_browser = df_browser.sort_values("sentiment")

    st.markdown(f"#### คอมเมนต์ใน Aspect: {selected_aspect} ({len(df_browser)} คอมเมนต์)")
    st.dataframe(df_browser[["comment", "sentiment"]], use_container_width=True)
else:
    st.info("กรุณากด INITIALIZE เพื่อวิเคราะห์ Aspect & Sentiment ก่อนจึงจะสามารถเรียกดูคอมเมนต์ได้")

# -------------------- Sidebar: Configuration & Instructions --------------------

st.sidebar.markdown("## 🔑 Configuration")
api_key = st.sidebar.text_input(
    "Google Gemini API Key",
    value=st.session_state.get("api_key", ""),
    type="password",
    help="ใส่ Google Gemini API Key ของคุณ (ได้จาก https://makersuite.google.com/app/apikey)"
)
st.session_state["api_key"] = api_key
if not api_key:
    st.sidebar.warning("⚠️ กรุณาใส่ API Key ก่อนใช้งาน")

st.sidebar.markdown("---")
st.sidebar.markdown("## 🤖 เลือกโมเดล AI")
model_choice = st.sidebar.selectbox(
    "เลือกโมเดล Gemini",
    options=[
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite-preview-06-17",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite"
    ],
    index=1 if st.session_state.get("model_choice") is None else
          ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite-preview-06-17", "gemini-2.0-flash", "gemini-2.0-flash-lite"].index(st.session_state.get("model_choice")),
    help="เลือกโมเดล Gemini ที่ต้องการใช้"
)
st.session_state["model_choice"] = model_choice

# Show model info
model_info = {
    "gemini-2.5-pro": "🎯 ความแม่นยำสูง เหมาะกับงานวิเคราะห์เชิงลึก",
    "gemini-2.5-flash": "⚡ เร็วและประหยัด Token (ค่าเริ่มต้น)",
    "gemini-2.5-flash-lite-preview-06-17": "🧪 รุ่นทดลอง ประหยัด Token มาก",
    "gemini-2.0-flash": "⚡ เร็วและประหยัด Token",
    "gemini-2.0-flash-lite": "🧪 รุ่นทดลอง ประหยัด Token มาก"
}
st.sidebar.info(model_info[model_choice])

st.sidebar.markdown("---")
st.sidebar.markdown("## 📖 วิธีการใช้งาน")
st.sidebar.markdown("1. รับ API Key จาก [Google AI Studio](https://makersuite.google.com/app/apikey)")
st.sidebar.markdown("2. ใส่ API Key ในช่องด้านบน")
st.sidebar.markdown("3. เลือกโมเดลที่ต้องการ")
st.sidebar.markdown("4. ใช้งานฟีเจอร์ต่าง ๆ ในหน้านี้")

st.sidebar.markdown("---")
st.sidebar.markdown("## ℹ️ ข้อมูลเพิ่มเติม")
st.sidebar.markdown("- แอปนี้ใช้สำหรับวิเคราะห์ความเห็นใน Pantip")
st.sidebar.markdown("- ข้อมูลจะถูกสรุปด้วย AI")
st.sidebar.markdown("- API Key จะไม่ถูกเก็บบันทึก")
st.sidebar.markdown("- เช็คโควต้าได้ที่ [Google AI Studio](https://makersuite.google.com/app/apikey)")