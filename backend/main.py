import os
import joblib
import numpy as np
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

# ================= LOAD ENV =================

load_dotenv()

DATABASE_URL = "sqlite:///./users.db"
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ================= APP =================

app = FastAPI(title="AI Health Scanner - ML Powered")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "AI Health API Running"}

# ================= DATABASE =================

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True)
    password = Column(String)

    history = relationship("HealthHistory", back_populates="user")


class HealthHistory(Base):
    __tablename__ = "health_history"

    id = Column(Integer, primary_key=True)
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


def hash_password(password):
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def create_token(data: dict):
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

        user = db.query(User).filter(User.email == email).first()

        if not user:
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
    age: int
    sex: int
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

    existing_user = db.query(User).filter(User.email == data.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        email=data.email,
        password=hash_password(data.password)
    )

    db.add(user)
    db.commit()

    return {"message": "User registered successfully"}


@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"sub": user.email})

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ================= LOAD ML MODELS =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    diabetes_model = joblib.load(os.path.join(BASE_DIR, "diabetes_model.pkl"))
    heart_model = joblib.load(os.path.join(BASE_DIR, "heart_model.pkl"))
    print("ML models loaded successfully")
except Exception as e:
    print("Model loading error:", e)
    diabetes_model = None
    heart_model = None


# ================= HEART RISK =================

@app.post("/heart-risk")
def heart_risk(
    data: HeartRiskInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if heart_model is None:
        raise HTTPException(status_code=500, detail="Heart model not loaded")

    features = np.array([[ 
        data.age,
        data.sex,
        data.trestbps,
        data.chol,
        data.thalach,
        data.oldpeak
    ]])

    prob = heart_model.predict_proba(features)[0][1]

    level = "Low" if prob < 0.4 else "Moderate" if prob < 0.7 else "High"

    db.add(HealthHistory(
        user_id=user.id,
        prediction_type="Heart",
        risk_level=level,
        risk_score=float(prob)
    ))

    db.commit()

    return {
        "risk_level": level,
        "risk_score": float(prob)
    }


# ================= DIABETES RISK =================

@app.post("/diabetes-risk")
def diabetes_risk(
    data: DiabetesRiskInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if diabetes_model is None:
        raise HTTPException(status_code=500, detail="Diabetes model not loaded")

    features = np.array([[ 
        data.Pregnancies,
        data.Glucose,
        data.BloodPressure,
        data.SkinThickness,
        data.Insulin,
        data.BMI,
        data.DiabetesPedigreeFunction,
        data.Age
    ]])

    prob = diabetes_model.predict_proba(features)[0][1]

    level = "Low" if prob < 0.4 else "Moderate" if prob < 0.7 else "High"

    db.add(HealthHistory(
        user_id=user.id,
        prediction_type="Diabetes",
        risk_level=level,
        risk_score=float(prob)
    ))

    db.commit()

    return {
        "risk_level": level,
        "risk_score": float(prob)
    }


# ================= HISTORY =================

@app.get("/history")
def history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    records = db.query(HealthHistory)\
        .filter(HealthHistory.user_id == user.id)\
        .order_by(HealthHistory.created_at.desc())\
        .all()

    return [
        {
            "prediction_type": r.prediction_type,
            "risk_level": r.risk_level,
            "risk_score": r.risk_score,
            "created_at": r.created_at
        }
        for r in records
    ]


# ================= AI CHAT =================

@app.post("/chat")
def chat(data: ChatRequest):

    message = data.message.lower()

    if "hello" in message or "hi" in message:
        reply = "Hello! I am your AI Health Assistant. How can I help you today?"

    elif "diabetes" in message:
        reply = "Diabetes is a disease where blood sugar levels become high. Maintaining diet and exercise helps control it."

    elif "heart" in message:
        reply = "Heart disease risk increases with smoking, high cholesterol, and lack of exercise."

    else:
        reply = "I recommend consulting a doctor for proper medical advice."

    return {"reply": reply}