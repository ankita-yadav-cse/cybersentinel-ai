import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# ================= LOAD DATA =================
df = pd.read_csv("dataset/copy of spam.csv", encoding="latin-1")

df = df[['v1', 'v2']]
df.columns = ['label', 'text']

# ================= CLEAN =================
df["label"] = df["label"].map({"ham": 0, "spam": 1})
df["text"] = df["text"].str.lower().str.strip()

# ================= ADD CUSTOM SPAM =================
new_spam = [
    "your bank account has been blocked verify immediately",
    "update your kyc now",
    "upi account suspended click here",
    "you won lottery claim prize",
    "free iphone click now",
    "urgent account verification required",
    "bank account blocked suspicious activity",
    "win cash reward now",
    "claim your gift now",
    "limited time offer click now"
]

# ================= ADD CUSTOM HAM (IMPORTANT FIX) =================
new_ham = [
    "hi how are you",
    "let's meet tomorrow",
    "good morning have a nice day",
    "please send me the report",
    "are you coming to class today",
    "call me when you are free",
    "i will reach home late today",
    "let's discuss the project",
    "thank you for your help",
    "see you tomorrow"
]

# build dataframe
new_df_spam = pd.DataFrame({"label": [1]*len(new_spam), "text": new_spam})
new_df_ham = pd.DataFrame({"label": [0]*len(new_ham), "text": new_ham})

df = pd.concat([df, new_df_spam, new_df_ham], ignore_index=True)

# ================= SPLIT =================
X = df["text"]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ================= VECTORIZATION (FIXED) =================
vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),   # reduced from 3 → more stable
    max_features=10000
)

X_train = vectorizer.fit_transform(X_train)
X_test = vectorizer.transform(X_test)

# ================= MODEL =================
model = LogisticRegression(max_iter=2000)
model.fit(X_train, y_train)

# ================= EVALUATION =================
y_pred = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))

# ================= SAVE =================
joblib.dump(model, "model/spam_model.pkl")
joblib.dump(vectorizer, "model/vectorizer.pkl")

print("Model saved successfully!")