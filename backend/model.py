from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib

# Improved dataset
data = [
    ("fever cough headache body pain", "flu"),
    ("high fever chills sweating", "malaria"),
    ("chest pain shortness breath", "heart disease"),
    ("sneezing runny nose mild fever", "common cold"),
    ("thirst fatigue frequent urination", "diabetes"),
    ("weight loss cough blood", "tuberculosis"),
    ("joint pain fatigue rash", "dengue"),
]

texts = [d[0] for d in data]
labels = [d[1] for d in data]

vectorizer = CountVectorizer()
X = vectorizer.fit_transform(texts)

model = MultinomialNB()
model.fit(X, labels)

joblib.dump(model, "model.pkl")
joblib.dump(vectorizer, "vectorizer.pkl")

print("✅ Model trained with better dataset")