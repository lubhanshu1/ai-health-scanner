import os
import joblib
import numpy as np
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from passlib.context import CryptContext
from jose import JWTError, jwt

# ================= CONFIG =================

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

DATABASE_URL = "sqlite:////tmp/users.db"

# ================= APP =================

app = FastAPI(title="AI Health Scanner - ML Powered")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= DATABASE =================

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

Base.metadata.create_all(bind=engine)

# ================= AUTH =================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ================= REQUEST MODELS =================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class HeartRiskInput(BaseModel):
    age: int = Field(..., ge=1, le=120)
    sex: int = Field(..., ge=0, le=1)
    trestbps: float
    chol: float
    thalach: float
    oldpeak: float

class DiabetesRiskInput(BaseModel):
    Pregnancies: int
    Glucose: float
    BloodPressure: float
    SkinThickness: float
    Insulin: float
    BMI: float
    DiabetesPedigreeFunction: float
    Age: int

# ================= AUTH ROUTES =================

@app.post("/register")
def register(data: RegisterRequest):
    db: Session = SessionLocal()
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=data.email,
        password=hash_password(data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully"}

@app.post("/login")
def login(data: LoginRequest):
    db: Session = SessionLocal()
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

# ================= LOAD MODELS =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
diabetes_model = joblib.load(os.path.join(BASE_DIR, "diabetes_model.pkl"))
heart_model = joblib.load(os.path.join(BASE_DIR, "heart_model.pkl"))

# ================= HEART =================

@app.post("/heart-risk")
def heart_risk(data: HeartRiskInput):
    features = np.array([[ 
        data.age,
        data.sex,
        data.trestbps,
        data.chol,
        data.thalach,
        data.oldpeak
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

# ================= DIABETES =================

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

    return {
        "prediction": risk_level,
        "risk_probability": round(float(probability), 3)
    }