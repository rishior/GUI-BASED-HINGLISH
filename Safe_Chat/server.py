import socket 
from _thread import *
import sys
from collections import defaultdict as df
import pickle
import time
import os
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
    except Exception as e:
        print("Error checking bullying:", e)
        return 0


class Server:
    def __init__(self):
        self.rooms = df(list)
        # Buffer to store recent short messages per user: user_id -> list of (text, timestamp)
        self.user_buffers = df(list)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def accept_connections(self, ip_address, port):
        self.ip_address = ip_address
        self.port = port
        self.server.bind((self.ip_address, int(self.port)))
        self.server.listen(100)
        print(f"Server is listening on {self.ip_address}:{self.port}...")

        while True:
            connection, address = self.server.accept()
            print(f"{address[0]}:{address[1]} Connected")
            start_new_thread(self.clientThread, (connection,))

        self.server.close()

    def clientThread(self, connection):
        user_id = connection.recv(1024).decode("utf-8", errors="replace").replace("User ", "").strip()
        room_id = connection.recv(1024).decode("utf-8", errors="replace").replace("Join ", "").strip()

        if room_id not in self.rooms:
            connection.send("New Group created".encode("utf-8"))
        else:
            connection.send("Welcome to chat room".encode("utf-8"))

        self.rooms[room_id].append(connection)

        while True:
            try:
                message_bytes = connection.recv(1024)
                if not message_bytes:
                    self.remove(connection, room_id)
                    break

                message = message_bytes.decode("utf-8", errors="replace")

                if message == "FILE":
                    self.broadcastFile(connection, room_id, user_id)
                    continue

                current_time = time.time()
                # 1. Clean buffer items older than 20 seconds
                self.user_buffers[user_id] = [
                    item for item in self.user_buffers[user_id]
                    if current_time - item[1] < 20
                ]

                # 2. Check if the message (text, single emoji, or word + emoji) is bullying
                pred_single = check_bullying(message)
                if pred_single == 1:
                    print(f"Direct bullying detected from '{user_id}': {message}")
                    self.user_buffers[user_id].clear()
                    # Warn the sender directly
                    try:
                        connection.send("CMD:WARN:Stop bullying people and behave decently.".encode("utf-8"))
                    except:
                        pass
                    # Inform other users in the room
                    self.broadcast("Bullying message detected it has been hidden", connection, room_id, pred=1)
                    continue

                # 3. Check for split-character / multi-message evasion
                buffer_tokens = [item[0] for item in self.user_buffers[user_id]]
                candidate_tokens = buffer_tokens + [message]

                detected_split = False
                matched_word = ""
                retract_count = 0

                if len(candidate_tokens) > 1:
                    for i in range(len(candidate_tokens)):
                        sub_tokens = candidate_tokens[i:]
                        # A) Check concatenation without spaces (e.g. 'F'+'U'+'C'+'K' -> 'fuck')
                        sub_no_space = "".join(sub_tokens).strip()
                        if len(sub_no_space) >= 3 and check_bullying(sub_no_space) == 1:
                            detected_split = True
                            matched_word = sub_no_space
                            retract_count = len(candidate_tokens) - 1 - i
                            break

                        # B) Check combination with spaces (e.g. 'tu' + 'ganda' + 'hai')
                        sub_with_space = " ".join(sub_tokens).strip()
                        if len(sub_with_space) >= 3 and check_bullying(sub_with_space) == 1:
                            detected_split = True
                            matched_word = sub_with_space
                            retract_count = len(candidate_tokens) - 1 - i
                            break

                if detected_split:
                    print(f"Split bullying detected from '{user_id}': '{matched_word}' (retracting {retract_count} previous items)")
                    self.user_buffers[user_id].clear()

                    # Erase previously sent split letters from all clients in the room
                    if retract_count > 0:
                        retract_cmd = f"CMD:RETRACT:{retract_count}"
                        for client in self.rooms[room_id]:
                            try:
                                client.send(retract_cmd.encode("utf-8"))
                            except:
                                pass
                        time.sleep(0.05)

                    # Send warning to the offending sender
                    try:
                        connection.send("CMD:WARN:Stop bullying people! Split word detected and removed.".encode("utf-8"))
                    except:
                        pass

                    # Inform other clients in the room
                    time.sleep(0.05)
                    notice = f"<System> Split bullying attempt from {user_id} was detected and deleted."
                    for client in self.rooms[room_id]:
                        if client != connection:
                            try:
                                client.send(notice.encode("utf-8"))
                            except:
                                pass
                    continue

                # 4. Message is clean - broadcast normally
                # Keep short tokens (<= 6 characters) in the buffer to catch future split attempts
                if len(message.strip()) <= 6:
                    self.user_buffers[user_id].append((message, current_time))
                else:
                    self.user_buffers[user_id].clear()

                message_to_send = "<" + str(user_id) + "> " + message
                self.broadcast(message_to_send, connection, room_id, pred=0)

            except Exception as e:
                print(repr(e))
                print("Client disconnected earlier")
                break

    def broadcastFile(self, connection, room_id, user_id):
        file_name = connection.recv(1024).decode("utf-8", errors="replace")
        lenOfFile = connection.recv(1024).decode("utf-8", errors="replace")
        for client in self.rooms[room_id]:
            if client != connection:
                try: 
                    client.send("FILE".encode("utf-8"))
                    time.sleep(0.1)
                    client.send(file_name.encode("utf-8"))
                    time.sleep(0.1)
                    client.send(lenOfFile.encode("utf-8"))
                    time.sleep(0.1)
                    client.send(user_id.encode("utf-8"))
                except:
                    client.close()
                    self.remove(client, room_id)

        total = 0
        print(file_name, lenOfFile)
        while str(total) != lenOfFile:
            data = connection.recv(1024)
            total = total + len(data)
            for client in self.rooms[room_id]:
                if client != connection:
                    try: 
                        client.send(data)
                        time.sleep(0.1)
                    except:
                        client.close()
                        self.remove(client, room_id)

    def prettyPrinter(self, data_1):
        """Maintained for backward compatibility."""
        return check_bullying(data_1)

    def broadcast(self, message_to_send, connection, room_id, pred):
        for client in self.rooms[room_id]:
            if client != connection:
                try:
                    if pred == 0:
                        client.send(message_to_send.encode("utf-8"))
                    else:
                        client.send("Bullying message detected it has been hidden".encode("utf-8"))
                except:
                    client.close()
                    self.remove(client, room_id)

    def remove(self, connection, room_id):
        if connection in self.rooms[room_id]:
            self.rooms[room_id].remove(connection)


if __name__ == "__main__":
    ip_address = "127.0.0.1"
    port = 12345

    s = Server()
    s.accept_connections(ip_address, port)
