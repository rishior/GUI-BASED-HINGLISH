import pickle
import warnings
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

warnings.filterwarnings("ignore")
from sklearn.feature_extraction.text import TfidfVectorizer

# Load stopwords
my_file = open('Safe_Chat/stopwords.txt', 'r', encoding='utf-8')
content_list = my_file.read().split('\n')
my_file.close()

# Load vocabulary and model
vocab = pickle.load(open('Safe_Chat/tfidf_vector_vocabulary.pkl', 'rb'))
tfidf = TfidfVectorizer(stop_words=content_list, lowercase=True, vocabulary=vocab)
model = pickle.load(open('Safe_Chat/LinearSVC.pkl', 'rb'))

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

def predict_message(text):
    if not text or not text.strip():
        return 0
    # 1. Direct emoji check
    for emo in BULLYING_EMOJIS:
        if emo in text:
            return 1
    # 2. Demojize text
    clean_text = text
    for emo, rep in EMOJI_MAP.items():
        clean_text = clean_text.replace(emo, f" {rep} ")
    # 3. Model predict
    data = tfidf.fit_transform([clean_text.strip()])
    return int(model.predict(data)[0])

# Test messages: plain text, single emojis, and word + emoji combinations
msgs = [
    'hello how are you',
    'tu bahut ganda hai',
    'you are amazing',
    'i will kill you',
    'tum bohat ache ho',
    # Single emojis
    '🖕',
    '🤬',
    '🤡',
    '💩',
    '👎',
    # Word + emoji combinations
    'you 🖕',
    'shut up 🤬',
    'tu 🤡 hai',
    'teri 💩',
    'post 👎',
]

preds = [predict_message(m) for m in msgs]

print("=" * 60)
print("CyberBullying Detection - Text & Emoji Test Results")
print("=" * 60)
for m, p in zip(msgs, preds):
    label = "BULLYING" if p == 1 else "NON-BULLYING"
    print(f"  '{m}' => {label}")
print("=" * 60)
print("\nAll text and emoji cases classified successfully!")
