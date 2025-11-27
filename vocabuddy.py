# import tkinter to visualize the GUI
# import pytesseract for OCR functionality 
import tkinter as tk
from tkinter import filedialog, messagebox
import pytesseract
from PIL import Image
import docx
import PyPDF2

user_words = []

# upload file function
#need to make sure it accepts txt, csv, docx, pdf files
def upload_file():
    global user_words
    file_path = filedialog.askopenfilename(
        filetypes=[("All supported", "*.txt *.csv *.docx *.pdf")]
    )
    if not file_path:
        return
    
    try:
        words = []
        if file_path.endswith(".txt") or file_path.endswith(".csv"):
            with open(file_path, 'r', encoding='utf-8') as f:
                words = f.read().split()
        elif file_path.endswith(".docx"):
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                words += para.text.split()
        elif file_path.endswith(".pdf"):
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    words += page.extract_text().split()
        
        words = [w.strip() for w in words if w.strip()]
        if len(words) != 10:
            messagebox.showerror("Error!", "Only ten words are allowed!")
            return
        user_words[:] = words
        messagebox.showinfo( "Success", "File upload successful!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read: {e}")

# upload image function with OCR
# need to identify different types of pictures
def upload_image():
    global user_words
    img_path = filedialog.askopenfilename(
        filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif")]
    )
    if not img_path:
        return
    try:
        text = pytesseract.image_to_string(Image.open(img_path))
        words = text.split()
        words = [w.strip() for w in words if w.strip()]
        if len(words) != 10:
            messagebox.showerror("Error", "Only ten words are allowed!")
            return
        user_words[:] = words
        messagebox.showinfo("Success", "OCR upload successful!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read: {e}")

# define start game function
def start_game():
    global user_words
    if user_words:
        generate_game()
        return

    words_input = text_box.get("1.0", tk.END).strip()
    words = [w.strip() for w in words_input.split() if w.strip()]
    
    if len(words) != 10:
        messagebox.showerror("错误", "请输入正好 10 个单词")
        return
    
    user_words[:] = words
    generate_game()

# 游戏逻辑（拼写游戏）
def generate_game():
    game_window = tk.Toplevel(root)
    game_window.title("拼写游戏")
    
    import random
    random.shuffle(user_words)
    current_index = tk.IntVar(value=0)
    score = tk.IntVar(value=0)
    
    prompt_label = tk.Label(game_window, text=f"输入单词: {user_words[current_index.get()]}")
    prompt_label.pack(pady=10)
    
    answer_entry = tk.Entry(game_window)
    answer_entry.pack()
    
    def check_answer():
        if answer_entry.get().strip().lower() == user_words[current_index.get()].lower():
            score.set(score.get() + 1)
        current_index.set(current_index.get() + 1)
        if current_index.get() < len(user_words):
            prompt_label.config(text=f"输入单词: {user_words[current_index.get()]}")
            answer_entry.delete(0, tk.END)
        else:
            messagebox.showinfo("游戏结束", f"你的得分: {score.get()}/{len(user_words)}")
            game_window.destroy()
    
    submit_btn = tk.Button(game_window, text="提交", command=check_answer)
    submit_btn.pack(pady=5)

# Tkinter GUI setup
root = tk.Tk()
root.title("单词练习生成器")

tk.Label(root, text="请输入10个单词（用空格或换行分开）:").pack(pady=5)
text_box = tk.Text(root, height=10, width=30)
text_box.pack(pady=5)

tk.Button(root, text="上传文件 (txt/csv/docx/pdf)", command=upload_file).pack(pady=5)
tk.Button(root, text="上传图片", command=upload_image).pack(pady=5)
tk.Button(root, text="开始游戏", command=start_game).pack(pady=10)

root.mainloop()
