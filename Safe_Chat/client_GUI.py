import socket
import tkinter as tk
from tkinter import font
from tkinter import ttk
from tkinter import filedialog
import time
import threading
import pickle
import os
import sys
import warnings

# Reconfigure console output to UTF-8 on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

warnings.filterwarnings("ignore")
from sklearn.feature_extraction.text import TfidfVectorizer

# Use relative paths based on the directory of this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Preload stopwords, vocabulary, and model once at startup
with open(os.path.join(BASE_DIR, "stopwords.txt"), "r", encoding="utf-8") as my_file:
    STOPWORDS = my_file.read().split("\n")

VOCAB = pickle.load(open(os.path.join(BASE_DIR, "tfidf_vector_vocabulary.pkl"), "rb"))
TFIDF = TfidfVectorizer(stop_words=STOPWORDS, lowercase=True, vocabulary=VOCAB)
MODEL = pickle.load(open(os.path.join(BASE_DIR, "LinearSVC.pkl"), "rb"))

# Cyberbullying emojis (including skin tone variants)
BULLYING_EMOJIS = {
    "\U0001F595",  # 🖕 Middle finger
    "\U0001F595\U0001F3FB", "\U0001F595\U0001F3FC", "\U0001F595\U0001F3FD", "\U0001F595\U0001F3FE", "\U0001F595\U0001F3FF",
    "\U0001F92C",  # 🤬 Cursing face
    "\U0001F921",  # 🤡 Clown face
    "\U0001F4A9",  # 💩 Pile of poo
    "\U0001F44E",  # 👎 Thumbs down
    "\U0001F44E\U0001F3FB", "\U0001F44E\U0001F3FC", "\U0001F44E\U0001F3FD", "\U0001F44E\U0001F3FE", "\U0001F44E\U0001F3FF",
}

# Semantic mapping for emojis into text tokens for NLP classification
EMOJI_MAP = {
    "\U0001F595": "fuck you",
    "\U0001F92C": "abusive cursing",
    "\U0001F921": "clown idiot",
    "\U0001F4A9": "shit ganda",
    "\U0001F44E": "dislike hate",
}

# Shortcodes for typing emojis with regular text
EMOJI_SHORTCODES = {
    ":finger:": "\U0001F595",
    ":middle_finger:": "\U0001F595",
    ":middlefinger:": "\U0001F595",
    ":fuck:": "\U0001F595",
    ":curse:": "\U0001F92C",
    ":cursing:": "\U0001F92C",
    ":angry:": "\U0001F92C",
    ":clown:": "\U0001F921",
    ":joker:": "\U0001F921",
    ":poop:": "\U0001F4A9",
    ":poo:": "\U0001F4A9",
    ":shit:": "\U0001F4A9",
    ":tatti:": "\U0001F4A9",
    ":thumbsdown:": "\U0001F44E",
    ":thumbs_down:": "\U0001F44E",
    ":-1:": "\U0001F44E",
    ":smile:": "😀",
    ":fire:": "🔥",
    ":skull:": "💀",
    ":heart:": "❤️",
}


def replace_shortcodes(text):
    """Replaces text shortcodes like :finger: or :clown: with actual emojis."""
    for code, emo in EMOJI_SHORTCODES.items():
        text = text.replace(code, emo)
    return text


def check_bullying(text):
    """Predicts whether the given text is bullying (1) or non-bullying (0).
    Handles plain text, single emojis, and mixed word + emoji messages.
    """
    if not text or not text.strip():
        return 0

    # 1. Direct Emoji Check (single emoji, repeated emojis, or word + emoji)
    for emo in BULLYING_EMOJIS:
        if emo in text:
            return 1

    # 2. Demojize text (translate any mapped emojis to text tokens)
    clean_text = text
    for emo, word_rep in EMOJI_MAP.items():
        clean_text = clean_text.replace(emo, f" {word_rep} ")

    # 3. Predict using TF-IDF + LinearSVC ML model
    try:
        data = TFIDF.fit_transform([clean_text.strip()])
        pred = int(MODEL.predict(data)[0])
        return pred
    except:
        return 0


class GUI:
    def __init__(self, ip_address, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((ip_address, port))

        # Message tracking for retraction
        self.message_counter = 0
        self.message_tags = []
        self.local_buffer = []  # stores recent short tokens from self: list of (text, timestamp)
        self.more_emoji_window = None

        self.Window = tk.Tk()
        self.Window.withdraw()

        self.login = tk.Toplevel()
        self.login.title("Login")
        self.login.resizable(width=False, height=False)
        self.login.configure(width=400, height=350)

        self.pls = tk.Label(self.login, 
                            text="Please Login to a chatroom", 
                            justify=tk.CENTER,
                            font="Helvetica 12 bold")
        self.pls.place(relheight=0.15, relx=0.2, rely=0.07)

        self.userLabelName = tk.Label(self.login, text="Username: ", font="Helvetica 11")
        self.userLabelName.place(relheight=0.2, relx=0.1, rely=0.25)

        self.userEntryName = tk.Entry(self.login, font="Helvetica 12")
        self.userEntryName.place(relwidth=0.4, relheight=0.1, relx=0.35, rely=0.30)
        self.userEntryName.focus()

        self.roomLabelName = tk.Label(self.login, text="Room Id: ", font="Helvetica 12")
        self.roomLabelName.place(relheight=0.2, relx=0.1, rely=0.40)

        self.roomEntryName = tk.Entry(self.login, font="Helvetica 11", show="*")
        self.roomEntryName.place(relwidth=0.4, relheight=0.1, relx=0.35, rely=0.45)
        
        self.go = tk.Button(self.login, 
                            text="CONTINUE", 
                            font="Helvetica 12 bold", 
                            command=lambda: self.goAhead(self.userEntryName.get(), self.roomEntryName.get()))
        self.go.place(relx=0.35, rely=0.62)

        self.Window.mainloop()

    def goAhead(self, username, room_id="0"):
        self.name = username
        self.server.send(str.encode(username, encoding="utf-8"))
        time.sleep(0.1)
        self.server.send(str.encode(room_id, encoding="utf-8"))
        
        self.login.destroy()
        self.layout()

        rcv = threading.Thread(target=self.receive)
        rcv.daemon = True
        rcv.start()

    def layout(self):
        self.Window.deiconify()
        self.Window.title("SAFECHAT")
        self.Window.resizable(width=False, height=False)
        self.Window.configure(width=480, height=590, bg="#17202A")

        # Top Bar
        self.chatBoxHead = tk.Label(self.Window, 
                                    bg="#17202A", 
                                    fg="#EAECEE", 
                                    text=f"User: {self.name}", 
                                    font="Helvetica 11 bold", 
                                    anchor="w",
                                    padx=10)
        self.chatBoxHead.place(relx=0.01, rely=0.01, relwidth=0.70, relheight=0.05)

        # Clear Chat Button
        self.clearBtn = tk.Button(self.Window,
                                  text="Clear Chat",
                                  font="Helvetica 9 bold",
                                  bg="#C0392B",
                                  fg="#FFFFFF",
                                  activebackground="#E74C3C",
                                  activeforeground="#FFFFFF",
                                  cursor="hand2",
                                  command=self.clearChat)
        self.clearBtn.place(relx=0.73, rely=0.01, relwidth=0.25, relheight=0.05)

        self.line = tk.Label(self.Window, bg="#ABB2B9")
        self.line.place(relwidth=1, rely=0.065, relheight=0.005)

        # Chat Message History with Emoji font support
        self.textCons = tk.Text(self.Window, 
                                width=20, 
                                height=2, 
                                bg="#17202A", 
                                fg="#EAECEE", 
                                font=("Segoe UI Emoji", 11), 
                                padx=8, 
                                pady=8)
        self.textCons.place(relheight=0.66, relwidth=1, rely=0.07)

        # Tags for colored text
        self.textCons.tag_config("warning", foreground="#E74C3C", font=("Segoe UI Emoji", 10, "italic"))
        self.textCons.tag_config("system", foreground="#F39C12", font=("Segoe UI Emoji", 10, "italic"))

        # --- EMOJI TOOLBAR ---
        self.emojiBar = tk.Frame(self.Window, bg="#212F3D", height=38)
        self.emojiBar.place(relx=0, rely=0.735, relwidth=1, relheight=0.065)

        emoji_list = ["🖕", "🤬", "🤡", "💩", "👎", "😀", "😡", "💀", "🔥", "❤️"]
        for idx, emo in enumerate(emoji_list):
            btn = tk.Button(self.emojiBar, 
                            text=emo, 
                            font=("Segoe UI Emoji", 11), 
                            bg="#2C3E50", 
                            fg="#FFFFFF",
                            activebackground="#34495E",
                            activeforeground="#FFFFFF",
                            bd=0,
                            cursor="hand2",
                            command=lambda e=emo: self.insertEmoji(e))
            btn.place(relx=0.015 + (idx * 0.082), rely=0.12, relwidth=0.075, relheight=0.76)

        self.moreEmojiBtn = tk.Button(self.emojiBar,
                                      text="More 😊",
                                      font="Helvetica 8 bold",
                                      bg="#34495E",
                                      fg="#EAECEE",
                                      bd=0,
                                      cursor="hand2",
                                      command=self.toggleMoreEmojis)
        self.moreEmojiBtn.place(relx=0.84, rely=0.12, relwidth=0.145, relheight=0.76)

        # Bottom Input Area
        self.labelBottom = tk.Frame(self.Window, bg="#ABB2B9")
        self.labelBottom.place(relwidth=1, rely=0.805, relheight=0.09)

        # Text Input with Segoe UI Emoji font for proper emoji rendering
        self.entryMsg = tk.Entry(self.labelBottom, 
                                 bg="#2C3E50", 
                                 fg="#EAECEE", 
                                 insertbackground="#FFFFFF",
                                 font=("Segoe UI Emoji", 11))
        self.entryMsg.place(relwidth=0.75, relheight=0.72, rely=0.14, relx=0.015)
        self.entryMsg.focus()
        self.entryMsg.bind("<Return>", lambda event: self.sendButton(self.entryMsg.get()))
        # Clipboard paste handler for emoji safety
        self.entryMsg.bind("<Control-v>", self.onPaste)
        self.entryMsg.bind("<Control-V>", self.onPaste)

        self.buttonMsg = tk.Button(self.labelBottom, 
                                   text="Send", 
                                   font="Helvetica 10 bold", 
                                   bg="#2980B9", 
                                   fg="#FFFFFF",
                                   activebackground="#3498DB",
                                   activeforeground="#FFFFFF",
                                   cursor="hand2",
                                   command=lambda: self.sendButton(self.entryMsg.get()))
        self.buttonMsg.place(relx=0.78, rely=0.14, relheight=0.72, relwidth=0.20)

        # File Attachment Area
        self.labelFile = tk.Frame(self.Window, bg="#ABB2B9")
        self.labelFile.place(relwidth=1, rely=0.90, relheight=0.09)

        self.fileLocation = tk.Label(self.labelFile, 
                                     text="Choose file to send",
                                     bg="#2C3E50", 
                                     fg="#EAECEE", 
                                     font="Helvetica 10",
                                     anchor="w",
                                     padx=8)
        self.fileLocation.place(relwidth=0.62, relheight=0.72, rely=0.14, relx=0.015)

        self.browse = tk.Button(self.labelFile, 
                                text="Browse", 
                                font="Helvetica 9 bold", 
                                bg="#7F8C8D", 
                                fg="#FFFFFF",
                                cursor="hand2",
                                command=self.browseFile)
        self.browse.place(relx=0.65, rely=0.14, relheight=0.72, relwidth=0.16)

        self.sengFileBtn = tk.Button(self.labelFile, 
                                     text="Send File", 
                                     font="Helvetica 9 bold", 
                                     bg="#27AE60", 
                                     fg="#FFFFFF",
                                     activebackground="#2ECC71",
                                     cursor="hand2",
                                     command=self.sendFile)
        self.sengFileBtn.place(relx=0.82, rely=0.14, relheight=0.72, relwidth=0.16)

        self.textCons.config(cursor="arrow")
        scrollbar = tk.Scrollbar(self.textCons)
        scrollbar.place(relheight=1, relx=0.974)
        scrollbar.config(command=self.textCons.yview)
        self.textCons.config(state=tk.DISABLED)

    def insertEmoji(self, emoji_char):
        """Inserts an emoji directly into the message input field."""
        self.entryMsg.insert(tk.INSERT, emoji_char)
        self.entryMsg.focus_set()

    def onPaste(self, event=None):
        """Safely pastes text/emojis from Windows clipboard."""
        try:
            cb_text = self.Window.clipboard_get()
            self.entryMsg.insert(tk.INSERT, cb_text)
            return "break"
        except:
            return None

    def toggleMoreEmojis(self):
        """Opens a popup panel with additional emojis."""
        if self.more_emoji_window and tk.Toplevel.winfo_exists(self.more_emoji_window):
            self.more_emoji_window.destroy()
            self.more_emoji_window = None
            return

        self.more_emoji_window = tk.Toplevel(self.Window)
        self.more_emoji_window.title("Emojis")
        self.more_emoji_window.geometry("260x170")
        self.more_emoji_window.configure(bg="#212F3D")
        self.more_emoji_window.resizable(False, False)

        all_emojis = [
            "🖕", "🤬", "🤡", "💩", "👎",
            "😀", "😂", "😍", "😡", "💀",
            "🔥", "👍", "🎉", "🙏", "💯",
            "🤮", "😈", "💔", "👏", "👀"
        ]

        row = 0
        col = 0
        for emo in all_emojis:
            btn = tk.Button(self.more_emoji_window,
                            text=emo,
                            font=("Segoe UI Emoji", 12),
                            bg="#2C3E50",
                            fg="#FFFFFF",
                            bd=0,
                            cursor="hand2",
                            command=lambda e=emo: [self.insertEmoji(e), self.more_emoji_window.destroy()])
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            col += 1
            if col >= 5:
                col = 0
                row += 1

    def clearChat(self):
        """Erases all messages from the chat screen."""
        self.textCons.config(state=tk.NORMAL)
        self.textCons.delete("1.0", tk.END)
        self.textCons.config(state=tk.DISABLED)
        self.message_tags.clear()
        self.local_buffer.clear()

    def insertMessage(self, text, is_system=False, tag_type=None):
        """Inserts a message block into the text view with tracking for deletion."""
        self.textCons.config(state=tk.NORMAL)
        self.message_counter += 1
        tag = f"msg_{self.message_counter}"

        tags_to_apply = (tag,)
        if tag_type:
            tags_to_apply = (tag, tag_type)

        self.textCons.insert(tk.END, text + "\n\n", tags_to_apply)
        if not is_system:
            self.message_tags.append(tag)

        self.textCons.config(state=tk.DISABLED)
        self.textCons.see(tk.END)
        return tag

    def deleteLastMessages(self, count):
        """Deletes the last N user messages from the chat display."""
        self.textCons.config(state=tk.NORMAL)
        deleted = 0
        while self.message_tags and deleted < count:
            tag = self.message_tags.pop()
            ranges = self.textCons.tag_ranges(tag)
            if ranges:
                self.textCons.delete(ranges[0], ranges[1])
                deleted += 1
        self.textCons.config(state=tk.DISABLED)
        self.textCons.see(tk.END)

    def browseFile(self):
        self.filename = filedialog.askopenfilename(initialdir="/", 
                                                   title="Select a file",
                                                   filetypes=(("Text files", "*.txt*"), ("all files", "*.*")))
        if self.filename:
            self.fileLocation.configure(text="File Opened: " + os.path.basename(self.filename))

    def sendFile(self):
        if not hasattr(self, 'filename') or not self.filename:
            return
        self.server.send("FILE".encode("utf-8"))
        time.sleep(0.1)
        self.server.send(str("client_" + os.path.basename(self.filename)).encode("utf-8"))
        time.sleep(0.1)
        self.server.send(str(os.path.getsize(self.filename)).encode("utf-8"))
        time.sleep(0.1)

        with open(self.filename, "rb") as file:
            data = file.read(1024)
            while data:
                self.server.send(data)
                data = file.read(1024)

        self.insertMessage("<You> " + str(os.path.basename(self.filename)) + " Sent", is_system=True)

    def sendButton(self, msg):
        self.msg = msg
        self.entryMsg.delete(0, tk.END)
        snd = threading.Thread(target=self.sendMessage)
        snd.start()

    def sendMessage(self):
        # Automatically replace text shortcodes like :finger: or :clown: with actual emojis
        msg = replace_shortcodes(self.msg.strip())
        if not msg:
            return

        current_time = time.time()
        # Clean local buffer (> 20s)
        self.local_buffer = [item for item in self.local_buffer if current_time - item[1] < 20]

        # 1. Check if the message (text, single emoji, or word + emoji) is bullying
        if check_bullying(msg) == 1:
            self.local_buffer.clear()
            self.insertMessage("<You> Stop bullying people and behave decently.", is_system=True, tag_type="warning")
            self.server.send(msg.encode("utf-8"))
            return

        # 2. Check if combining with recent short messages forms a split bad word
        candidate_tokens = [item[0] for item in self.local_buffer] + [msg]
        detected_split = False
        retract_count = 0

        if len(candidate_tokens) > 1:
            for i in range(len(candidate_tokens)):
                sub_tokens = candidate_tokens[i:]
                sub_no_space = "".join(sub_tokens).strip()
                if len(sub_no_space) >= 3 and check_bullying(sub_no_space) == 1:
                    detected_split = True
                    retract_count = len(candidate_tokens) - 1 - i
                    break

                sub_with_space = " ".join(sub_tokens).strip()
                if len(sub_with_space) >= 3 and check_bullying(sub_with_space) == 1:
                    detected_split = True
                    retract_count = len(candidate_tokens) - 1 - i
                    break

        if detected_split:
            self.local_buffer.clear()
            # Immediately retract previous split letters locally from screen
            if retract_count > 0:
                self.deleteLastMessages(retract_count)
            self.insertMessage("<You> Stop bullying people and behave decently. (Split word detected and removed)", is_system=True, tag_type="warning")
            self.server.send(msg.encode("utf-8"))
            return

        # 3. Clean message: display and buffer if short
        if len(msg) <= 6:
            self.local_buffer.append((msg, current_time))
        else:
            self.local_buffer.clear()

        self.insertMessage("<You> " + msg)
        self.server.send(msg.encode("utf-8"))

    def prettyPrinter(self, data_1):
        """Maintained for backward compatibility."""
        return check_bullying(data_1)

    def receive(self):
        while True:
            try:
                message = self.server.recv(1024).decode("utf-8", errors="replace")
                if not message:
                    break

                if str(message) == "FILE":
                    file_name = self.server.recv(1024).decode("utf-8", errors="replace")
                    lenOfFile = self.server.recv(1024).decode("utf-8", errors="replace")
                    send_user = self.server.recv(1024).decode("utf-8", errors="replace")

                    if os.path.exists(file_name):
                        os.remove(file_name)

                    total = 0
                    with open(file_name, 'wb') as file:
                        while str(total) != lenOfFile:
                            data = self.server.recv(1024)
                            total = total + len(data)
                            file.write(data)

                    self.insertMessage(f"<{send_user}> {file_name} Received", is_system=True)

                elif message.startswith("CMD:RETRACT:"):
                    # Server instructed all clients to retract the last N split messages
                    parts = message.split(":")
                    if len(parts) >= 3:
                        count = int(parts[2])
                        self.deleteLastMessages(count)

                elif message.startswith("CMD:WARN:"):
                    warn_text = message[len("CMD:WARN:"):]
                    self.insertMessage("<System> " + warn_text, is_system=True, tag_type="warning")

                elif message.startswith("Bullying message detected") or message.startswith("<System>"):
                    self.insertMessage(message, is_system=True, tag_type="warning")

                else:
                    # Regular chat message from another user
                    self.insertMessage(message, is_system=False)

            except Exception as e:
                print("Connection error:", e)
                self.server.close()
                break


if __name__ == "__main__":
    ip_address = "127.0.0.1"
    port = 12345
    g = GUI(ip_address, port)
