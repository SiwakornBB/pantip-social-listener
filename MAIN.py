import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import time
import google.generativeai as genai
import urllib.parse
from datetime import datetime
from selenium.webdriver.chrome.options import Options
import random

# -------------------- Streamlit Page Config --------------------
st.set_page_config(
    page_title="Pantip Social Listener",
    page_icon="👂",
    layout="centered",
    initial_sidebar_state="expanded"
)
st.title("สรุปกระทู้ Pantip ด้วย AI")

# -------------------- Session State Initialization --------------------
if "api_key" not in st.session_state:
    st.session_state["api_key"] = None
if "model_choice" not in st.session_state:
    st.session_state["model_choice"] = None

# -------------------- Sidebar: API Key & Model Selection --------------------
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
    index=1,
    help="เลือกโมเดล Gemini ที่ต้องการใช้"
)
st.session_state["model_choice"] = model_choice

# Optional: Sentiment analysis toggle
st.sidebar.markdown("## 🧠 ตัวเลือกเพิ่มเติม")
sentiment_toggle = st.sidebar.toggle(
    "📊 วิเคราะห์ความรู้สึกเบื้องต้น (Basic Sentiment Analysis)", value=True
)

# Show model info
model_info = {
    "gemini-2.5-pro": "🎯 ความแม่นยำสูง เหมาะกับงานวิเคราะห์เชิงลึก",
    "gemini-2.5-flash": "⚡ เร็วและประหยัด Token (ค่าเริ่มต้น)",
    "gemini-2.5-flash-lite-preview-06-17": "🧪 รุ่นทดลอง ประหยัด Token มาก",
    "gemini-2.0-flash": "⚡ เร็วและประหยัด Token",
    "gemini-2.0-flash-lite": "🧪 รุ่นทดลอง ประหยัด Token มาก"
}
st.sidebar.info(model_info[model_choice])

# API Key Test
if api_key:
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(model_choice)
        st.sidebar.markdown("---")
        st.sidebar.markdown("## 📊 API Status")
        st.sidebar.success(f"🤖 โมเดล: {model_choice}")
        st.sidebar.info("💡 เช็คโควต้าที่ [Google AI Studio](https://makersuite.google.com/app/apikey)")
        if st.sidebar.button("🧪 ทดสอบ API"):
            with st.spinner("กำลังทดสอบ API..."):
                try:
                    test_response = model.generate_content("Hello, respond in Thai")
                    st.sidebar.success("✅ API ทำงานปกติ")
                    if hasattr(test_response, 'usage_metadata'):
                        st.sidebar.write(f"**Token ที่ใช้ในการทดสอบ:** {test_response.usage_metadata.total_token_count}")
                except Exception as e:
                    st.sidebar.error(f"❌ API Error: {e}")
    except Exception as e:
        st.sidebar.error(f"❌ API Key ไม่ถูกต้อง: {e}")

# -------------------- Main Content: User Inputs --------------------
keyword = st.text_input(
    "ค้นหาด้วยคีย์เวิร์ด (Keyword)",
    value=st.session_state.get("keyword", ""),
)
st.session_state["keyword"] = keyword

sort_options = ["เกี่ยวข้องมากที่สุด", "กระทู้ใหม่ที่สุด"]
sort_option = st.selectbox(
    "เลือกวิธีเรียงลำดับ (Sort by)",
    options=sort_options,
    index=sort_options.index(st.session_state.get("sort_option", "กระทู้ใหม่ที่สุด")),
)
st.session_state["sort_option"] = sort_option

max_posts = st.number_input(
    "จำนวนกระทู้สูงสุดที่ต้องการ (Max posts)",
    min_value=1, max_value=30,
    value=st.session_state.get("max_posts", 15),
    step=1
)
st.session_state["max_posts"] = max_posts

date_filter = st.date_input(
    "กรองเฉพาะกระทู้หลังวันที่ (Filter posts after date)",
    value=st.session_state.get("date_filter", None),
    help="เลือกวันที่เพื่อกรองเฉพาะกระทู้ใหม่ หรือปล่อยว่างเพื่อดูทั้งหมด"
)
st.session_state["date_filter"] = date_filter

# -------------------- Build Pantip Search URL --------------------
keyword_encoded = urllib.parse.quote_plus(keyword)
if sort_option == "กระทู้ใหม่ที่สุด":
    search_url = f"https://pantip.com/search?q={keyword_encoded}&timebias=true"
else:
    search_url = f"https://pantip.com/search?q={keyword_encoded}"

st.write(f"Pantip Search URL: [คลิกที่นี่]({search_url})")

# -------------------- Scrape Pantip Threads --------------------
def parse_thai_date(date_str):
    """
    Parse Thai date string like '21 มิ.ย. 67' to datetime object.
    Returns None if parsing fails.
    """
    try:
        thai_months = {
            'ม.ค.': 1, 'ก.พ.': 2, 'มี.ค.': 3, 'เม.ย.': 4, 'พ.ค.': 5, 'มิ.ย.': 6,
            'ก.ค.': 7, 'ส.ค.': 8, 'ก.ย.': 9, 'ต.ค.': 10, 'พ.ย.': 11, 'ธ.ค.': 12
        }
        parts = date_str.strip().split()
        if len(parts) != 3:
            return None
        day = int(parts[0])
        month = thai_months.get(parts[1])
        year = int(parts[2])
        if year < 100:
            year += 2500
        year -= 543
        if month is None:
            return None
        return datetime(year, month, day)
    except Exception:
        return None

# -------------------- Main Button: Summarize Pantip Threads --------------------
if st.button("สรุปกระทู้ Pantip", disabled=not api_key or not keyword):
    if not api_key:
        st.error("❌ กรุณาใส่ API Key ก่อนใช้งาน")
    elif not keyword:
        st.error("❌ กรุณาใส่คีย์เวิร์ดที่ต้องการค้นหา")
    else:
        st.info(f"คุณเลือก {max_posts} กระทู้ | Keyword: {keyword} | Sort: {sort_option}")

        # --- Start Selenium Browser ---
        with st.spinner("🔍 กำลังเปิดเบราว์เซอร์และค้นหา..."):
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")

            driver = webdriver.Chrome(options=chrome_options)
            driver.get(search_url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.pt-list-item h2 a"))
            )

        # --- Load More Results if Needed ---
        with st.spinner("📜 กำลังโหลดผลการค้นหาเพิ่มเติม..."):
            max_tries = 10
            for _ in range(max_tries):
                threads = driver.find_elements(By.CSS_SELECTOR, "li.pt-list-item h2 a")
                if len(threads) >= max_posts:
                    break
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

        # --- Parse Search Results ---
        with st.spinner("🔗 กำลังประมวลผลลิงก์กระทู้..."):
            soup = BeautifulSoup(driver.page_source, "html.parser")
            threads = soup.select("li.pt-list-item h2 a")[:max_posts]
            thread_urls = [t['href'] if t['href'].startswith("http") else "https://pantip.com" + t['href'] for t in threads]

            all_forums_text = []

            # Filter by date if needed
            if date_filter:
                filtered_urls = []
                date_elements = soup.select("li.pt-list-item .pt-sm-toggle-date-hide")
                for i, url in enumerate(thread_urls):
                    if i < len(date_elements):
                        date_str = date_elements[i].get_text(strip=True)
                        post_date = parse_thai_date(date_str)
                        if post_date and post_date.date() >= date_filter:
                            filtered_urls.append(url)
                thread_urls = filtered_urls
                st.info(f"📅 กรองแล้ว: เหลือ {len(thread_urls)} กระทู้หลังวันที่ {date_filter}")
            else:
                st.info(f"📊 ไม่กรองตามวันที่: รวม {len(thread_urls)} กระทู้")

            if not thread_urls:
                st.warning("❌ ไม่พบกระทู้ที่ตรงกับเงื่อนไขที่ค้นหา")
                st.stop()

        # --- Scrape Each Thread ---
        st.info("📝 กำลังดึงข้อมูลเนื้อหากระทู้...")
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, url in enumerate(thread_urls):
            progress = (i + 1) / len(thread_urls)
            progress_bar.progress(progress)
            status_text.text(f"กำลังดึงข้อมูลกระทู้ที่ {i+1}/{len(thread_urls)}")
            try:
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "display-post-story"))
                )
                # Click all "see more replies" buttons
                for _ in range(3):
                    see_more_buttons = driver.find_elements(By.CSS_SELECTOR, "a.reply.see-more")
                    if not see_more_buttons:
                        break
                    for btn in see_more_buttons:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.1)
                try:
                    WebDriverWait(driver, 5).until(
                        lambda d: len(d.find_elements(By.CLASS_NAME, "display-post-story")) > 1
                    )
                except Exception:
                    pass
                time.sleep(1)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                header = soup.find("h2", {"class": "display-post-title"})
                forum_texts = []
                if header:
                    forum_texts.append(f"หัวข้อ : {header.text}")
                comments = soup.find_all("div", {"class": "display-post-story"})
                for idx, comment in enumerate(comments, start=0):
                    text = comment.get_text(separator=" ", strip=True)
                    text = re.sub(r'\s+', ' ', text)
                    label = f"เนื้อหา : {text}" if idx == 0 else f"คอมเมนต์ที่ {idx} : {text}"
                    forum_texts.append(label)
                all_forums_text.append("\n".join(forum_texts))
                st.session_state["all_forums_text"] = all_forums_text
                time.sleep(0.5)
                time.sleep(0.2)
                time.sleep(random.uniform(1, 2))
            except Exception as e:
                st.warning(f"Error scraping {url}: {e}")
                continue

        progress_bar.empty()
        status_text.empty()

        with st.spinner("🔒 กำลังปิดเบราว์เซอร์..."):
            driver.quit()

        st.success(f"✅ ดึงข้อมูลเสร็จสิ้น! ได้ข้อมูลจาก {len(all_forums_text)} กระทู้")

        # --- Prepare Data for AI ---
        with st.spinner("📋 กำลังเตรียมข้อมูลสำหรับ AI..."):
            input_for_llm = "\n\n".join(all_forums_text)
            st.session_state["input_for_llm"] = input_for_llm
            with st.expander("🔎 ข้อความที่นำเข้า (คลิกเพื่อดู/ซ่อน)", expanded=False):
                st.text_area(
                    "ข้อความที่นำเข้า",
                    st.session_state["input_for_llm"],
                    height=300,
                    key="input_for_llm_preview",
                    disabled=True
                )

            model = genai.GenerativeModel(model_choice)
            prompt_parts = [
                "You are a LLM-powered social-listening application, tasked to summarize Pantip posts and comments into aspects in THAI LANGUAGE.",
                "Here are the texts you need to summarize:",
                st.session_state["input_for_llm"],
                "Summarize the information into each aspect in this format:",
                "**สรุปโดยย่อ**: {summary}",
                "**{aspect1}**: {aspect1_summary}",
                "**{aspect2}**: {aspect2_summary}",
                "and so on...",
                "Aspect is not the same as thread, it is what have been discussed.",
                "You must response in the format above.",
                "You must response in THAI LANGUAGE only.",
                "Every paragraph MUST have a new line between them"
            ]
            if sentiment_toggle:
                prompt_parts.insert(-2, "For each aspect, add a new line below the summary in this format:\n**อารมณ์ (Sentiment)**: <label> (positive😄, neutral😐, or negative😡)")
            prompt = "\n".join(prompt_parts)

        # --- AI Summarization ---
        with st.spinner("🤖 กำลังสรุปผลด้วย Gemini AI... กรุณารอสักครู่"):
            try:
                response = model.generate_content(prompt)
                st.success("✅ สรุปเสร็จสิ้น!")
                if hasattr(response, 'usage_metadata'):
                    st.info(f"🔢 Token ที่ใช้: {response.usage_metadata.total_token_count} "
                            f"(Input: {response.usage_metadata.prompt_token_count}, "
                            f"Output: {response.usage_metadata.candidates_token_count})")
                st.session_state["llm_summary"] = response.text
                st.rerun()
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาดในการสรุปผล: {e}")

# -------------------- Show Latest Summary --------------------
if "llm_summary" in st.session_state and st.session_state["llm_summary"]:
    st.markdown("---")
    st.markdown("### 📊 สรุปจากโมเดลภาษา")
    st.markdown(st.session_state["llm_summary"])

# -------------------- Show Input Preview --------------------
if "input_for_llm" in st.session_state:
    st.markdown("---")
    with st.expander("🔎 ข้อความที่นำเข้า (คลิกเพื่อดู/ซ่อน)", expanded=False):
        st.text_area(
            "ข้อความที่นำเข้า",
            st.session_state["input_for_llm"],
            height=300,
            key="input_for_llm_preview",
            disabled=False
        )

# -------------------- Regenerate Summary with Selected Threads --------------------
if "input_for_llm" in st.session_state:
    st.markdown("---")
    st.markdown("### 🎯 เลือกกระทู้ที่ต้องการวิเคราะห์")
    if "all_forums_text" in st.session_state and st.session_state["all_forums_text"]:
        if len(st.session_state.get("selected_forums", [])) != len(st.session_state["all_forums_text"]):
            st.session_state["selected_forums"] = [True] * len(st.session_state["all_forums_text"])

        forum_options = []
        for i, forum_text in enumerate(st.session_state["all_forums_text"]):
            lines = forum_text.split('\n')
            title = lines[0] if lines else f"กระทู้ที่ {i+1}"
            if title.startswith("หัวข้อ : "):
                title = title.replace("หัวข้อ : ", "", 1)
            if len(title) > 60:
                title = title[:60] + "..."
            forum_options.append(f"{i+1}. {title}")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✅ เลือกทั้งหมด", key="select_all"):
                st.session_state["selected_forums"] = [True] * len(st.session_state["all_forums_text"])
                st.rerun()
        with col2:
            if st.button("❌ ยกเลิกทั้งหมด", key="deselect_all"):
                st.session_state["selected_forums"] = [False] * len(st.session_state["all_forums_text"])
                st.rerun()

        st.markdown("**เลือกกระทู้ที่ต้องการรวมในการวิเคราะห์:**")
        currently_selected = [i for i, selected in enumerate(st.session_state.get("selected_forums", [])) if selected]
        currently_selected_options = [forum_options[i] for i in currently_selected]

        def update_selected_forums():
            selected_options = st.session_state["forum_multiselect"]
            selected_forums = [False] * len(st.session_state["all_forums_text"])
            for option in selected_options:
                index = int(option.split('.')[0]) - 1
                selected_forums[index] = True
            st.session_state["selected_forums"] = selected_forums

        selected_options = st.multiselect(
            "เลือกกระทู้:",
            options=forum_options,
            default=currently_selected_options,
            key="forum_multiselect",
            help="เลือกกระทู้ที่ต้องการนำมาวิเคราะห์",
            on_change=update_selected_forums
        )

        st.session_state["selected_forums"] = [False] * len(st.session_state["all_forums_text"])
        for option in selected_options:
            index = int(option.split('.')[0]) - 1
            st.session_state["selected_forums"][index] = True

        selected_count = sum(st.session_state["selected_forums"])
        total_count = len(st.session_state["all_forums_text"])

        if selected_count == 0:
            st.warning("⚠️ กรุณาเลือกอย่างน้อย 1 กระทู้")
        else:
            st.info(f"📊 เลือกแล้ว: {selected_count}/{total_count} กระทู้")
            if st.toggle("🔍 แสดงตัวอย่างเนื้อหาที่เลือก", value=False):
                for i, forum_text in enumerate(st.session_state["all_forums_text"]):
                    if st.session_state["selected_forums"][i]:
                        lines = forum_text.split('\n')
                        title = lines[0]
                        if title.startswith("หัวข้อ : "):
                            title = title.replace("หัวข้อ : ", "", 1)
                        preview = forum_text
                        with st.expander(f"📄{i+1}. {title}", expanded=False):
                            st.text(preview)

    regenerate_disabled = (
        not st.session_state.get("all_forums_text") or 
        not any(st.session_state.get("selected_forums", []))
    )

    if st.button("🔄 สรุปใหม่ด้วย AI (ใช้กระทู้ที่เลือก)", disabled=regenerate_disabled):
        if not st.session_state.get("all_forums_text"):
            st.error("❌ ไม่พบข้อมูลกระทู้ กรุณาดึงข้อมูลใหม่")
        elif not any(st.session_state.get("selected_forums", [])):
            st.error("❌ กรุณาเลือกอย่างน้อย 1 กระทู้")
        else:
            with st.spinner("🤖 กำลังสรุปผลด้วย Gemini AI... กรุณารอสักครู่"):
                try:
                    selected_forums_text = [
                        forum_text for i, forum_text in enumerate(st.session_state["all_forums_text"])
                        if st.session_state["selected_forums"][i]
                    ]
                    filtered_input_for_llm = "\n\n".join(selected_forums_text)
                    selected_count = len(selected_forums_text)
                    st.info(f"📊 กำลังวิเคราะห์ {selected_count} กระทู้ที่เลือก")
                    with st.expander("🔎 ข้อความที่นำเข้า (กระทู้ที่เลือก)", expanded=False):
                        st.text_area("ข้อความที่นำเข้า", filtered_input_for_llm, height=300, key="filtered_input")
                    model = genai.GenerativeModel(model_choice)
                    prompt_parts = [
                        "You are a LLM-powered social-listening application, tasked to summarize Pantip posts and comments into aspects in THAI LANGUAGE.",
                        "Here are the texts you need to summarize:",
                        filtered_input_for_llm,
                        "Summarize the information into each aspect in this format:",
                        "**สรุปโดยย่อ**: {summary}",
                        "**{aspect1}**: {aspect1_summary}",
                        "**{aspect2}**: {aspect2_summary}",
                        "and so on...",
                        "Aspect is not the same as thread, it is what have been discussed.",
                        "You must response in the format above.",
                        "You must response in THAI LANGUAGE only.",
                        "Every paragraph MUST have a new line between them"
                    ]
                    if sentiment_toggle:
                        prompt_parts.insert(-2, "For each aspect, add a new line below the summary in this format:\n**อารมณ์ (Sentiment)**: <label> (positive😄, neutral😐, or negative😡)")
                    prompt = "\n".join(prompt_parts)
                    response = model.generate_content(prompt)
                    st.success(f"✅ สรุปเสร็จสิ้น! (จากกระทู้ที่เลือก {selected_count} กระทู้)")
                    if hasattr(response, 'usage_metadata'):
                        st.info(f"🔢 Token ที่ใช้: {response.usage_metadata.total_token_count} "
                                f"(Input: {response.usage_metadata.prompt_token_count}, "
                                f"Output: {response.usage_metadata.candidates_token_count})")
                    st.session_state["llm_summary"] = response.text
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดในการสรุปผล: {e}")

# -------------------- Sidebar Instructions --------------------
st.sidebar.markdown("---")
st.sidebar.markdown("## 📖 วิธีการใช้งาน")
st.sidebar.markdown("1. รับ API Key จาก [Google AI Studio](https://makersuite.google.com/app/apikey)")
st.sidebar.markdown("2. ใส่ API Key ในช่องด้านบน")
st.sidebar.markdown("3. ใส่คีย์เวิร์ดที่ต้องการค้นหา")
st.sidebar.markdown("4. คลิกปุ่ม 'สรุปกระทู้ Pantip'")

st.sidebar.markdown("---")
st.sidebar.markdown("## ℹ️ ข้อมูลเพิ่มเติม")
st.sidebar.markdown("- แอปนี้ใช้สำหรับวิเคราะห์ความเห็นใน Pantip")
st.sidebar.markdown("- ข้อมูลจะถูกสรุปด้วย AI")
st.sidebar.markdown("- API Key จะไม่ถูกเก็บบันทึก")
st.sidebar.markdown("- เช็คโควต้าได้ที่ [Google AI Studio](https://makersuite.google.com/app/apikey)")

# Store latest user input in session state for other pages
keyword = st.session_state["keyword"]
sort_option = st.session_state["sort_option"]