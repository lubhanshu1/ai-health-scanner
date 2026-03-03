import os
import joblib
import numpy as np
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv
from openai import OpenAI

# ================= LOAD ENV =================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)

# ================= CONFIG =================

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ================= APP =================

app = FastAPI(title="AI Health Platform - Production Ready")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= DATABASE =================

# PostgreSQL should NOT use check_same_thread
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    history = relationship("HealthHistory", back_populates="user")

class HealthHistory(Base):
    __tablename__ = "health_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    prediction_type = Column(String)
    risk_level = Column(String)
    risk_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="history")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ================= AUTH =================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.email == email).first()

        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

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

class ChatRequest(BaseModel):
    message: str

# ================= AUTH ROUTES =================

@app.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
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
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.email})

    return {"access_token": token, "token_type": "bearer"}

# ================= LOAD ML MODELS =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
diabetes_model = joblib.load(os.path.join(BASE_DIR, "diabetes_model.pkl"))
heart_model = joblib.load(os.path.join(BASE_DIR, "heart_model.pkl"))

# ================= HEART =================

@app.post("/heart-risk")
def heart_risk(data: HeartRiskInput,
               current_user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):

    features = np.array([[ 
        data.age, data.sex, data.trestbps,
        data.chol, data.thalach, data.oldpeak
    ]])

    probability = heart_model.predict_proba(features)[0][1]

    risk_level = (
        "Low" if probability < 0.4
        else "Moderate" if probability < 0.7
        else "High"
    )

    db.add(HealthHistory(
        user_id=current_user.id,
        prediction_type="Heart",
        risk_level=risk_level,
        risk_score=float(probability)
    ))
    db.commit()

    return {
        "risk_level": risk_level,
        "risk_score": round(float(probability), 4)
    }

# ================= DIABETES =================

@app.post("/diabetes-risk")
def diabetes_risk(data: DiabetesRiskInput,
                  current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):

    features = np.array([[ 
        data.Pregnancies, data.Glucose,
        data.BloodPressure, data.SkinThickness,
        data.Insulin, data.BMI,
        data.DiabetesPedigreeFunction, data.Age
    ]])

    probability = diabetes_model.predict_proba(features)[0][1]

    risk_level = (
        "Low" if probability < 0.4
        else "Moderate" if probability < 0.7
        else "High"
    )

    db.add(HealthHistory(
        user_id=current_user.id,
        prediction_type="Diabetes",
        risk_level=risk_level,
        risk_score=float(probability)
    ))
    db.commit()

    return {
        "risk_level": risk_level,
        "risk_score": round(float(probability), 4)
    }

# ================= HISTORY =================

@app.get("/my-history")
def get_history(current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):

    records = db.query(HealthHistory)\
        .filter(HealthHistory.user_id == current_user.id)\
        .order_by(HealthHistory.created_at.desc())\
        .all()

    return [
        {
            "type": r.prediction_type,
            "risk_level": r.risk_level,
            "risk_score": r.risk_score,
            "date": r.created_at
        }
        for r in records
    ]

# ================= AI CHAT =================

@app.post("/chat")
def chat_assistant(data: ChatRequest,
                   current_user: User = Depends(get_current_user)):

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI health assistant. Provide general advice only. Always recommend consulting a doctor for serious issues."
                },
                {"role": "user", "content": data.message}
            ]
        )

        reply = response.choices[0].message.content
        return {"reply": reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))