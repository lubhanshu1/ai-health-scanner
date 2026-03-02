import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# ===============================
# LOAD UCI CLEVELAND DATASET
# ===============================

columns = [
    "age","sex","cp","trestbps","chol","fbs",
    "restecg","thalach","exang","oldpeak",
    "slope","ca","thal","target"
]

df = pd.read_csv("heart.csv", names=columns)

# Replace missing values marked as ?
df.replace("?", np.nan, inplace=True)
df = df.dropna()
df = df.astype(float)

# Convert target to binary
df["target"] = df["target"].apply(lambda x: 1 if x > 0 else 0)

# ===============================
# SELECT IMPORTANT FEATURES
# ===============================

features = [
    "age",
    "sex",
    "trestbps",
    "chol",
    "thalach",
    "oldpeak"
]

X = df[features]
y = df["target"]

# ===============================
# TRAIN TEST SPLIT
# ===============================

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ===============================
# TRAIN MODEL (IMPROVED)
# ===============================

model = Pipeline([
    ("scaler", StandardScaler()),
    ("rf", RandomForestClassifier(
        n_estimators=500,
        max_depth=8,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42
    ))
])

model.fit(X_train, y_train)

# ===============================
# EVALUATE
# ===============================

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
roc = roc_auc_score(y_test, y_prob)

print("\nModel Evaluation")
print("---------------------")
print("Accuracy:", round(accuracy, 4))
print("ROC-AUC:", round(roc, 4))
print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))

# ===============================
# SAVE MODEL
# ===============================

joblib.dump(model, "heart_model.pkl")

print("\nheart_model.pkl saved successfully!")