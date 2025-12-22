import streamlit as st
import random
import pandas as pd
import pytesseract
from PIL import Image, UnidentifiedImageError
import docx
import PyPDF2
import requests
import hashlib
import io
from gtts import gTTS
import os

# ============ initialization: session_state ============

if "user_words" not in st.session_state:
    st.session_state.user_words = []
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "game_mode" not in st.session_state:
    st.session_state.game_mode = "Scrambled Letters Game"

if "scramble_index" not in st.session_state:
    st.session_state.scramble_index = 0
if "scramble_score" not in st.session_state:
    st.session_state.scramble_score = 0
if "scramble_answers" not in st.session_state:
    st.session_state.scramble_answers = [""] * 10
if "scramble_scrambled" not in st.session_state:
    st.session_state.scramble_scrambled = [""] * 10

if "matching_words_generated" not in st.session_state:
    st.session_state.matching_words_generated = False
if "matching_answers" not in st.session_state:
    st.session_state.matching_answers = {}
if "matching_score" not in st.session_state:
    st.session_state.matching_score = 0

if "Listen_index" not in st.session_state:
    st.session_state.Listen_index = 0
if "Listen_score" not in st.session_state:
    st.session_state.Listen_score = 0
if "Listen_answers" not in st.session_state:
    st.session_state.Listen_answers = [""] * 10
if "Listen_played_words" not in st.session_state:
    st.session_state.Listen_played_words = []
if "waiting_for_next" not in st.session_state:
    st.session_state.waiting_for_next = False

if "fb_index" not in st.session_state:
    st.session_state.fb_index = 0
if "fb_score" not in st.session_state:
    st.session_state.fb_score = 0
if "fb_total_questions" not in st.session_state:
    st.session_state.fb_total_questions = 0
if "fb_answers" not in st.session_state:
    st.session_state.fb_answers = [""] * 10
if "fb_correct_answers" not in st.session_state:
    st.session_state.fb_correct_answers = []
if "fb_blanked_sentences" not in st.session_state:
    st.session_state.fb_blanked_sentences = []
if "fb_original_sentences" not in st.session_state:
    st.session_state.fb_original_sentences = []
if "fb_is_fallback" not in st.session_state:
    st.session_state.fb_is_fallback = []
if "fb_played_order" not in st.session_state:
    st.session_state.fb_played_order = []
if "fb_waiting_for_next" not in st.session_state:
    st.session_state.fb_waiting_for_next = False

if "translation_cache" not in st.session_state:
    st.session_state.translation_cache = {}

# ------------------- generate audio ------------------------
AUDIO_DIR = "audio"

def ensure_audio_folder():
    os.makedirs(AUDIO_DIR, exist_ok=True)

def generate_tts_audio(word):
    """If audio doesn't exist, generate TTS."""
    ensure_audio_folder()
    audio_path = os.path.join(AUDIO_DIR, f"{word}.mp3")

    if not os.path.exists(audio_path):
        tts = gTTS(word, lang='en')
        tts.save(audio_path)

    return audio_path
    
# ------------------- Baidu Translate API -------------------
APPID = "20251130002509027"  # <- 在此填入你的 APPID
KEY = "GtRhonqtdzGpchMRJuCq"    # <- 在此填入你的 KEY

def baidu_translate(q, from_lang="auto", to_lang="zh"):
    """Translate q using Baidu Translate. Returns q itself on failure."""
    if not q or not isinstance(q, str):
        return q
    # If user hasn't provided API keys, skip actual API calls and return the original word
    if APPID == "" or KEY == "":
        return q
    salt = str(random.randint(10000, 99999))
    sign_str = APPID + q + salt + KEY
    sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()
    url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    params = {"q": q, "from": from_lang, "to": to_lang,
              "appid": APPID, "salt": salt, "sign": sign}
    try:
        response = requests.get(url, params=params, timeout=3)
        data = response.json()
        if "error_code" in data:
            # fallback to original word if API returns an error
            return q
        return data["trans_result"][0]["dst"]
    except Exception:
        return q

# ------------------- Reading files -------------------
def read_file(file):
    """Read words from txt/csv/docx/pdf file-like object (Streamlit UploadFile)."""
    words = []
    name = file.name.lower()
    try:
        if name.endswith((".txt", ".csv")):
            content = file.read().decode("utf-8", errors="ignore")
            words = content.split()
        elif name.endswith(".docx"):
            doc = docx.Document(io.BytesIO(file.read()))
            for para in doc.paragraphs:
                words += para.text.split()
        elif name.endswith(".pdf"):
            reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    words += text.split()
    except Exception:
        return []
    return [w.strip() for w in words if w.strip()]

# ------------------- reading from images -------------------
def read_image(image_file):
    """Run OCR via pytesseract; return list of words. If OCR fails, return []."""
    try:
        img = Image.open(io.BytesIO(image_file.read()))
        text = pytesseract.image_to_string(img)
        words = [w.strip() for w in text.split() if w.strip()]
        return words
    except UnidentifiedImageError:
        return []
    except Exception:
        return []

# ------------------- Streamlit Design -------------------
st.set_page_config(page_title="Vocabuddy", layout="centered")
st.title("Hi, Welcome to Vocabuddy")
with st.expander("ℹ️ Vocabuddy Guidance/使用方式指引", expanded=False):
    st.markdown("""
        0. You’re in control of what you learn. 这是一个支持自主学习的学单词工具
        1. start small: 选择自己想要学习的英语单词（每次10个）
        2. 上传方式：手动输入、上传文件或图像
        3. 四个练习维度：音形义用
        4. 两种练习模式:针对性练习:专门训练短板（适合练习有一点点印象，但是掌握不够熟练的单词） or 默认模式：按顺序练习四个维度（适合完全不认识的单词）
        5. 每个练习后都有反馈，建议训练到准确率达至少80%以上，否则可以不断重复练习
        6. 词汇积累是个过程，关键在于重复重复重复！
        7. 没有7了，赶紧开始你的单词学习旅程吧～
            """)
            
# ------------------- Users Input -------------------
st.markdown("### 1. Provide 10 words")
words_input = st.text_area("Please enter 10 words (use space or enter in another line)", height=120)
if words_input:
    st.session_state.user_words = [w.strip() for w in words_input.split() if w.strip()]

col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Upload a file (txt/csv/docx/pdf)", type=["txt","csv","docx","pdf"])
    if uploaded_file:
        words_from_file = read_file(uploaded_file)
        if words_from_file:
            st.session_state.user_words = words_from_file
        else:
            st.warning("Couldn't read file or file empty. Make sure it's a supported format and contains text.")

with col2:
    uploaded_image = st.file_uploader("Upload an image (OCR)", type=["png","jpg","jpeg","bmp","tiff","tif"])
    if uploaded_image:
        words_from_image = read_image(uploaded_image)
        if words_from_image:
            st.session_state.user_words = words_from_image
        else:
            st.warning("OCR failed or no text found in image. Ensure tesseract is installed and image contains text.")

# ------------------- make sure 10 words -------------------
if st.session_state.user_words:
    st.info(f"Current words ({len(st.session_state.user_words)}): {st.session_state.user_words}")
    if len(st.session_state.user_words) != 10:
        st.warning("Please provide exactly 10 words to play (you can enter/upload more and then edit).")
        
# ------------------- choose game mode -------------------
# 卡片式游戏选择
if st.session_state.user_words and len(st.session_state.user_words) == 10:
    st.markdown("### 2. Choose Practice Mode 选择练习模式")
    
    # 简单的四个按钮代替下拉框
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🎧 音 Listen&choose", use_container_width=True, 
                    type="primary" if st.session_state.get("game_mode") == "Listen & Choose" else "secondary"):
            st.session_state.game_mode = "Listen & Choose"
            st.rerun()
    
    with col2:
        if st.button("✏️ 形 Spelling Game", use_container_width=True,
                    type="primary" if st.session_state.get("game_mode") == "Spelling Game" else "secondary"):
            st.session_state.game_mode = "Spelling Game"
            st.rerun()
    
    with col3:
        if st.button("🔤 义 Matching", use_container_width=True,
                    type="primary" if st.session_state.get("game_mode") == "Matching Game" else "secondary"):
            st.session_state.game_mode = "Matching Game"
            st.rerun()
    
    with col4:
        if st.button("📝 用 Fill in", use_container_width=True,
                    type="primary" if st.session_state.get("game_mode") == "Fill-in-the-Blank Game" else "secondary"):
            st.session_state.game_mode = "Fill-in-the-Blank Game"
            st.rerun()
    
    # 显示当前选择
    if st.session_state.game_mode:
        mode_display = {
            "Listen & Choose": "🎧 音 Listen&choose",
            "Spelling Game": "✏️ 形 Spelling Game", 
            "Matching Game": "🔤 义 Matching",
            "Fill-in-the-Blank Game": "📝 用 Fill in"
        }
        st.info(f"已选择: {mode_display.get(st.session_state.game_mode, st.session_state.game_mode)}")
        
if st.button("Start Game"):
    st.session_state.game_started = True
    original_words = st.session_state.user_words.copy()
    
    # 为各个游戏创建单词列表副本
    st.session_state.scramble_words = original_words.copy()
    random.shuffle(st.session_state.scramble_words)
    
    st.session_state.matching_words = original_words.copy()
    st.session_state.listen_words = original_words.copy()  
    st.session_state.fill_blank_words = original_words.copy()
    
    # reset spelling Game
    st.session_state.spelling_index = 0
    st.session_state.spelling_score = 0
    st.session_state.spelling_words = []
    st.session_state.spelling_progress = []
    
    # reset Matching Game
    st.session_state.matching_answers = {}
    st.session_state.matching_score = 0
    st.session_state.matching_words_generated = False
    
    # ⭐️ 新增：reset Listen & Choose Game ⭐️
    st.session_state.Listen_index = 0
    st.session_state.Listen_score = 0
    st.session_state.Listen_answers = [""] * 10
    st.session_state.Listen_played_words = []  # 清空播放顺序
    st.session_state.Listen_options_list = []  # 清空选项列表
    st.session_state.waiting_for_next = False  # 新增状态
    
    # reset Fill-in-the-Blank Game
    st.session_state.fb_index = 0
    st.session_state.fb_score = 0
    st.session_state.fb_total_questions = 0
    st.session_state.fb_answers = [""] * 10
    st.session_state.fb_correct_answers = []
    st.session_state.fb_blanked_sentences = []
    st.session_state.fb_original_sentences = []
    st.session_state.fb_is_fallback = []
    st.session_state.fb_played_order = []
    st.session_state.fb_waiting_for_next = False
        
        # 清除所有选择状态
    for key in list(st.session_state.keys()):
        if key.startswith("selected_") or key.startswith("fb_selected_"):
            del st.session_state[key]
        
    st.rerun()

# ______ 1. Listen & Choose  ______
# ______ 1. Listen & Choose ______
if st.session_state.get("game_started", False) and st.session_state.get("game_mode") == "Listen & Choose":
    st.subheader("🎧 Listen & Choose Game")
    
    # 获取当前索引和单词列表
    idx = st.session_state.Listen_index
    user_words = st.session_state.listen_words  # 使用专门为听音游戏准备的单词列表
    
    # 如果是第一题，初始化打乱的播放顺序
    if idx == 0 and len(st.session_state.Listen_played_words) == 0:
        # 创建打乱的播放顺序
        shuffled_words = user_words.copy()
        random.shuffle(shuffled_words)
        st.session_state.Listen_played_words = shuffled_words
    
    # 检查游戏是否结束
    if idx < len(user_words):
        # 获取当前题目信息
        current_audio_word = st.session_state.Listen_played_words[idx]  # 音频播放的单词（打乱顺序）
        correct_word = current_audio_word  # 正确答案就是播放的单词
        
        st.info(f"🎵 Word {idx + 1} of {len(user_words)}")

            # 精简游戏说明
        with st.expander("ℹ️ Game Instructions: 像婴儿学母语一样自然——先听音，后认词（查看具体步骤/规则可下拉)", expanded=False):
            st.markdown("""
            1. 🎵 Click the play button to hear the word pronunciation 点击播放按钮听单词发音（建议跟着音频念出发音）
            2. 🔤 Select the word you heard from the 10 options below 从下方10个单词中选择你听到的单词
            3. ✅ Submit your answer for immediate feedback 提交答案，即时获得反馈
            4. ➡️ View your score after completing all 10 words 完成10个单词后查看成绩
            """)
            
        # 生成并播放音频（自动播放）
        audio_file = generate_tts_audio(current_audio_word)
        st.audio(audio_file, format="audio/mp3", autoplay=True)
        
        # 显示所有10个单词作为选项（保持原始顺序）
        st.write("**Select the word you heard:**")
        
        # 创建两列布局显示10个选项
        cols = st.columns(2)  # 创建两列
        
        # 将10个单词分配到两列
        user_choice = None
        for i, word in enumerate(user_words):
            col_idx = i % 2  # 0表示第一列，1表示第二列
            with cols[col_idx]:
                # 使用radio或者button风格的选择
                if st.button(
                    word,
                    key=f"word_btn_{idx}_{i}",
                    use_container_width=True,
                    type="primary" if st.session_state.get(f"selected_{idx}") == word else "secondary"
                ):
                    # 记录用户选择
                    user_choice = word
                    st.session_state[f"selected_{idx}"] = word
                    st.rerun()
        
        # 显示当前选择的单词（如果有）
        if st.session_state.get(f"selected_{idx}"):
            st.markdown(f"**Your current selection:** `{st.session_state[f'selected_{idx}']}`")
        
        # 提交当前答案的按钮
        col1, col2 = st.columns(2)
        
        # 如果没有选择，禁用Submit按钮
        submit_disabled = st.session_state.get(f"selected_{idx}") is None
        
        with col1:
            if st.button("✅ Submit Answer", 
                        key=f"Listen_submit_{idx}", 
                        disabled=submit_disabled,
                        use_container_width=True):
                # 获取用户选择
                user_choice = st.session_state.get(f"selected_{idx}", "")
                
                # 保存答案
                st.session_state.Listen_answers[idx] = user_choice
                
                # 检查答案
                if user_choice == correct_word:
                    st.session_state.Listen_score += 1
                    st.success(f"✅ Correct! **'{correct_word}'** is right!")
                else:
                    st.error(f"❌ Wrong. You selected **'{user_choice}'**. The correct answer was **'{correct_word}'**.")
                
                # 清除当前选择
                if f"selected_{idx}" in st.session_state:
                    del st.session_state[f"selected_{idx}"]
                
                # 显示下一题按钮（等待用户点击）
                st.session_state.waiting_for_next = True
        
        # 如果等待下一题，显示Next按钮
        if st.session_state.get("waiting_for_next", False):
            with col2:
                if st.button("➡️ Next Word", 
                            key=f"next_{idx}", 
                            use_container_width=True):
                    st.session_state.Listen_index += 1
                    st.session_state.waiting_for_next = False
                    st.rerun()
    else:
        # 游戏结束：显示结果
        st.balloons()  # 庆祝动画
        st.success(f"🎮 Game Finished! Your score: **{st.session_state.Listen_score}/{len(user_words)}**")
        
        # 创建结果表格
        df_data = []
        for i in range(len(user_words)):
            audio_word = st.session_state.Listen_played_words[i]
            user_answer = st.session_state.Listen_answers[i]
            is_correct = user_answer == audio_word
            
            df_data.append({
                "Audio Word": audio_word,
                "Your Choice": user_answer,
                "Correct?": "✅" if is_correct else "❌"
            })
        
        df = pd.DataFrame(df_data)
        
        # 添加样式到表格
        st.subheader("📊 Your Results")
        
        # 使用st.dataframe以获得更好的控制
        st.dataframe(
            df,
            column_config={
                "Audio Word": "Heard Word",
                "Your Choice": "Your Answer",
                "Correct?": st.column_config.TextColumn(
                    "Result",
                    help="✅ = Correct, ❌ = Wrong"
                )
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 显示分数统计
        correct_count = sum(1 for result in df_data if result["Correct?"] == "✅")
        accuracy = (correct_count / len(user_words)) * 100
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Score", f"{st.session_state.Listen_score}/{len(user_words)}")
        with col2:
            st.metric("Accuracy", f"{accuracy:.1f}%")
        with col3:
            if accuracy >= 80:
                performance = "🏆 Excellent"
            elif accuracy >= 60:
                performance = "👍 Good"
            else:
                performance = "📚 Needs Practice"
            st.metric("Performance", performance)
        
        # 添加两个按钮
        st.markdown("---")
        st.write("### What would you like to do next?")
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🔄 Play Again", 
                        use_container_width=True,
                        help="Play the same game again with new random order"):
                # 重置听音游戏状态
                st.session_state.Listen_index = 0
                st.session_state.Listen_score = 0
                st.session_state.Listen_answers = [""] * 10
                st.session_state.Listen_played_words = []  # 清空，下次会重新生成
                st.session_state.waiting_for_next = False
                # 清除所有选择状态
                for key in list(st.session_state.keys()):
                    if key.startswith("selected_"):
                        del st.session_state[key]
                st.rerun()
        
        with col2:
            if st.button("🎮 Try Another Game", 
                        use_container_width=True,
                        help="Go back to choose a different game mode"):
                # 返回游戏选择界面
                st.session_state.game_started = False
                # 只重置听音游戏特定状态
                st.session_state.Listen_index = 0
                st.session_state.Listen_score = 0
                st.session_state.Listen_answers = [""] * 10
                st.session_state.Listen_played_words = []
                st.session_state.waiting_for_next = False
                # 清除所有选择状态
                for key in list(st.session_state.keys()):
                    if key.startswith("selected_"):
                        del st.session_state[key]
                st.rerun()
        
        with col3:
            if st.button("🏠 Main Menu", 
                        use_container_width=True,
                        help="Return to the main menu"):
                # 完全重置所有状态
                st.session_state.game_started = False
                st.session_state.game_mode = None
                # 清除所有听音游戏状态
                for key in ["Listen_index", "Listen_score", "Listen_answers", 
                           "Listen_played_words", "waiting_for_next"]:
                    if key in st.session_state:
                        del st.session_state[key]
                # 清除所有选择状态
                for key in list(st.session_state.keys()):
                    if key.startswith("selected_"):
                        del st.session_state[key]
                st.rerun()

# ------------------- 2. spelling Game -------------------
def play_spelling_game():
    """单词拼写游戏：根据音频提示拼写单词"""
    if st.session_state.get("game_started", False) and st.session_state.get("game_mode") == "Spelling Game":
        st.subheader("🎧 🔊 Spelling Game - Listen & Spell")
        
        # 初始化游戏状态
        if "spelling_index" not in st.session_state:
            st.session_state.spelling_index = 0
            st.session_state.spelling_score = 0
            st.session_state.spelling_words = []  # 存储打乱顺序的单词
            st.session_state.spelling_progress = []  # 存储每个单词的进度
        
        # 如果是第一次，初始化游戏数据
        if not st.session_state.spelling_words:
            # 从用户单词创建副本并打乱顺序
            original_words = st.session_state.user_words.copy()
            random.shuffle(original_words)
            st.session_state.spelling_words = original_words
            
            # 初始化每个单词的进度数据
            st.session_state.spelling_progress = []
            for word in original_words:
                word_data = {
                    "word": word.lower(),  # 正确答案（小写）
                    "revealed": [False] * len(word),  # 哪些字母已揭示
                    "attempted_letters": set(),  # 已尝试的字母
                    "wrong_letters": set(),  # 错误的字母
                    "wrong_count": 0,  # 错误次数
                    "max_wrong": 5,  # 最大错误次数
                    "hint_given": False,  # 是否已给提示
                    "completed": False,  # 是否完成
                    "user_input_history": []  # 用户输入历史
                }
                st.session_state.spelling_progress.append(word_data)
        
        # 获取当前题目
        idx = st.session_state.spelling_index
        if idx >= len(st.session_state.spelling_words):
            # 游戏结束，显示结果
            show_spelling_results()
            return
        
        current_word_data = st.session_state.spelling_progress[idx]
        current_word = current_word_data["word"]
        
        # 游戏界面
        # 精简游戏说明
        with st.expander("ℹ️ Game Instructions:英语拼写遵循发音规则，这个游戏帮你建立音和形对应关系。（查看具体步骤/规则可下拉)", expanded=False):
            st.markdown("""
            - 🎧 Listen to the word pronunciation 播放音频听单词的发音（建议跟着音频念出发音）
            - 🔤 Type letters you hear (press Enter) 根据发音输入单词拼写
            - ✅ Correct letters appear automatically 输入正确的字母会自动出现
            - ❌ Wrong letters are tracked below 输入错误的字母会有记录
            - ⚠️ Max 5 wrong attempts per word 每个单词最多5次错误
            - 💡 Hint after 3 wrong attempts 错3次会有提示
            """)
        
        # 音频播放（居中对齐）
        audio_file = generate_tts_audio(current_word)
        progress_col, audio_col = st.columns([1, 3])

        with progress_col:
            st.info(f"📝 Word {idx + 1} of {len(st.session_state.spelling_words)}")
        with audio_col:
            st.audio(audio_file, format="audio/mp3")
        
        # 显示单词空格（居中对齐，放大字号）
        display_letters = []
        for i, letter in enumerate(current_word):
            if current_word_data["revealed"][i]:
                # 用小写字母显示已揭示的字母
                display_letters.append(f'<span style="color: #2E86C1; font-weight: bold;">{letter}</span>')
            else:
                display_letters.append('<span style="color: #7B7D7D;">_</span>')
        
        # 使用HTML样式让单词居中并放大
        st.markdown(f"""
        <div style="text-align: center; margin: 20px 0 30px 0;">
            <h1 style="font-size: 42px; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                {' '.join(display_letters)}
            </h1>
        </div>
        """, unsafe_allow_html=True)
        
        # 显示已尝试的字母和错误字母列表（紧凑显示）
        if current_word_data["attempted_letters"] or current_word_data["wrong_letters"]:
            col1, col2 = st.columns(2)
            
            with col1:
                if current_word_data["attempted_letters"]:
                    attempted_display = []
                    for letter in sorted(current_word_data["attempted_letters"]):
                        if letter in current_word_data["wrong_letters"]:
                            attempted_display.append(f"❌{letter}")
                        else:
                            attempted_display.append(f"✅{letter}")
                    
                    st.markdown(f"**Attempted:** {' '.join(attempted_display)}")
            
            with col2:
                if current_word_data["wrong_letters"]:
                    wrong_list = [f"❌{letter}" for letter in sorted(current_word_data["wrong_letters"])]
                    st.markdown(f"**Wrong:** {' '.join(wrong_list)}")
        
        # 提示系统（错误3次后提供首字母提示）
        if current_word_data["wrong_count"] >= 3 and not current_word_data["hint_given"]:
            hint_col1, hint_col2 = st.columns([3, 1])
            with hint_col1:
                st.info(f"💡 **Hint:** The word starts with **'{current_word[0]}'**")
            with hint_col2:
                if st.button("More Hints", key=f"hint_btn_{idx}"):
                    # 找出最常用的元音字母提示
                    vowels_in_word = [l for l in current_word if l in 'aeiou']
                    if vowels_in_word:
                        st.info(f"💡 Contains vowels: {', '.join(vowels_in_word)}")
                    current_word_data["hint_given"] = True
        
        # 字母输入框和按钮在同一行
        st.markdown("---")
        
        # 使用一个标志来跟踪是否需要清空输入框
        if f"clear_input_{idx}" not in st.session_state:
            st.session_state[f"clear_input_{idx}"] = False
        
        # 创建表单用于Enter键提交
        with st.form(key=f"spelling_form_{idx}"):
            # 在同一行显示输入框和按钮
            input_col, btn_col = st.columns([4, 1])
            
            with input_col:
                # 如果设置了清空标志，使用空值
                input_value = "" if st.session_state.get(f"clear_input_{idx}", False) else ""
                user_input = st.text_input(
                    "Type letters and press Enter:",
                    value=input_value,
                    key=f"spelling_input_{idx}",
                    placeholder="Enter letters here...",
                    max_chars=10,
                    label_visibility="collapsed"
                ).lower()
            
            with btn_col:
                submitted = st.form_submit_button("🔤 Check", use_container_width=True)
            
            if submitted and user_input:
                # 直接处理用户输入（不调用外部函数）
                process_spelling_input_local(idx, user_input, current_word_data, current_word)
                # 设置清空标志
                st.session_state[f"clear_input_{idx}"] = True
                st.rerun()
        
        # 提交后重置清空标志
        if st.session_state.get(f"clear_input_{idx}", False):
            st.session_state[f"clear_input_{idx}"] = False
        
        # 进度条放在底部
        progress = current_word_data["wrong_count"] / 5
        st.progress(progress, text=f"Wrong attempts: {current_word_data['wrong_count']}/5")
        
        # 如果单词已完成或错误达到上限，显示相应信息
        if current_word_data["completed"]:
            st.success(f"🎉 Congratulations! You spelled **'{current_word}'** correctly!")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("➡️ Next Word", 
                            key=f"next_spelling_{idx}",
                            use_container_width=True):
                    st.session_state.spelling_index += 1
                    st.rerun()
        
        elif current_word_data["wrong_count"] >= 5:
            st.error(f"❌ Maximum attempts reached. The word was **'{current_word}'**")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("➡️ Skip to Next Word", 
                            key=f"skip_spelling_{idx}",
                            use_container_width=True):
                    st.session_state.spelling_index += 1
                    st.rerun()

def process_spelling_input_local(idx, user_input, word_data, word):
    """处理用户输入的字母（本地函数）"""
    # 过滤输入：只保留字母，转换为小写
    filtered_input = ''.join([c for c in user_input if c.isalpha()]).lower()
    
    if not filtered_input:
        return
    
    # 记录用户输入历史
    word_data["user_input_history"].append(filtered_input)
    
    correct_letters = []
    wrong_letters = []
    
    # 检查每个输入的字母
    for letter in filtered_input:
        # 如果这个字母之前已经尝试过，跳过
        if letter in word_data["attempted_letters"]:
            continue
        
        # 记录为已尝试
        word_data["attempted_letters"].add(letter)
        
        # 检查字母是否在单词中
        if letter in word:
            # 找到所有这个字母的位置并揭示
            for i, w_letter in enumerate(word):
                if w_letter == letter and not word_data["revealed"][i]:
                    word_data["revealed"][i] = True
            correct_letters.append(letter)
        else:
            # 错误的字母
            word_data["wrong_letters"].add(letter)
            wrong_letters.append(letter)
            word_data["wrong_count"] += 1
    
    # 检查是否完成单词
    if all(word_data["revealed"]):
        word_data["completed"] = True
        st.session_state.spelling_score += 1
    
    # 显示反馈
    if correct_letters:
        st.success(f"✅ Correct letters: {', '.join([l for l in correct_letters])}")
    
    if wrong_letters:
        st.error(f"❌ Wrong letters: {', '.join([l for l in wrong_letters])}")
        
        # 如果达到错误上限，提示
        if word_data["wrong_count"] >= 5:
            st.error("⚠️ You've reached the maximum wrong attempts!")

def show_spelling_results():
    """显示拼写游戏的结果"""
    st.balloons()
    total_words = len(st.session_state.spelling_words)
    score = st.session_state.spelling_score
    
    st.success(f"🎮 Game Finished! Your score: **{score}/{total_words}**")
    
    # 创建详细结果表格
    df_data = []
    for i, word_data in enumerate(st.session_state.spelling_progress):
        word = word_data["word"]
        completed = word_data["completed"]
        wrong_count = word_data["wrong_count"]
        attempted_count = len(word_data["attempted_letters"])
        
        df_data.append({
            "Word": word.upper(),
            "Status": "✅ Completed" if completed else "❌ Failed",
            "Wrong Attempts": wrong_count,
            "Letters Attempted": attempted_count,
            "Score": "1" if completed else "0"
        })
    
    df = pd.DataFrame(df_data)
    
    # 显示结果表格
    st.subheader("📊 Your Results")
    st.dataframe(
        df,
        column_config={
            "Word": "Word",
            "Status": "Result",
            "Wrong Attempts": st.column_config.NumberColumn(
                "Wrong Attempts",
                help="Number of wrong letter attempts"
            ),
            "Letters Attempted": st.column_config.NumberColumn(
                "Letters Tried",
                help="Total letters attempted"
            ),
            "Score": st.column_config.NumberColumn(
                "Points",
                help="1 point for correct, 0 for failed"
            )
        },
        hide_index=True,
        use_container_width=True
    )
    
    # 显示统计信息
    accuracy = (score / total_words) * 100
    avg_wrong = sum([d["wrong_count"] for d in st.session_state.spelling_progress]) / total_words
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Score", f"{score}/{total_words}")
    with col2:
        st.metric("Accuracy", f"{accuracy:.1f}%")
    with col3:
        st.metric("Avg Wrong Attempts", f"{avg_wrong:.1f}")
    
    # 性能评价
    st.markdown("---")
    if accuracy >= 80:
        performance = "🏆 Excellent Spelling Skills!"
    elif accuracy >= 60:
        performance = "👍 Good Job!"
    else:
        performance = "📚 Keep Practicing!"
    
    st.markdown(f"### {performance}")
    
    # 添加三个按钮（与其他游戏一致）
    st.markdown("---")
    st.write("### What would you like to do next?")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔄 Play Again", 
                    use_container_width=True,
                    help="Play the same game again with new random order"):
            reset_spelling_game()
            st.rerun()
    
    with col2:
        if st.button("🎮 Try Another Game", 
                    use_container_width=True,
                    help="Go back to choose a different game mode"):
            st.session_state.game_started = False
            st.rerun()
    
    with col3:
        if st.button("🏠 Main Menu", 
                    use_container_width=True,
                    help="Return to the main menu"):
            st.session_state.game_started = False
            st.session_state.game_mode = None
            # 清理拼写游戏状态
            for key in ["spelling_index", "spelling_score", "spelling_words", "spelling_progress"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

def reset_spelling_game():
    """重置拼写游戏状态"""
    st.session_state.spelling_index = 0
    st.session_state.spelling_score = 0
    st.session_state.spelling_words = []
    st.session_state.spelling_progress = []
                                
# ------------------- 3. Matching Game (优化版) -------------------
def prepare_matching_game():
    """初始化匹配游戏数据"""
    if st.session_state.get("game_started", False) and st.session_state.get("game_mode") == "Matching Game":
        if not st.session_state.get("matching_words_generated", False):
            # 生成英文和中文列表
            word_en = st.session_state.user_words.copy()
            word_cn = []
            mapping = {}
            
            # 翻译所有单词
            st.info("⏳ Translating words...")
            progress_bar = st.progress(0)
            
            for i, w in enumerate(word_en):
                if w in st.session_state.translation_cache:
                    cn = st.session_state.translation_cache[w]
                else:
                    cn = baidu_translate(w)
                    st.session_state.translation_cache[w] = cn
                word_cn.append(cn)
                mapping[w] = cn
                progress_bar.progress((i + 1) / len(word_en))
            
            progress_bar.empty()
            
            # 打乱顺序
            en_shuffled = word_en.copy()
            cn_shuffled = word_cn.copy()
            random.shuffle(en_shuffled)
            random.shuffle(cn_shuffled)
            
            # 存储到 session_state
            st.session_state.matching_en_list = en_shuffled
            st.session_state.matching_cn_list = cn_shuffled
            st.session_state.matching_mapping = mapping
            st.session_state.matching_current_index = 0
            st.session_state.matching_score = 0
            st.session_state.matching_answers = [None] * len(word_en)
            st.session_state.matching_submitted = False
            st.session_state.matching_finished = False
            st.session_state.matching_words_generated = True
            st.session_state.matching_waiting_for_next = False

def play_matching_game():
    """玩匹配游戏 - 优化版界面"""
    prepare_matching_game()
    
    if not st.session_state.get("matching_words_generated", False):
        return
    
    st.subheader("🔤 Matching Game - Match English with Chinese")
    
    # 游戏说明
    with st.expander("ℹ️ Game Instructions", expanded=False):
        st.markdown("""
        - 📖 Match each English word with its correct Chinese translation
        - 🔄 English words are in a fixed order on the left
        - 🔀 Chinese translations are shuffled on the right
        - ✅ Select one Chinese meaning for each English word
        """)
    
    # 获取当前状态
    idx = st.session_state.matching_current_index
    en_list = st.session_state.matching_en_list
    cn_list = st.session_state.matching_cn_list
    mapping = st.session_state.matching_mapping
    total_words = len(en_list)
    
    # 如果游戏未完成，显示当前题目
    if not st.session_state.get("matching_finished", False):
        # 当前英文单词
        current_en_word = en_list[idx]
        
        st.markdown(f"""
        <div style="text-align: center; margin: 20px 0 30px 0;">
            <h2 style="font-size: 32px; color: #2E86C1; font-weight: bold;">
                {current_en_word}
            </h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Select the correct Chinese meaning:")
        
        # 显示所有中文选项（分为两列）
        cols = st.columns(2)
        selected_cn = st.session_state.matching_answers[idx]
        
        # 将中文选项分配到两列
        for i, cn_word in enumerate(cn_list):
            col_idx = i % 2
            with cols[col_idx]:
                is_selected = selected_cn == cn_word
                button_type = "primary" if is_selected else "secondary"
                
                if st.button(
                    cn_word,
                    key=f"match_cn_{idx}_{i}",
                    use_container_width=True,
                    type=button_type
                ):
                    st.session_state.matching_answers[idx] = cn_word
                    st.rerun()
        
        # 显示当前选择
        if selected_cn:
            st.markdown(f"**Your current selection:** `{selected_cn}`")
        
        # 提交按钮和导航按钮
        col1, col2 = st.columns(2)
        
        with col1:
            # 检查是否可以提交当前答案
            submit_disabled = st.session_state.matching_answers[idx] is None
            
            if st.button("✅ Submit Answer", 
                        key=f"match_submit_{idx}", 
                        disabled=submit_disabled,
                        use_container_width=True):
                # 保存当前答案
                user_choice = st.session_state.matching_answers[idx]
                correct_cn = mapping.get(current_en_word, "")
                
                # 立即反馈
                if user_choice == correct_cn:
                    st.success(f"✅ Correct! **'{current_en_word}'** means **'{correct_cn}'**")
                else:
                    st.error(f"❌ Wrong. **'{current_en_word}'** means **'{correct_cn}'**, not **'{user_choice}'**")
                
                # 等待下一题
                st.session_state.matching_waiting_for_next = True
        
        # 如果等待下一题，显示Next按钮
        if st.session_state.get("matching_waiting_for_next", False):
            with col2:
                if st.button("➡️ Next Word", 
                            key=f"match_next_{idx}", 
                            use_container_width=True):
                    # 移动到下一题
                    if idx < total_words - 1:
                        st.session_state.matching_current_index += 1
                    else:
                        # 最后一题完成，计算总分
                        calculate_matching_score()
                        st.session_state.matching_finished = True
                    
                    st.session_state.matching_waiting_for_next = False
                    st.rerun()
        
        # 进度条
        progress = (idx + 1) / total_words
        st.progress(progress, text=f"Progress: {idx + 1}/{total_words}")
        
        # 显示快速跳转按钮（可选）
        if total_words > 5:
            st.markdown("---")
            st.write("**Quick Navigation:**")
            
            # 创建一行按钮，每行最多5个
            max_buttons_per_row = 5
            for start in range(0, total_words, max_buttons_per_row):
                end = min(start + max_buttons_per_row, total_words)
                cols = st.columns(end - start)
                
                for i in range(start, end):
                    col_idx = i - start
                    with cols[col_idx]:
                        button_text = f"🔤 {i+1}"
                        button_type = "primary" if i == idx else "secondary"
                        
                        if st.button(
                            button_text,
                            key=f"nav_{i}",
                            use_container_width=True,
                            type=button_type
                        ):
                            st.session_state.matching_current_index = i
                            st.session_state.matching_waiting_for_next = False
                            st.rerun()
    
    else:
        # 游戏完成，显示结果
        show_matching_results()

def calculate_matching_score():
    """计算匹配游戏总分"""
    en_list = st.session_state.matching_en_list
    mapping = st.session_state.matching_mapping
    answers = st.session_state.matching_answers
    
    score = 0
    for i, en_word in enumerate(en_list):
        correct_cn = mapping.get(en_word, "")
        user_answer = answers[i]
        if user_answer == correct_cn:
            score += 1
    
    st.session_state.matching_score = score

def show_matching_results():
    """显示匹配游戏结果"""
    st.balloons()
    
    en_list = st.session_state.matching_en_list
    cn_list = st.session_state.matching_cn_list
    mapping = st.session_state.matching_mapping
    answers = st.session_state.matching_answers
    score = st.session_state.matching_score
    total = len(en_list)
    
    st.success(f"🎮 Game Finished! Your score: **{score}/{total}**")
    
    # 创建结果表格
    df_data = []
    for i, en_word in enumerate(en_list):
        correct_cn = mapping.get(en_word, "")
        user_answer = answers[i] if answers[i] else "(No answer)"
        is_correct = user_answer == correct_cn
        
        df_data.append({
            "English Word": en_word,
            "Correct Chinese": correct_cn,
            "Your Answer": user_answer,
            "Result": "✅" if is_correct else "❌"
        })
    
    df = pd.DataFrame(df_data)
    
    # 显示结果表格
    st.subheader("📊 Your Results")
    st.dataframe(
        df,
        column_config={
            "English Word": st.column_config.TextColumn(
                "English",
                width="medium"
            ),
            "Correct Chinese": st.column_config.TextColumn(
                "Correct Meaning",
                width="medium"
            ),
            "Your Answer": st.column_config.TextColumn(
                "Your Choice",
                width="medium"
            ),
            "Result": st.column_config.TextColumn(
                "Result",
                help="✅ = Correct, ❌ = Wrong"
            )
        },
        hide_index=True,
        use_container_width=True
    )
    
    # 显示统计信息
    accuracy = (score / total) * 100
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Score", f"{score}/{total}")
    with col2:
        st.metric("Accuracy", f"{accuracy:.1f}%")
    with col3:
        if accuracy >= 90:
            performance = "🏆 Excellent"
        elif accuracy >= 75:
            performance = "👍 Great"
        elif accuracy >= 60:
            performance = "👌 Good"
        else:
            performance = "📚 Needs Practice"
        st.metric("Performance", performance)
    
    # 显示正确答案的翻译参考
    with st.expander("📚 All Word Translations", expanded=False):
        trans_data = []
        for en_word, cn_meaning in mapping.items():
            trans_data.append({
                "English": en_word,
                "Chinese": cn_meaning
            })
        
        trans_df = pd.DataFrame(trans_data)
        st.table(trans_df)
    
    # 添加操作按钮（与其他游戏一致）
    st.markdown("---")
    st.write("### What would you like to do next?")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔄 Play Again", 
                    use_container_width=True,
                    help="Play the same game again with new random order"):
            reset_matching_game()
            st.rerun()
    
    with col2:
        if st.button("🎮 Try Another Game", 
                    use_container_width=True,
                    help="Go back to choose a different game mode"):
            st.session_state.game_started = False
            reset_matching_game()
            st.rerun()
    
    with col3:
        if st.button("🏠 Main Menu", 
                    use_container_width=True,
                    help="Return to the main menu"):
            st.session_state.game_started = False
            st.session_state.game_mode = None
            reset_matching_game(clear_all=True)
            st.rerun()

def reset_matching_game(clear_all=False):
    """重置匹配游戏状态"""
    keys_to_reset = [
        "matching_en_list", "matching_cn_list", "matching_mapping",
        "matching_current_index", "matching_score", "matching_answers",
        "matching_submitted", "matching_finished", "matching_words_generated",
        "matching_waiting_for_next"
    ]
    
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    
    # 清除所有选择状态
    for key in list(st.session_state.keys()):
        if key.startswith("match_"):
            del st.session_state[key]
    
    # 如果清除所有，也清除翻译缓存
    if clear_all and "translation_cache" in st.session_state:
        del st.session_state["translation_cache"]
        
# ------------------- Merriam-Webster API -------------------
MW_API_KEY = "b03334be-a55f-4416-9ff4-782b15a4dc77"  

def clean_html_tags(text):
    """Clean HTML-like tags from Merriam-Webster API response"""
    import re
    # 移除 {wi}...{/wi} 标签
    text = re.sub(r'\{/?wi\}', '', text)
    # 移除 {it}...{/it} 标签
    text = re.sub(r'\{/?it\}', '', text)
    # 移除其他常见标签
    text = re.sub(r'\{/?[^}]+?\}', '', text)
    # 清理多余的空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# 替换 play_fill_blank_game() 函数中的部分代码

def get_example_sentence_mw(word):
    """
    Get example sentence from Merriam-Webster Collegiate API.
    Fallback to a template if no sentence is found.
    """
    url = f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={MW_API_KEY}"
    try:
        r = requests.get(url)
        data = r.json()
        if not data or not isinstance(data[0], dict):
            # 使用标志性字符串，便于后续识别
            return f"[DEFAULT] Please use the word: {word}"
        defs = data[0].get("def", [])
        for d in defs:
            sseq = d.get("sseq", [])
            for sense_group in sseq:
                for sense in sense_group:
                    dt = sense[1].get("dt", [])
                    for item in dt:
                        if item[0] == "vis":  # example sentences
                            vis_list = item[1]
                            if vis_list:
                                raw_sentence = vis_list[0]["t"]
                                # 清理HTML标签
                                cleaned_sentence = clean_html_tags(raw_sentence)
                                return cleaned_sentence
        # 如果没有找到例句，返回标志性默认句子
        return f"[DEFAULT] Please use the word: {word}"
    except Exception as e:
        print(f"Error getting example sentence for {word}: {e}")
        return f"[DEFAULT] Please use the word: {word}"

def create_blank_sentence(word, sentence):
    """Replace the target word with blanks in the sentence, handling variations"""
    import re
    
    # 确保句子已经清理过HTML标签
    cleaned_sentence = clean_html_tags(sentence)
    
    # 检查是否为默认句子
    if "[DEFAULT]" in cleaned_sentence:
        # 从默认句子中提取单词
        match = re.search(r':\s*(\w+)', cleaned_sentence)
        if match:
            target_word = match.group(1)
            return cleaned_sentence.replace(target_word, "_____")
        return cleaned_sentence
    
    # 定义单词的词形变化模式
    word_lower = word.lower()
    
    # 生成可能的词形变化
    def generate_variants(base_word):
        variants = []
        base_lower = base_word.lower()
        
        # 基本形式
        variants.append(base_word)
        
        # 复数形式
        if base_lower.endswith('y'):
            variants.append(base_word[:-1] + 'ies')
            variants.append(base_word[:-1] + 'ied')
        elif base_lower.endswith(('s', 'x', 'z', 'ch', 'sh')):
            variants.append(base_word + 'es')
        else:
            variants.append(base_word + 's')
            variants.append(base_word + 'es')
        
        # 过去式和过去分词
        if base_lower.endswith('e'):
            variants.append(base_word + 'd')
        else:
            variants.append(base_word + 'ed')
        
        # 进行时
        if base_lower.endswith('e'):
            variants.append(base_word[:-1] + 'ing')
        else:
            variants.append(base_word + 'ing')
        
        # 第三人称单数
        if base_lower.endswith(('s', 'x', 'z', 'ch', 'sh')):
            variants.append(base_word + 'es')
        elif base_lower.endswith('y'):
            variants.append(base_word[:-1] + 'ies')
        else:
            variants.append(base_word + 's')
        
        # 不规则变化（常见动词）
        irregular_map = {
            'go': ['went', 'gone', 'goes', 'going'],
            'be': ['am', 'is', 'are', 'was', 'were', 'been', 'being'],
            'have': ['has', 'had', 'having'],
            'do': ['does', 'did', 'done', 'doing'],
            'say': ['says', 'said', 'saying'],
            'get': ['gets', 'got', 'gotten', 'getting'],
            'make': ['makes', 'made', 'making'],
            'know': ['knows', 'knew', 'known', 'knowing'],
            'think': ['thinks', 'thought', 'thinking'],
            'take': ['takes', 'took', 'taken', 'taking'],
            'see': ['sees', 'saw', 'seen', 'seeing'],
            'come': ['comes', 'came', 'coming'],
            'want': ['wants', 'wanted', 'wanting'],
            'look': ['looks', 'looked', 'looking'],
            'use': ['uses', 'used', 'using'],
            'find': ['finds', 'found', 'finding'],
            'give': ['gives', 'gave', 'given', 'giving'],
            'tell': ['tells', 'told', 'telling'],
            'work': ['works', 'worked', 'working'],
            'call': ['calls', 'called', 'calling'],
            'try': ['tries', 'tried', 'trying'],
            'ask': ['asks', 'asked', 'asking'],
            'need': ['needs', 'needed', 'needing'],
            'feel': ['feels', 'felt', 'feeling'],
            'become': ['becomes', 'became', 'becoming'],
            'leave': ['leaves', 'left', 'leaving'],
            'put': ['puts', 'put', 'putting'],
            'mean': ['means', 'meant', 'meaning'],
            'keep': ['keeps', 'kept', 'keeping'],
            'let': ['lets', 'let', 'letting'],
            'begin': ['begins', 'began', 'begun', 'beginning'],
            'seem': ['seems', 'seemed', 'seeming'],
            'help': ['helps', 'helped', 'helping'],
            'talk': ['talks', 'talked', 'talking'],
            'turn': ['turns', 'turned', 'turning'],
            'start': ['starts', 'started', 'starting'],
            'show': ['shows', 'showed', 'shown', 'showing'],
            'hear': ['hears', 'heard', 'hearing'],
            'play': ['plays', 'played', 'playing'],
            'run': ['runs', 'ran', 'running'],
            'move': ['moves', 'moved', 'moving'],
            'like': ['likes', 'liked', 'liking'],
            'live': ['lives', 'lived', 'living'],
            'believe': ['believes', 'believed', 'believing'],
            'hold': ['holds', 'held', 'holding'],
            'bring': ['brings', 'brought', 'bringing'],
            'happen': ['happens', 'happened', 'happening'],
            'write': ['writes', 'wrote', 'written', 'writing'],
            'provide': ['provides', 'provided', 'providing'],
            'sit': ['sits', 'sat', 'sitting'],
            'stand': ['stands', 'stood', 'standing'],
            'lose': ['loses', 'lost', 'losing'],
            'pay': ['pays', 'paid', 'paying'],
            'meet': ['meets', 'met', 'meeting'],
            'include': ['includes', 'included', 'including'],
            'continue': ['continues', 'continued', 'continuing'],
            'set': ['sets', 'set', 'setting'],
            'learn': ['learns', 'learned', 'learnt', 'learning'],
            'lead': ['leads', 'led', 'leading'],
            'understand': ['understands', 'understood', 'understanding'],
            'watch': ['watches', 'watched', 'watching'],
            'follow': ['follows', 'followed', 'following'],
            'stop': ['stops', 'stopped', 'stopping'],
            'create': ['creates', 'created', 'creating'],
            'speak': ['speaks', 'spoke', 'spoken', 'speaking'],
            'read': ['reads', 'read', 'reading'],
            'allow': ['allows', 'allowed', 'allowing'],
            'add': ['adds', 'added', 'adding'],
            'spend': ['spends', 'spent', 'spending'],
            'grow': ['grows', 'grew', 'grown', 'growing'],
            'open': ['opens', 'opened', 'opening'],
            'walk': ['walks', 'walked', 'walking'],
            'win': ['wins', 'won', 'winning'],
            'offer': ['offers', 'offered', 'offering'],
            'remember': ['remembers', 'remembered', 'remembering'],
            'love': ['loves', 'loved', 'loving'],
            'consider': ['considers', 'considered', 'considering'],
            'appear': ['appears', 'appeared', 'appearing'],
            'buy': ['buys', 'bought', 'buying'],
            'wait': ['waits', 'waited', 'waiting'],
            'serve': ['serves', 'served', 'serving'],
            'die': ['dies', 'died', 'dying'],
            'send': ['sends', 'sent', 'sending'],
            'expect': ['expects', 'expected', 'expecting'],
            'build': ['builds', 'built', 'building'],
            'stay': ['stays', 'stayed', 'staying'],
            'fall': ['falls', 'fell', 'fallen', 'falling'],
            'cut': ['cuts', 'cut', 'cutting'],
            'reach': ['reaches', 'reached', 'reaching'],
            'kill': ['kills', 'killed', 'killing'],
            'raise': ['raises', 'raised', 'raising'],
            'pass': ['passes', 'passed', 'passing'],
            'sell': ['sells', 'sold', 'selling'],
            'require': ['requires', 'required', 'requiring'],
        }
        
        if base_lower in irregular_map:
            variants.extend(irregular_map[base_lower])
        
        return list(set(variants))  # 去重
    
    # 生成所有可能的变体
    all_variants = generate_variants(word)
    
    # 按长度排序，优先匹配较长的变体（避免部分匹配）
    all_variants.sort(key=len, reverse=True)
    
    # 尝试匹配每个变体
    for variant in all_variants:
        # 使用正则表达式确保匹配整个单词
        pattern = re.compile(rf'\b{re.escape(variant)}\b', re.IGNORECASE)
        match = pattern.search(cleaned_sentence)
        if match:
            # 找到实际出现在句子中的形式（保持原有大小写）
            actual_word = cleaned_sentence[match.start():match.end()]
            return cleaned_sentence.replace(actual_word, "_____")
    
    # 如果以上都没匹配到，尝试更宽松的匹配
    # 查找包含原始单词的单词（如 collaborated 包含 collaborate）
    pattern_partial = re.compile(rf'\b\w*{re.escape(word_lower)}\w*\b', re.IGNORECASE)
    matches = pattern_partial.findall(cleaned_sentence)
    
    for match in matches:
        # 使用正则表达式确保匹配整个单词
        pattern_full = re.compile(rf'\b{re.escape(match)}\b', re.IGNORECASE)
        full_match = pattern_full.search(cleaned_sentence)
        if full_match:
            actual_word = cleaned_sentence[full_match.start():full_match.end()]
            return cleaned_sentence.replace(actual_word, "_____")
    
    # 如果还是没有匹配到，返回带提示的句子
    return f"{cleaned_sentence} (Fill in: _____)"

def play_fill_blank_game():
    # ______ Fill-in-the-Blank Game (改进版) ______
    if st.session_state.get("game_started", False) and st.session_state.get("game_mode") == "Fill-in-the-Blank Game":
        st.subheader("📝 Fill-in-the-Blank Game")
        
        with st.expander("ℹ️ Game Instructions", expanded=False):
            st.markdown("""
            1. 📖 Read the sentence with a blank 阅读带有空白的句子
            2. 🔍 Choose the correct word to fill the blank based on context 根据上下文选择正确的单词填入空白
            3. ✅ Submit your answer to view the original sentence and explanation 提交答案，查看原句和解释
            4. ➡️ Check your score after completing all questions 完成所有题目后查看成绩
            5. Important Notes: Some questions use real dictionary examples (scored), and some questions use default sentences (not scored) 部分题目使用词典真实例句（计分）,部分题目使用默认句子（不计分）
            6. Only real examples count towards your final score 只有真实例句会计入最终分数
            """)
            
        # 初始化游戏状态
        if "fb_index" not in st.session_state:
            st.session_state.fb_index = 0
            st.session_state.fb_score = 0
            st.session_state.fb_total_questions = 0  # 只计算非fallback的题目数量
            st.session_state.fb_answers = [""] * 10
            st.session_state.fb_correct_answers = []
            st.session_state.fb_blanked_sentences = []
            st.session_state.fb_original_sentences = []
            st.session_state.fb_is_fallback = []  # 记录是否为fallback句子
            st.session_state.fb_played_order = []  # 存储打乱的问题顺序
            st.session_state.fb_waiting_for_next = False
        
        # 获取当前索引和单词列表
        idx = st.session_state.fb_index
        user_words = st.session_state.fill_blank_words  # 使用专门为填空游戏准备的单词列表
        
        # 如果是第一题，初始化游戏数据
        if idx == 0 and len(st.session_state.fb_correct_answers) == 0:
            # 1. 存储正确答案（原始单词列表）
            st.session_state.fb_correct_answers = user_words.copy()
            
            # 2. 为每个单词获取例句并创建填空句子
            st.session_state.fb_blanked_sentences = []
            st.session_state.fb_original_sentences = []
            st.session_state.fb_is_fallback = []  # 初始化fallback记录
            st.session_state.fb_total_questions = 0  # 重置非fallback题目计数
            
            st.info("⏳ Generating example sentences...")
            progress_bar = st.progress(0)
            
            for i, word in enumerate(user_words):
                # 获取例句
                sentence = get_example_sentence_mw(word)
                st.session_state.fb_original_sentences.append(sentence)
                
                # 检查是否为fallback句子
                is_fallback = "[DEFAULT]" in sentence
                st.session_state.fb_is_fallback.append(is_fallback)
                
                # 创建填空句子
                if not is_fallback:
                    blanked_sentence = create_blank_sentence(word, sentence)
                    # 检查是否成功挖空
                    if "_____" in blanked_sentence:
                        st.session_state.fb_blanked_sentences.append(blanked_sentence)
                        st.session_state.fb_total_questions += 1
                    else:
                        # 如果挖空失败，标记为fallback
                        st.session_state.fb_is_fallback[-1] = True
                        st.session_state.fb_blanked_sentences.append(sentence + " (Fill in: _____)")
                else:
                    # 对于fallback句子，直接显示填空提示
                    st.session_state.fb_blanked_sentences.append(sentence.replace(word, "_____"))
                
                # 更新进度条
                progress_bar.progress((i + 1) / len(user_words))
            
            progress_bar.empty()
            
            # 3. 创建打乱的问题顺序（只打乱实际会展示的顺序）
            # 注意：所有10个问题都会展示，但只有非fallback的会计分
            shuffled_order = list(range(len(user_words)))
            random.shuffle(shuffled_order)
            st.session_state.fb_played_order = shuffled_order
        
        # 检查游戏是否结束
        if idx < len(user_words):
            # 获取当前题目信息
            current_order = st.session_state.fb_played_order[idx]  # 当前问题的索引（打乱顺序）
            current_sentence = st.session_state.fb_blanked_sentences[current_order]
            correct_word = st.session_state.fb_correct_answers[current_order]
            original_sentence = st.session_state.fb_original_sentences[current_order]
            is_fallback = st.session_state.fb_is_fallback[current_order]
            
            # 显示是否为fallback句子
            if is_fallback:
                st.info(f"📝 Question {idx + 1} of {len(user_words)} (⚪ Practice Sentence - Not Counted)")
            else:
                st.info(f"📝 Question {idx + 1} of {len(user_words)} (🎯 Scored)")
            
            # 显示填空句子
            st.markdown(f"### {current_sentence}")
            
            # 显示所有10个单词作为选项（保持原始顺序）
            st.write("**Select the correct word to fill in the blank:**")
            
            # 创建两列布局显示10个选项
            cols = st.columns(2)
            
            # 将10个单词分配到两列
            for i, word in enumerate(user_words):
                col_idx = i % 2
                with cols[col_idx]:
                    is_selected = st.session_state.get(f"fb_selected_{idx}") == word
                    button_type = "primary" if is_selected else "secondary"
                    
                    if st.button(
                        word,
                        key=f"fb_word_btn_{idx}_{i}",
                        use_container_width=True,
                        type=button_type
                    ):
                        st.session_state[f"fb_selected_{idx}"] = word
                        st.rerun()
            
            # 显示当前选择的单词
            if st.session_state.get(f"fb_selected_{idx}"):
                st.markdown(f"**Your current selection:** `{st.session_state[f'fb_selected_{idx}']}`")
            
            # 提交按钮
            col1, col2 = st.columns(2)
            submit_disabled = st.session_state.get(f"fb_selected_{idx}") is None
            
            with col1:
                if st.button("✅ Submit Answer", 
                            key=f"fb_submit_{idx}", 
                            disabled=submit_disabled,
                            use_container_width=True):
                    user_choice = st.session_state.get(f"fb_selected_{idx}", "")
                    
                    # 保存答案
                    st.session_state.fb_answers[current_order] = user_choice
                    
                    # 显示原始句子
                    with st.expander("📖 Show original sentence"):
                        st.write(f"**Original sentence:** {original_sentence}")
                        if is_fallback:
                            st.warning("⚪ This is a practice sentence - not counted in final score")
                    
                    # 检查答案（只有非fallback句子才计分）
                    if not is_fallback:
                        # 计分题目的答案检查
                        if user_choice.lower() == correct_word.lower():
                            st.session_state.fb_score += 1
                            st.success(f"✅ Correct! **'{correct_word}'** fits perfectly! (+1 point)")
                        else:
                            st.error(f"❌ Wrong. You selected **'{user_choice}'**. The correct answer was **'{correct_word}'**.")
                    else:
                        # 练习句子只给反馈，不计分
                        if user_choice.lower() == correct_word.lower():
                            st.success(f"✅ Good! **'{correct_word}'** is correct! (Practice sentence)")
                        else:
                            st.error(f"❌ Try again. You selected **'{user_choice}'**. The correct answer was **'{correct_word}'**. (Practice sentence)")
                    
                    # 清除当前选择
                    if f"fb_selected_{idx}" in st.session_state:
                        del st.session_state[f"fb_selected_{idx}"]
                    
                    # 显示下一题按钮
                    st.session_state.fb_waiting_for_next = True
            
            # 下一题按钮
            if st.session_state.get("fb_waiting_for_next", False):
                with col2:
                    if st.button("➡️ Next Question", 
                                key=f"fb_next_{idx}", 
                                use_container_width=True):
                        st.session_state.fb_index += 1
                        st.session_state.fb_waiting_for_next = False
                        st.rerun()
        else:
            # 游戏结束：显示结果
            st.balloons()
            
            # 计算有效题目（非fallback）的数量
            valid_questions = st.session_state.fb_total_questions
            
            if valid_questions > 0:
                accuracy = (st.session_state.fb_score / valid_questions) * 100
                st.success(f"🎮 Game Finished! Your score: **{st.session_state.fb_score}/{valid_questions}**")
                st.info(f"📊 Accuracy: {accuracy:.1f}%")
            else:
                st.success(f"🎮 Game Finished! All sentences were practice sentences.")
            
            # 创建结果表格
            df_data = []
            for i in range(len(user_words)):
                original_idx = st.session_state.fb_played_order[i]
                blanked_sentence = st.session_state.fb_blanked_sentences[original_idx]
                user_answer = st.session_state.fb_answers[original_idx]
                correct_answer = st.session_state.fb_correct_answers[original_idx]
                original_sentence = st.session_state.fb_original_sentences[original_idx]
                is_fallback = st.session_state.fb_is_fallback[original_idx]
                
                # 检查是否答对
                if not is_fallback:
                    is_correct = user_answer.lower() == correct_answer.lower() if user_answer else False
                    result = "✅ Correct" if is_correct else "❌ Wrong"
                    scored = "Yes"
                else:
                    if user_answer:
                        is_practice_correct = user_answer.lower() == correct_answer.lower()
                        result = "✅ Practice" if is_practice_correct else "❌ Practice"
                    else:
                        result = "⚪ Not answered"
                    scored = "No"
                
                df_data.append({
                    "Sentence": blanked_sentence,
                    "Correct Answer": correct_answer,
                    "Your Answer": user_answer if user_answer else "(No answer)",
                    "Result": result,
                    "Scored?": scored
                })
            
            # 显示表格
            st.subheader("📊 Your Results")
            
            df = pd.DataFrame(df_data)
            st.dataframe(
                df,
                column_config={
                    "Sentence": st.column_config.TextColumn("Fill-in Sentence", width="large"),
                    "Correct Answer": "Correct Word",
                    "Your Answer": "Your Choice",
                    "Result": st.column_config.TextColumn("Result"),
                    "Scored?": st.column_config.TextColumn("Counted in Score?")
                },
                hide_index=True,
                use_container_width=True
            )
            
            # 显示详细统计
            fallback_count = sum(st.session_state.fb_is_fallback)
            answered_count = sum(1 for ans in st.session_state.fb_answers if ans)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Questions", len(user_words))
            with col2:
                st.metric("Scored Questions", valid_questions)
            with col3:
                st.metric("Practice Sentences", fallback_count)
            
            # 性能评价（仅针对计分题目）
            if valid_questions > 0:
                if accuracy >= 90:
                    performance = "🏆 Outstanding!"
                elif accuracy >= 75:
                    performance = "👍 Excellent!"
                elif accuracy >= 60:
                    performance = "👌 Good Job"
                else:
                    performance = "📚 Keep Practicing"
                
                st.markdown(f"### {performance}")
            
            # 添加操作按钮
            st.markdown("---")
            st.write("### What would you like to do next?")
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("🔄 Play Again", use_container_width=True):
                    reset_fill_blank_game()
                    st.rerun()
            
            with col2:
                if st.button("🎮 Try Another Game", use_container_width=True):
                    st.session_state.game_started = False
                    reset_fill_blank_game()
                    st.rerun()
            
            with col3:
                if st.button("🏠 Main Menu", use_container_width=True):
                    st.session_state.game_started = False
                    st.session_state.game_mode = None
                    reset_fill_blank_game(clear_all=True)
                    st.rerun()

def reset_fill_blank_game(clear_all=False):
    """重置填空游戏状态"""
    keys_to_reset = [
        "fb_index", "fb_score", "fb_total_questions", "fb_answers",
        "fb_correct_answers", "fb_blanked_sentences", "fb_original_sentences",
        "fb_is_fallback", "fb_played_order", "fb_waiting_for_next"
    ]
    
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    
    # 清除所有选择状态
    for key in list(st.session_state.keys()):
        if key.startswith("fb_selected_"):
            del st.session_state[key]
    
    # 如果清除所有，也清除翻译缓存
    if clear_all and "translation_cache" in st.session_state:
        del st.session_state["translation_cache"]
        
                                
# ------------------- session_state defaults -------------------
if "user_words" not in st.session_state:
    st.session_state.user_words = []
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "game_mode" not in st.session_state:
    st.session_state.game_mode = None

# Scrambled Game state
if "scramble_index" not in st.session_state:
    st.session_state.scramble_index = 0
if "scramble_score" not in st.session_state:
    st.session_state.scramble_score = 0
if "scramble_answers" not in st.session_state:
    st.session_state.scramble_answers = [""] * 10
if "scramble_scrambled" not in st.session_state:
    st.session_state.scramble_scrambled = [""] * 10

# translation cache
if "translation_cache" not in st.session_state:
    st.session_state.translation_cache = {}
    
# ------------------- Matching Game -------------------
if st.session_state.game_started and st.session_state.game_mode == "Matching Game":
    play_matching_game()    
        
# ------------------- Fill-in-the-Blank  -------------------
if st.session_state.game_started and st.session_state.game_mode == "Fill-in-the-Blank Game":
    play_fill_blank_game()
    
# =================== 新增：Spelling Game调用 ===================
if st.session_state.get("game_started", False) and st.session_state.get("game_mode") == "Spelling Game":
    play_spelling_game()
