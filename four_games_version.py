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
''' initialize four games'''

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
if st.session_state.user_words and len(st.session_state.user_words) == 10:
    st.markdown("### 2. Choose a game and start")
    st.session_state.game_mode = st.selectbox(
        "Choose game mode",
        ["Listen & Choose", "Spelling Game", "Matching Game",  "Fill-in-the-Blank Game"],
        index=0
    )
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
        with st.expander("ℹ️ Game Instructions", expanded=False):
            st.markdown("""
            - 🎧 Listen to the word pronunciation
            - 🔤 Type letters you hear (press Enter)
            - ✅ Correct letters appear automatically
            - ❌ Wrong letters are tracked below
            - ⚠️ Max 5 wrong attempts per word
            - 💡 Hint after 3 wrong attempts
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
                                
# ------------------- 3. Matching Game helpers -------------------
def generate_matching_game_once(user_words):
    """
    Generate (and translate) only once. Returns en_shuffled, cn_shuffled, mapping.
    This function DOES NOT change session_state; caller should store results.
    """
    word_en = []
    word_cn = []
    mapping = {}
    for w in user_words:
        # use cached translations if available (session_state)
        if "translation_cache" in st.session_state and w in st.session_state.translation_cache:
            cn = st.session_state.translation_cache[w]
        else:
            cn = baidu_translate(w)
            # cache it locally
            if "translation_cache" not in st.session_state:
                st.session_state.translation_cache = {}
            st.session_state.translation_cache[w] = cn
        word_en.append(w)
        word_cn.append(cn)
        mapping[w] = cn
    en_shuffled = word_en[:]
    cn_shuffled = word_cn[:]
    random.shuffle(en_shuffled)
    random.shuffle(cn_shuffled)
    return en_shuffled, cn_shuffled, mapping

def prepare_matching_game():
    """Ensure matching game data exists in session_state (generate once per Start Game)."""
    if st.session_state.get("game_started", False) and st.session_state.get("game_mode") == "Matching Game":
        if not st.session_state.get("matching_words_generated", False):
            en_list, cn_list, mapping = generate_matching_game_once(st.session_state.user_words)
            st.session_state.en_list = en_list
            st.session_state.cn_list = cn_list
            st.session_state.mapping = mapping
            st.session_state.matching_answers = {w: "Select" for w in en_list}
            st.session_state.matching_words_generated = True

def play_matching_game():
    prepare_matching_game()
    en_list = st.session_state.en_list
    cn_list = st.session_state.cn_list
    mapping = st.session_state.mapping

    st.subheader("Match English words with their Chinese meaning")

    # Build selectboxes — keys must be stable
    for en_word in en_list:
        current_choice = st.session_state.matching_answers.get(en_word, "Select")
        # 不使用 on_change 或 rerun
        sel = st.selectbox(
            f"{en_word} ->",
            options=["Select"] + cn_list,
            index=(0 if current_choice not in (["Select"] + cn_list) else (["Select"] + cn_list).index(current_choice)),
            key=f"matching_{en_word}"
        )
        # 保存选择状态到 session_state
        st.session_state.matching_answers[en_word] = sel

    st.markdown("---")
    if st.button("✅ Submit Matching Game"):
        score = 0
        for w in en_list:
            if st.session_state.matching_answers.get(w) == mapping.get(w):
                score += 1
        st.success(f"You scored: {score}/{len(en_list)}")
        st.session_state.matching_score = score

        df = pd.DataFrame({
            "Word": en_list,
            "Correct Meaning": [mapping[w] for w in en_list],
            "Your Answer": [st.session_state.matching_answers[w] for w in en_list],
            "Correct?": [st.session_state.matching_answers[w] == mapping[w] for w in en_list]
        })
        st.subheader("Your results")
        st.table(df)

        # 游戏结束，允许用户选择下一步
        st.session_state.game_started = False
        st.session_state.matching_words_generated = False

        
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
            # 使用清理后的默认句子
            return f"DEFAULT SENTECT: I LIKE TO {word} EVERY DAY."
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
        # 如果没有找到例句，返回清理后的默认句子
        return f"DEFAULT SENTECT: I LIKE TO {word} EVRY DAY."
    except Exception as e:
        # 打印错误信息用于调试
        print(f"Error getting example sentence for {word}: {e}")
        return f"DEFAULT SENTECT: I LIKE TO {word} EVRY DAY."

def create_blank_sentence(word, sentence):
    """Replace the target word with blanks in the sentence, handling variations"""
    import re
    
    # 确保句子已经清理过HTML标签
    cleaned_sentence = clean_html_tags(sentence)
    
    # 策略1：优先尝试匹配单词的基本形式（不区分大小写）
    # 使用正则表达式确保匹配整个单词
    pattern_base = re.compile(rf'\b{re.escape(word)}\b', re.IGNORECASE)
    if pattern_base.search(cleaned_sentence):
        # 找到实际出现在句子中的形式（保持原有大小写）
        match = pattern_base.search(cleaned_sentence)
        actual_word = cleaned_sentence[match.start():match.end()]
        return cleaned_sentence.replace(actual_word, "_____")
    
    # 策略2：如果基本形式没找到，尝试更灵活的匹配
    # 移除可能的标点符号进行匹配
    word_lower = word.lower()
    words_in_sentence = re.findall(r'\b\w+\b', cleaned_sentence)
    
    for i, w in enumerate(words_in_sentence):
        if w.lower() == word_lower:
            # 构建正则表达式来匹配这个具体的单词（包括可能的标点）
            pattern_specific = re.compile(rf'\b{re.escape(w)}\b')
            match = pattern_specific.search(cleaned_sentence)
            if match:
                # 获取匹配位置
                start, end = match.start(), match.end()
                # 创建空白句子
                return cleaned_sentence[:start] + "_____" + cleaned_sentence[end:]
    
    # 策略3：如果还是没找到，检查单词的变体（如复数、时态变化）
    # 简单的变体检测规则
    variants = [
        word + 's',  # 复数
        word + 'es',  # 复数变体
        word + 'ed',  # 过去式
        word + 'ing',  # 进行时
        word + 'er',  # 比较级
        word + 'est',  # 最高级
        word[:-1] + 'ies' if word.endswith('y') else None,  # 复数变体
        word + 'd' if not word.endswith('e') else None,  # 过去式变体
    ]
    
    for variant in variants:
        if variant:
            variant_pattern = re.compile(rf'\b{re.escape(variant)}\b', re.IGNORECASE)
            if variant_pattern.search(cleaned_sentence):
                match = variant_pattern.search(cleaned_sentence)
                actual_variant = cleaned_sentence[match.start():match.end()]
                return cleaned_sentence.replace(actual_variant, "_____")
    
    # 策略4：如果以上都失败，尝试部分匹配
    if word_lower in cleaned_sentence.lower():
        # 找到单词在句子中的位置（不区分大小写）
        start = cleaned_sentence.lower().find(word_lower)
        end = start + len(word)
        # 确保我们替换的是整个单词，而不是部分单词
        # 检查边界字符
        if (start == 0 or not cleaned_sentence[start-1].isalnum()) and \
           (end >= len(cleaned_sentence) or not cleaned_sentence[end].isalnum()):
            return cleaned_sentence[:start] + "_____" + cleaned_sentence[end:]
    
    # 策略5：如果都没有匹配到，手动创建包含空白的句子
    return cleaned_sentence + f" (Fill in: _____)"
    
def play_fill_blank_game():
    # ______ Fill-in-the-Blank Game (改进版) ______
    if st.session_state.get("game_started", False) and st.session_state.get("game_mode") == "Fill-in-the-Blank Game":
        st.subheader("📝 Fill-in-the-Blank Game")
        
        # 显示提示信息
        st.info(
            'When no dictionary example is available, a default sentence will be used '
            '("I LIKE TO ___ EVERY DAY.").'
        )
        
        # 初始化游戏状态
        if "fb_index" not in st.session_state:
            st.session_state.fb_index = 0
            st.session_state.fb_score = 0
            st.session_state.fb_total_questions = 0  # 只计算非fallback的题目数量
            st.session_state.fb_answers = [""] * 10
            st.session_state.fb_correct_answers = []
            st.session_state.fb_blanked_sentences = []
            st.session_state.fb_original_sentences = []
            st.session_state.fb_is_fallback = []  # 新增：记录是否为fallback句子
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
                
                # 创建填空句子
                blanked_sentence = create_blank_sentence(word, sentence)
                st.session_state.fb_blanked_sentences.append(blanked_sentence)
                
                # 检查是否为fallback句子
                is_fallback = "DEFAULT SENTENCE" in sentence.upper() or "DEFAULT SENTENCE" in blanked_sentence.upper()
                st.session_state.fb_is_fallback.append(is_fallback)
                
                # 如果不是fallback句子，增加题目计数
                if not is_fallback:
                    st.session_state.fb_total_questions += 1
                
                # 更新进度条
                progress_bar.progress((i + 1) / len(user_words))
            
            progress_bar.empty()
            
            # 3. 创建打乱的问题顺序
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
            
            # 显示是否为fallback句子（用图标表示）
            if is_fallback:
                st.info(f"📝 Question {idx + 1} of {len(user_words)} (🎯 Default Sentence - Not Counted)")
            else:
                st.info(f"📝 Question {idx + 1} of {len(user_words)}")
            
            # 显示填空句子
            st.markdown(f"### {current_sentence}")
            
            # 显示所有10个单词作为选项（保持原始顺序）
            st.write("**Select the correct word to fill in the blank:**")
            
            # 创建两列布局显示10个选项
            cols = st.columns(2)  # 创建两列
            
            # 将10个单词分配到两列
            for i, word in enumerate(user_words):
                col_idx = i % 2  # 0表示第一列，1表示第二列
                with cols[col_idx]:
                    # 使用button风格的选择
                    is_selected = st.session_state.get(f"fb_selected_{idx}") == word
                    button_type = "primary" if is_selected else "secondary"
                    
                    if st.button(
                        word,
                        key=f"fb_word_btn_{idx}_{i}",
                        use_container_width=True,
                        type=button_type
                    ):
                        # 记录用户选择
                        st.session_state[f"fb_selected_{idx}"] = word
                        st.rerun()
            
            # 显示当前选择的单词（如果有）
            if st.session_state.get(f"fb_selected_{idx}"):
                st.markdown(f"**Your current selection:** `{st.session_state[f'fb_selected_{idx}']}`")
            
            # 提交当前答案的按钮
            col1, col2 = st.columns(2)
            
            # 如果没有选择，禁用Submit按钮
            submit_disabled = st.session_state.get(f"fb_selected_{idx}") is None
            
            with col1:
                if st.button("✅ Submit Answer", 
                            key=f"fb_submit_{idx}", 
                            disabled=submit_disabled,
                            use_container_width=True):
                    # 获取用户选择
                    user_choice = st.session_state.get(f"fb_selected_{idx}", "")
                    
                    # 保存答案
                    st.session_state.fb_answers[current_order] = user_choice
                    
                    # 显示原始句子（展开状态）
                    with st.expander("📖 Show original sentence"):
                        st.write(f"**Original sentence:** {original_sentence}")
                        if is_fallback:
                            st.warning("⚠️ This is a default sentence - not counted in final score")
                    
                    # 检查答案（只有非fallback句子才计分）
                    if user_choice.lower() == correct_word.lower():
                        if not is_fallback:
                            st.session_state.fb_score += 1
                            st.success(f"✅ Correct! **'{correct_word}'** fits perfectly!")
                        else:
                            st.success(f"✅ Correct! **'{correct_word}'** fits perfectly! (Default sentence - not scored)")
                    else:
                        if not is_fallback:
                            st.error(f"❌ Wrong. You selected **'{user_choice}'**. The correct answer was **'{correct_word}'**.")
                        else:
                            st.error(f"❌ Wrong. You selected **'{user_choice}'**. The correct answer was **'{correct_word}'**. (Default sentence - not scored)")
                    
                    # 清除当前选择
                    if f"fb_selected_{idx}" in st.session_state:
                        del st.session_state[f"fb_selected_{idx}"]
                    
                    # 显示下一题按钮（等待用户点击）
                    st.session_state.fb_waiting_for_next = True
            
            # 如果等待下一题，显示Next按钮
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
            st.balloons()  # 庆祝动画
            
            # 计算有效题目（非fallback）的数量
            valid_questions = st.session_state.fb_total_questions
            if valid_questions > 0:
                st.success(f"🎮 Game Finished! Your score: **{st.session_state.fb_score}/{valid_questions}** (excluding default sentences)")
            else:
                st.success(f"🎮 Game Finished! All sentences were default sentences - no score calculated")
            
            # 创建结果表格
            df_data = []
            for i in range(len(user_words)):
                original_idx = st.session_state.fb_played_order[i]
                blanked_sentence = st.session_state.fb_blanked_sentences[original_idx]
                user_answer = st.session_state.fb_answers[original_idx]
                correct_answer = st.session_state.fb_correct_answers[original_idx]
                original_sentence = st.session_state.fb_original_sentences[original_idx]
                is_fallback = st.session_state.fb_is_fallback[original_idx]
                
                # 检查是否答对（只有非fallback句子才需要判断）
                if is_fallback:
                    result = "⚪ Default"
                    scored = "No"
                else:
                    is_correct = user_answer.lower() == correct_answer.lower() if user_answer else False
                    result = "✅ Correct" if is_correct else "❌ Wrong"
                    scored = "Yes"
                
                df_data.append({
                    "Blanked Sentence": blanked_sentence,
                    "Original Sentence": original_sentence,
                    "Correct Answer": correct_answer,
                    "Your Answer": user_answer if user_answer else "(No answer)",
                    "Result": result,
                    "Scored?": scored
                })
            
            df = pd.DataFrame(df_data)
            
            # 添加样式到表格
            st.subheader("📊 Your Results")
            
            # 使用st.dataframe以获得更好的控制
            st.dataframe(
                df,
                column_config={
                    "Blanked Sentence": st.column_config.TextColumn(
                        "Fill-in Sentence",
                        width="large"
                    ),
                    "Original Sentence": st.column_config.TextColumn(
                        "Original Sentence",
                        width="large"
                    ),
                    "Correct Answer": "Correct Word",
                    "Your Answer": "Your Choice",
                    "Result": st.column_config.TextColumn(
                        "Result",
                        help="✅ = Correct, ❌ = Wrong, ⚪ = Default sentence"
                    ),
                    "Scored?": st.column_config.TextColumn(
                        "Counted?",
                        help="Whether this question was counted in your final score"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
            
            # 显示分数统计（只计算非fallback题目）
            if valid_questions > 0:
                accuracy = (st.session_state.fb_score / valid_questions) * 100
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Score", f"{st.session_state.fb_score}/{valid_questions}")
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
                
                # 显示统计信息
                fallback_count = len([x for x in st.session_state.fb_is_fallback if x])
                st.info(f"📊 Statistics: {len(user_words)} total questions, {valid_questions} scored questions, {fallback_count} default sentences")
            else:
                st.warning("⚠️ All sentences were default sentences. Your performance is not scored.")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Score", "N/A")
                with col2:
                    st.metric("Accuracy", "N/A")
                with col3:
                    st.metric("Performance", "No Score")
            
            # 添加两个按钮
            st.markdown("---")
            st.write("### What would you like to do next?")
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("🔄 Play Again", 
                            use_container_width=True,
                            help="Play the same game again with new random order"):
                    # 重置填空游戏状态
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
                        if key.startswith("fb_selected_"):
                            del st.session_state[key]
                    st.rerun()
            
            with col2:
                if st.button("🎮 Try Another Game", 
                            use_container_width=True,
                            help="Go back to choose a different game mode"):
                    # 返回游戏选择界面
                    st.session_state.game_started = False
                    # 只重置填空游戏特定状态
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
                        if key.startswith("fb_selected_"):
                            del st.session_state[key]
                    st.rerun()
            
            with col3:
                if st.button("🏠 Main Menu", 
                            use_container_width=True,
                            help="Return to the main menu"):
                    # 完全重置所有状态
                    st.session_state.game_started = False
                    st.session_state.game_mode = None
                    # 清除所有填空游戏状态
                    for key in ["fb_index", "fb_score", "fb_total_questions", "fb_answers", 
                               "fb_correct_answers", "fb_blanked_sentences",
                               "fb_original_sentences", "fb_is_fallback", "fb_played_order", 
                               "fb_waiting_for_next"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    # 清除所有选择状态
                    for key in list(st.session_state.keys()):
                        if key.startswith("fb_selected_"):
                            del st.session_state[key]
                    st.rerun()
                                
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
