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

# ------------------- Merriam-Webster API -------------------
MW_API_KEY = "b03334be-a55f-4416-9ff4-782b15a4dc77"  

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
            return f"I like to {word} every day."
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
                                return vis_list[0]["t"]
        return f"I like to {word} every day."
    except:
        return f"I like to {word} every day."

# ------------------- create blank in sentence -------------------
def create_blank_sentence(word, sentence):
    """
    Replace the word in the sentence with _____.
    Use regex to match different cases.
    """
    if not sentence:
        return f"Please fill in the blank: I like to {word}."

    # \b ensures word boundary, ignore case
    pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    new_sentence = pattern.sub("_____", sentence)

    # if the word was not found in the sentence, append at end
    if "_____" not in new_sentence:
        new_sentence = f"{sentence} (fill in: {word})"

    return new_sentence

# ------------------- Reading files -------------------
def read_file(file):
    """Read words from txt/csv/docx/pdf file-like object (Streamlit UploadFile)."""
    words = []
    name = file.name.lower()
    try:
        if name.endswith((".txt", ".csv")):
            # UploadFile.read() returns bytes
            content = file.read().decode("utf-8", errors="ignore")
            words = content.split()
        elif name.endswith(".docx"):
            # docx.Document accepts a path or a file-like object (works in-memory)
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
        # if any error reading, return empty list (caller can show warning)
        return []
    return [w.strip() for w in words if w.strip()]

# ------------------- reading from images -------------------
def read_image(image_file):
    """Run OCR via pytesseract; return list of words. If OCR fails, return []."""
    try:
        # image_file is UploadFile; use BytesIO
        img = Image.open(io.BytesIO(image_file.read()))
        text = pytesseract.image_to_string(img)
        words = [w.strip() for w in text.split() if w.strip()]
        return words
    except UnidentifiedImageError:
        return []
    except Exception:
        # If pytesseract or tesseract binary is missing, return []
        return []

# ------------------- define Scramble Game -------------------
def scramble_word(w):
    letters = list(w)
    if len(letters) <= 1:
        return w
    random.shuffle(letters)
    scrambled = "".join(letters)
    # ensure scrambled is different (try a few times)
    tries = 0
    while scrambled == w and tries < 10:
        random.shuffle(letters)
        scrambled = "".join(letters)
        tries += 1
    return scrambled

# ------------------- Matching Game helpers -------------------
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
    if "matching_words_generated" not in st.session_state or not st.session_state.matching_words_generated:
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
        # Use the stored answer as the default value. Provide options of cn_list (shuffled)
        current_choice = st.session_state.matching_answers.get(en_word, "Select")
        sel = st.selectbox(
            f"{en_word} ->",
            options=["Select"] + cn_list,
            index=(0 if current_choice not in (["Select"] + cn_list) else (["Select"] + cn_list).index(current_choice)),
            key=f"matching_{en_word}"
        )
        # Save selection into session_state mapping for persistence
        st.session_state.matching_answers[en_word] = sel

    if st.button("Submit Matching Game"):
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
        # end game
        st.session_state.game_started = False

# ------------------- Streamlit Design -------------------
st.set_page_config(page_title="Vocabuddy", layout="centered")
st.title("Hi, Welcome to Vocabuddy")

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

# Sentence Completion Game state
if "sc_sentences" not in st.session_state:
    st.session_state.sc_sentences = [""] * 10
if "sc_user_answers" not in st.session_state:
    st.session_state.sc_user_answers = [""] * 10
if "sc_index" not in st.session_state:
    st.session_state.sc_index = 0
if "sc_score" not in st.session_state:
    st.session_state.sc_score = 0


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
    st.markdown("### 2. Start your vacab journey!")
    st.session_state.game_mode = st.selectbox(
        "Choose game mode",
        ["Spell it", "Define it", "Use it"],
        index=0
    )

    # Start Game button: also reset per-game session flags
    if st.button("Start Game"):
        st.session_state.game_started = True
        # reset Scramble Game
        st.session_state.scramble_index = 0
        st.session_state.scramble_score = 0
        st.session_state.scramble_answers = [""] * 10
        st.session_state.scramble_scrambled = [""] * 10
        # reset Matching Game
        st.session_state.matching_answers = {}
        st.session_state.matching_score = 0
        st.session_state.matching_words_generated = False
        # shuffle words for scramble game (store as new list)
        random.shuffle(st.session_state.user_words)
        
            # reset Sentence Completion
    st.session_state.sc_index = 0
    st.session_state.sc_score = 0
    st.session_state.sc_sentences = []
    st.session_state.sc_user_answers = [""] * 10

    # Generate example sentences ONCE
    for w in st.session_state.user_words:
        example = get_example_sentence_mw(w)
        blanked = create_blank_sentence(w, example)
        st.session_state.sc_sentences.append((w, blanked))


# ------------------- Spell it/Scrambled Game -------------------
if st.session_state.game_started and st.session_state.game_mode == "Scrambled Letters Game":
    st.subheader("Spell the word in correct order")
    idx = st.session_state.scramble_index

    if idx < len(st.session_state.user_words):
        current_word = st.session_state.user_words[idx]

        if not st.session_state.scramble_scrambled[idx]:
            scrambled = scramble_word(current_word)
            st.session_state.scramble_scrambled[idx] = scrambled
        else:
            scrambled = st.session_state.scramble_scrambled[idx]

        def submit_answer():
            answer = st.session_state.scramble_input
            st.session_state.scramble_answers[idx] = answer.strip()
            if answer.strip().lower() == current_word.lower():
                st.session_state.scramble_score += 1
            st.session_state.scramble_index += 1
            st.session_state.scramble_input = ""

        st.text_input(
            f"Word {idx + 1}: {scrambled}",
            key="scramble_input",
            on_change=submit_answer
        )
    else:
        st.success(f"Game finished! Your score: {st.session_state.scramble_score}/10")
        data = {
            "Word": st.session_state.user_words,
            "Scrambled": st.session_state.scramble_scrambled,
            "Your Answer": st.session_state.scramble_answers,
            "Correct?": [
                ua.strip().lower() == w.lower()
                for ua, w in zip(st.session_state.scramble_answers, st.session_state.user_words)
            ]
        }
        df = pd.DataFrame(data)
        st.subheader("Your accuracy")
        st.table(df)
        st.session_state.game_started = False

# ------------------- Matching Game -------------------
if st.session_state.game_started and st.session_state.game_mode == "Matching Game":
    play_matching_game()

# ------------------- use it/Sentence Completion Game -------------------
if st.session_state.game_started and st.session_state.game_mode == "Sentence Completion Game":
    st.subheader("Fill in the missing word")

    idx = st.session_state.sc_index

    if idx < 10:
        word, sentence = st.session_state.sc_sentences[idx]

        st.markdown(f"### Sentence {idx+1}")
        st.write(sentence)

        def submit_sc_answer():
            ans = st.session_state.sc_input.strip()
            st.session_state.sc_user_answers[idx] = ans
            if ans.lower() == word.lower():
                st.session_state.sc_score += 1
            st.session_state.sc_index += 1
            st.session_state.sc_input = ""

        st.text_input("Your answer:", key="sc_input", on_change=submit_sc_answer)

    else:
        st.success(f"Game finished! Your score: {st.session_state.sc_score}/10")

        df = pd.DataFrame({
            "Word": [w for w, s in st.session_state.sc_sentences],
            "Sentence": [s for w, s in st.session_state.sc_sentences],
            "Your Answer": st.session_state.sc_user_answers,
            "Correct?": [
                ua.lower() == w.lower()
                for (w, s), ua in zip(st.session_state.sc_sentences, st.session_state.sc_user_answers)
            ]
        })

        st.subheader("Your performance")
        st.table(df)

        st.session_state.game_started = False
