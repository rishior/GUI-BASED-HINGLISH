from flask import Flask
from flask.wrappers import Request
from requests.models import Response
from flask import request
from sklearn.feature_extraction.text import TfidfVectorizer, TfidfTransformer
import pickle
import os

app = Flask(__name__)

# Use relative paths based on the directory of this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Preload stopwords, vocabulary, and model
with open(os.path.join(BASE_DIR, "stopwords.txt"), "r", encoding="utf-8") as my_file:
    STOPWORDS = my_file.read().split("\n")

VOCAB = pickle.load(open(os.path.join(BASE_DIR, "tfidf_vector_vocabulary.pkl"), "rb"))
TFIDF = TfidfVectorizer(stop_words=STOPWORDS, lowercase=True, vocabulary=VOCAB)
MODEL = pickle.load(open(os.path.join(BASE_DIR, "LinearSVC.pkl"), "rb"))

BULLYING_EMOJIS = {
    "\U0001F595",  # 🖕 Middle finger
    "\U0001F92C",  # 🤬 Cursing face
    "\U0001F921",  # 🤡 Clown face
    "\U0001F4A9",  # 💩 Pile of poo
    "\U0001F44E",  # 👎 Thumbs down
}

EMOJI_MAP = {
    "\U0001F595": "fuck you",
    "\U0001F92C": "abusive cursing",
    "\U0001F921": "clown idiot",
    "\U0001F4A9": "shit ganda",
    "\U0001F44E": "dislike hate",
}

def process_msg(msg):
    if msg == "hi":
        response = "Hello, Welcome to the cyberbullying detection bot!"
    else:
        # 1. Direct emoji check
        is_bullying = False
        for emo in BULLYING_EMOJIS:
            if emo in msg:
                is_bullying = True
                break
        
        # 2. Demojize text
        clean_text = msg
        for emo, rep in EMOJI_MAP.items():
            clean_text = clean_text.replace(emo, f" {rep} ")

        if not is_bullying:
            data = TFIDF.fit_transform([clean_text.strip()])
            pred = MODEL.predict(data)
            if str(pred[0]) == '1':
                is_bullying = True

        if is_bullying:
            response = "Output from my ML Model :- bullying"
        else:
            response = "Output from my ML Model :- non-bullying"
            
    return response 


@app.route("/testing", methods = ["POST"])
def testing():
    f = request.form 
    msg = f['Body']
    sender = f.get('From', 'User')
    response = process_msg(msg)
    return response, 200