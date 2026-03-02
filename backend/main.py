import os
import joblib
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="AI Health Scanner - ML Powered")

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- SAFE MODEL LOADING ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

diabetes_model = joblib.load(os.path.join(BASE_DIR, "diabetes_model.pkl"))
heart_model = joblib.load(os.path.join(BASE_DIR, "heart_model.pkl"))

# ---------------- MODEL INFO ----------------
@app.get("/model-info")
def model_info():
    return {
        "heart_model": "RandomForestClassifier",
        "diabetes_model": "RandomForestClassifier"
    }

# ==========================================================
# ❤️ HEART INPUT MODEL (MATCHES TRAINED MODEL EXACTLY)
# ==========================================================

class HeartRiskInput(BaseModel):
    age: int = Field(..., ge=1, le=120)
    sex: int = Field(..., ge=0, le=1)
    trestbps: float
    chol: float
    thalach: float
    oldpeak: float

# ==========================================================
# 🩸 DIABETES INPUT MODEL
# ==========================================================

class DiabetesRiskInput(BaseModel):
    Pregnancies: int
    Glucose: float
    BloodPressure: float
    SkinThickness: float
    Insulin: float
    BMI: float
    DiabetesPedigreeFunction: float
    Age: int

# ==========================================================
# ❤️ HEART RISK ENDPOINT (SIMPLIFIED & SAFE)
# ==========================================================

@app.post("/heart-risk")
def heart_risk(data: HeartRiskInput):
    try:
        features = np.array([[
            float(data.age),
            float(data.sex),
            float(data.trestbps),
            float(data.chol),
            float(data.thalach),
            float(data.oldpeak)
        ]])

        prediction = heart_model.predict(features)[0]
        probability = heart_model.predict_proba(features)[0][1]

        risk_level = (
            "Low" if probability < 0.4
            else "Moderate" if probability < 0.7
            else "High"
        )

        return {
            "prediction": int(prediction),
            "risk_level": risk_level,
            "risk_score": round(float(probability), 4)
        }

    except Exception as e:
        return {"error": str(e)}

# ==========================================================
# 🩸 DIABETES RISK ENDPOINT
# ==========================================================

@app.post("/diabetes-risk")
def predict_diabetes(data: DiabetesRiskInput):
    try:
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

        return {
            "prediction": risk_level,
            "risk_probability": round(float(probability), 3)
        }

    except Exception as e:
        return {"error": str(e)}