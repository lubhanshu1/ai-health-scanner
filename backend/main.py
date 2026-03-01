import joblib
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List

app = FastAPI(title="AI Health Scanner - ML Powered")

# ---------------- LOAD ML MODEL ----------------
diabetes_model = joblib.load("diabetes_model.pkl")


# 🔥 MODEL INFORMATION ENDPOINT (NEW)
@app.get("/model-info")
def model_info():
    return {
        "model_type": "RandomForestClassifier",
        "accuracy": 0.7467,
        "roc_auc": 0.8328,
        "dataset": "Pima Indians Diabetes Dataset",
        "features_used": 8,
        "description": "ML-based diabetes prediction model trained using scikit-learn."
    }


# ---------- MODELS ----------

class BMIInput(BaseModel):
    age: int = Field(..., ge=1, le=120)
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)


class SymptomInput(BaseModel):
    symptoms: List[str]


class HeartRiskInput(BaseModel):
    age: int = Field(..., ge=1, le=120)
    gender: str
    smoker: bool
    systolic_bp: int
    cholesterol: int
    diabetic: bool
    physically_active: bool


class DiabetesRiskInput(BaseModel):
    Pregnancies: int
    Glucose: float
    BloodPressure: float
    SkinThickness: float
    Insulin: float
    BMI: float
    DiabetesPedigreeFunction: float
    Age: int


class HealthScoreInput(BaseModel):
    age: int
    height_cm: float
    weight_kg: float
    sleep_hours: float
    stress_level: int
    physically_active: bool
    smoker: bool


# ---------- HOME ----------

@app.get("/")
def home():
    return {"message": "AI Health Scanner ML backend running successfully!"}


# ---------- 1. BMI ----------

@app.post("/bmi")
def calculate_bmi(data: BMIInput):
    height_m = data.height_cm / 100
    bmi = data.weight_kg / (height_m ** 2)

    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"

    return {
        "bmi": round(bmi, 2),
        "category": category,
        "summary": f"Your BMI is {round(bmi, 2)} which falls in the '{category}' range."
    }


# ---------- 2. SYMPTOM CHECKER ----------

SYMPTOM_RULES = {
    "fever": ["viral infection", "flu", "covid-like illness"],
    "cough": ["common cold", "bronchitis"],
    "chest pain": ["heart problem", "muscle strain"],
    "headache": ["migraine", "tension headache", "stress"],
    "shortness of breath": ["asthma", "heart or lung issue"],
    "fatigue": ["anemia", "thyroid issue", "sleep problem"],
}

@app.post("/symptom-check")
def symptom_check(data: SymptomInput):
    user_syms = [s.lower().strip() for s in data.symptoms]
    possible_conditions = set()

    for s in user_syms:
        for key, conditions in SYMPTOM_RULES.items():
            if key in s:
                possible_conditions.update(conditions)

    return {
        "entered_symptoms": user_syms,
        "possible_conditions": list(possible_conditions),
        "note": "For accurate diagnosis, consult a medical professional."
    }


# ---------- 3. HEART RISK ----------

@app.post("/heart-risk")
def heart_risk(data: HeartRiskInput):
    score = 0

    if data.age >= 45:
        score += 2
    if data.age >= 55:
        score += 2
    if data.smoker:
        score += 3
    if data.systolic_bp >= 130:
        score += 2
    if data.systolic_bp >= 150:
        score += 2
    if data.cholesterol >= 200:
        score += 2
    if data.cholesterol >= 240:
        score += 2
    if data.diabetic:
        score += 3
    if not data.physically_active:
        score += 2

    if score <= 3:
        risk = "Low"
    elif score <= 7:
        risk = "Moderate"
    else:
        risk = "High"

    return {
        "risk_level": risk,
        "risk_score": score,
        "note": "This is not a medical diagnosis."
    }


# ---------- 4. DIABETES RISK (ML POWERED) ----------

@app.post("/diabetes-risk")
def predict_diabetes(data: DiabetesRiskInput):

    input_data = np.array([[
        data.Pregnancies,
        data.Glucose,
        data.BloodPressure,
        data.SkinThickness,
        data.Insulin,
        data.BMI,
        data.DiabetesPedigreeFunction,
        data.Age
    ]])

    prediction = diabetes_model.predict(input_data)[0]
    probability = diabetes_model.predict_proba(input_data)[0][1]

    risk_level = "High Risk" if prediction == 1 else "Low Risk"

    confidence = (
        "Strong" if probability > 0.75
        else "Moderate" if probability > 0.55
        else "Low"
    )

    return {
        "prediction": risk_level,
        "risk_probability": round(float(probability), 3),
        "confidence": confidence,
        "model": "RandomForestClassifier"
    }


# ---------- 5. HEALTH SCORE ----------

@app.post("/health-score")
def health_score(data: HealthScoreInput):

    score = 100
    height_m = data.height_cm / 100
    bmi = data.weight_kg / (height_m ** 2)

    if bmi < 18.5 or bmi > 30:
        score -= 20
    elif bmi >= 25:
        score -= 10

    if data.sleep_hours < 6:
        score -= 15
    elif data.sleep_hours > 9:
        score -= 5

    score -= max(0, (data.stress_level - 4) * 3)

    if data.smoker:
        score -= 20

    if data.physically_active:
        score += 5
    else:
        score -= 10

    score = max(0, min(100, score))

    if score >= 80:
        level = "Excellent"
    elif score >= 60:
        level = "Good"
    elif score >= 40:
        level = "Average"
    else:
        level = "Poor"

    return {
        "health_score": score,
        "level": level,
        "bmi": round(bmi, 2),
        "note": "This is a rough AI-based estimation."
    }