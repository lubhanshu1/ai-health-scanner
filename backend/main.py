import os
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, create_engine, func
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
from passlib.context import CryptContext
from jose import JWTError, jwt

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "www"
SECRET_KEY = os.getenv("SECRET_KEY") or "dev-only-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'users.db'}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

app = FastAPI(title="AI Health Scanner", version="3.0.0")
security = HTTPBearer(auto_error=True)

allowed_origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allowed_origins != ["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    history = relationship("HealthHistory", back_populates="user", cascade="all, delete-orphan")


class HealthHistory(Base):
    __tablename__ = "health_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_type = Column(String(50), nullable=False)
    risk_level = Column(String(30), nullable=False)
    risk_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user = relationship("User", back_populates="history")


Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_token(user_id: int, email: str) -> str:
    expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "email": email, "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", "0"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class SimpleRequest(BaseModel):
    age: float = Field(ge=1, le=120)
    glucose: float = Field(ge=20, le=600)
    bp: float = Field(ge=40, le=300)
    bmi: float = Field(ge=5, le=100)


class HeartRequest(BaseModel):
    age: float = Field(ge=1, le=120)
    sex: int = Field(ge=0, le=1)
    trestbps: float = Field(ge=50, le=300)
    chol: float = Field(ge=50, le=700)
    thalach: float = Field(ge=40, le=250)
    oldpeak: float = Field(ge=0, le=20)


class DiabetesRequest(BaseModel):
    pregnancies: float = Field(ge=0, le=30)
    glucose: float = Field(ge=20, le=600)
    blood_pressure: float = Field(ge=30, le=250)
    skin_thickness: float = Field(ge=0, le=150)
    insulin: float = Field(ge=0, le=1000)
    bmi: float = Field(ge=5, le=100)
    diabetes_pedigree: float = Field(ge=0, le=5)
    age: float = Field(ge=1, le=120)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


# Model runtime.
# The checked-in artifacts are trusted repository files. If an artifact was serialized
# with an incompatible sklearn version, we retrain deterministically from the bundled
# datasets instead of serving a potentially incompatible model.
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import InconsistentVersionWarning

DIABETES_MODEL = None
HEART_MODEL = None
MODEL_STATUS = {"diabetes": "offline", "heart": "offline"}

def train_runtime_models():
    global DIABETES_MODEL, HEART_MODEL, MODEL_STATUS
    status = {}

    diabetes = pd.read_csv(BASE_DIR / "diabetes.csv")
    Xd = diabetes.drop("Outcome", axis=1)
    yd = diabetes["Outcome"]
    Xtr, Xte, ytr, yte = train_test_split(Xd, yd, test_size=0.20, random_state=42, stratify=yd)
    DIABETES_MODEL = RandomForestClassifier(n_estimators=300, max_depth=7, random_state=42, class_weight="balanced")
    DIABETES_MODEL.fit(Xtr, ytr)
    dp = DIABETES_MODEL.predict(Xte)
    dprob = DIABETES_MODEL.predict_proba(Xte)[:, 1]
    status["diabetes"] = {"status": "trained", "accuracy": round(float(accuracy_score(yte, dp)), 4), "roc_auc": round(float(roc_auc_score(yte, dprob)), 4)}

    heart = pd.read_csv(BASE_DIR / "heart.csv", names=["age","sex","cp","trestbps","chol","fbs","restecg","thalach","exang","oldpeak","slope","ca","thal","target"])
    heart.replace("?", pd.NA, inplace=True)
    heart = heart.dropna().astype(float)
    heart["target"] = heart["target"].apply(lambda x: 1 if x > 0 else 0)
    features = ["age","sex","trestbps","chol","thalach","oldpeak"]
    Xh, yh = heart[features], heart["target"]
    Xtr, Xte, ytr, yte = train_test_split(Xh, yh, test_size=0.20, random_state=42, stratify=yh)
    HEART_MODEL = Pipeline([
        ("scaler", StandardScaler()),
        ("rf", RandomForestClassifier(n_estimators=400, max_depth=8, min_samples_split=4, min_samples_leaf=2, class_weight="balanced", random_state=42))
    ])
    HEART_MODEL.fit(Xtr, ytr)
    hp = HEART_MODEL.predict(Xte)
    hprob = HEART_MODEL.predict_proba(Xte)[:, 1]
    status["heart"] = {"status": "trained", "accuracy": round(float(accuracy_score(yte, hp)), 4), "roc_auc": round(float(roc_auc_score(yte, hprob)), 4)}
    MODEL_STATUS = status

try:
    with warnings.catch_warnings():
        warnings.simplefilter("error", InconsistentVersionWarning)
        DIABETES_MODEL = joblib.load(BASE_DIR / "diabetes_model.pkl")
        HEART_MODEL = joblib.load(BASE_DIR / "heart_model.pkl")
    MODEL_STATUS = {"diabetes": {"status": "artifact-ready"}, "heart": {"status": "artifact-ready"}}
except Exception:
    train_runtime_models()


def classify(score: float) -> tuple[str, float]:
    score = max(0.0, min(1.0, float(score)))
    if score >= 0.70:
        return "High", round(score, 3)
    if score >= 0.40:
        return "Moderate", round(score, 3)
    return "Low", round(score, 3)


def save_result(db: Session, user: User, prediction_type: str, risk_level: str, score: float) -> None:
    db.add(HealthHistory(
        user_id=user.id,
        prediction_type=prediction_type,
        risk_level=risk_level,
        risk_score=score,
    ))
    db.commit()


def diabetes_reasons(data: DiabetesRequest) -> list[str]:
    reasons = []
    if data.glucose >= 126:
        reasons.append("elevated glucose")
    elif data.glucose >= 100:
        reasons.append("borderline glucose")
    if data.bmi >= 30:
        reasons.append("BMI in obesity range")
    elif data.bmi >= 25:
        reasons.append("BMI in overweight range")
    if data.age >= 45:
        reasons.append("age-related risk factor")
    if data.blood_pressure >= 140:
        reasons.append("elevated blood pressure")
    if data.pregnancies >= 4:
        reasons.append("higher pregnancy count")
    if data.diabetes_pedigree >= 0.5:
        reasons.append("higher family-history proxy")
    return reasons


def heart_reasons(data: HeartRequest) -> list[str]:
    reasons = []
    if data.age >= 55:
        reasons.append("age-related risk factor")
    elif data.age >= 45:
        reasons.append("age-related risk factor")
    if data.trestbps >= 140:
        reasons.append("elevated resting blood pressure")
    elif data.trestbps >= 130:
        reasons.append("borderline blood pressure")
    if data.chol >= 240:
        reasons.append("high cholesterol")
    elif data.chol >= 200:
        reasons.append("borderline cholesterol")
    if data.thalach < 100:
        reasons.append("low maximum heart rate")
    if data.oldpeak >= 2:
        reasons.append("higher exercise-related ST depression")
    elif data.oldpeak >= 1:
        reasons.append("exercise-related ST depression")
    return reasons


def diabetes_screen(data: DiabetesRequest) -> tuple[str, float, list[str], str]:
    reasons = diabetes_reasons(data)
    method = "RandomForest model"

    if DIABETES_MODEL is not None:
        frame = pd.DataFrame([{
            "Pregnancies": data.pregnancies,
            "Glucose": data.glucose,
            "BloodPressure": data.blood_pressure,
            "SkinThickness": data.skin_thickness,
            "Insulin": data.insulin,
            "BMI": data.bmi,
            "DiabetesPedigreeFunction": data.diabetes_pedigree,
            "Age": data.age,
        }])
        try:
            score = float(DIABETES_MODEL.predict_proba(frame)[0][1])
            level, score = classify(score)
            return level, score, reasons, method
        except Exception:
            pass

    # Safe deterministic fallback if the trusted artifact cannot load.
    score = 0.05
    if data.glucose >= 126: score += 0.40
    elif data.glucose >= 100: score += 0.20
    if data.bmi >= 30: score += 0.20
    elif data.bmi >= 25: score += 0.10
    if data.age >= 45: score += 0.10
    if data.blood_pressure >= 140: score += 0.10
    if data.pregnancies >= 4: score += 0.05
    if data.diabetes_pedigree >= 0.5: score += 0.05
    level, score = classify(score)
    return level, score, reasons, "deterministic screening fallback"


def heart_screen(data: HeartRequest) -> tuple[str, float, list[str], str]:
    reasons = heart_reasons(data)
    method = "RandomForest + StandardScaler model"

    if HEART_MODEL is not None:
        frame = pd.DataFrame([{
            "age": data.age,
            "sex": data.sex,
            "trestbps": data.trestbps,
            "chol": data.chol,
            "thalach": data.thalach,
            "oldpeak": data.oldpeak,
        }])
        try:
            score = float(HEART_MODEL.predict_proba(frame)[0][1])
            level, score = classify(score)
            return level, score, reasons, method
        except Exception:
            pass

    score = 0.05
    if data.age >= 55: score += 0.20
    elif data.age >= 45: score += 0.10
    if data.trestbps >= 140: score += 0.25
    elif data.trestbps >= 130: score += 0.10
    if data.chol >= 240: score += 0.20
    elif data.chol >= 200: score += 0.10
    if data.thalach < 100: score += 0.15
    if data.oldpeak >= 2: score += 0.15
    elif data.oldpeak >= 1: score += 0.05
    if data.sex == 1: score += 0.05
    level, score = classify(score)
    return level, score, reasons, "deterministic screening fallback"


def local_health_assistant(message: str) -> str:
    text = message.lower()
    if any(x in text for x in ["chest pain", "difficulty breathing", "can't breathe", "cannot breathe", "fainting"]):
        return "Chest pain, severe breathing difficulty, fainting, or sudden severe symptoms can be emergencies. Please seek urgent medical care or contact local emergency services rather than relying on this app."
    if "diabetes" in text or "blood sugar" in text or "glucose" in text:
        return "Diabetes screening commonly considers glucose, BMI, age, blood pressure, and other factors. A screening score is not a diagnosis; persistent abnormal glucose should be discussed with a clinician."
    if "heart" in text or "cholesterol" in text or "blood pressure" in text:
        return "Heart-risk screening can consider age, blood pressure, cholesterol, heart rate, and exercise-related measurements. Results here are educational screening estimates, not a diagnosis."
    if "fever" in text:
        return "For fever, hydration and monitoring are important. Seek medical care for severe symptoms, persistent high fever, confusion, breathing difficulty, dehydration, or worsening condition."
    if "bmi" in text:
        return "BMI is a screening measure based on height and weight and does not by itself diagnose health conditions. It should be interpreted alongside other clinical information."
    return "I can explain the screening fields, risk factors, and general health information. I cannot diagnose a condition or replace a qualified healthcare professional."


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": app.version,
        "models": MODEL_STATUS,
        "chat": "openai" if os.getenv("OPENAI_API_KEY") else "local-safe-assistant",
        "time": datetime.utcnow().isoformat(),
    }


@app.get("/model-info")
def model_info():
    return {
        "version": app.version,
        "models": MODEL_STATUS,
        "note": "Accuracy is dataset-dependent; no responsible medical model can be guaranteed to be 100% accurate on unseen patients.",
    }


@app.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(email=email, password=hash_password(data.password))
    db.add(user)
    db.commit()
    return {"message": "User registered successfully"}


@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_token(user.id, user.email), "token_type": "bearer"}


@app.get("/profile")
def profile(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}


@app.get("/history")
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(HealthHistory).filter(HealthHistory.user_id == user.id).order_by(HealthHistory.created_at.desc()).limit(100).all()
    return [{
        "id": row.id,
        "type": row.prediction_type,
        "risk": row.risk_level,
        "score": row.risk_score,
        "date": row.created_at.isoformat(),
    } for row in rows]


@app.get("/analytics")
def analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total = db.query(HealthHistory).filter(HealthHistory.user_id == user.id).count()
    counts = dict(
        db.query(HealthHistory.risk_level, func.count(HealthHistory.id))
        .filter(HealthHistory.user_id == user.id)
        .group_by(HealthHistory.risk_level)
        .all()
    )
    return {
        "total_scans": total,
        "low": counts.get("Low", 0),
        "moderate": counts.get("Moderate", 0),
        "high": counts.get("High", 0),
    }


@app.post("/predict")
@app.post("/predict-simple")
def predict(data: SimpleRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    score = 0.05
    reasons = []
    if data.glucose >= 126:
        score += 0.40; reasons.append("elevated glucose")
    elif data.glucose >= 100:
        score += 0.20; reasons.append("borderline glucose")
    if data.bmi >= 30:
        score += 0.20; reasons.append("high BMI")
    elif data.bmi >= 25:
        score += 0.10; reasons.append("elevated BMI")
    if data.bp >= 140:
        score += 0.20; reasons.append("elevated blood pressure")
    elif data.bp >= 130:
        score += 0.10; reasons.append("borderline blood pressure")
    if data.age >= 45:
        score += 0.10; reasons.append("age-related factor")
    risk, score = classify(score)
    save_result(db, user, "Overview", risk, score)
    return {
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons,
        "method": "deterministic screening",
        "disclaimer": "Screening only; not a diagnosis.",
    }


@app.post("/predict-heart")
@app.post("/heart-risk")
def predict_heart(data: HeartRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    risk, score, reasons, method = heart_screen(data)
    save_result(db, user, "Heart", risk, score)
    return {
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons,
        "method": method,
        "disclaimer": "Screening only; not a diagnosis.",
    }


@app.post("/predict-diabetes")
@app.post("/diabetes-risk")
def predict_diabetes(data: DiabetesRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    risk, score, reasons, method = diabetes_screen(data)
    save_result(db, user, "Diabetes", risk, score)
    return {
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons,
        "method": method,
        "disclaimer": "Screening only; not a diagnosis.",
    }


@app.post("/scan-image")
async def scan_image(image: UploadFile = File(...), user: User = Depends(get_current_user)):
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP images are supported")
    content = await image.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 5 MB or smaller")
    if not content:
        raise HTTPException(status_code=400, detail="Empty image")
    return {
        "status": "received",
        "filename": image.filename,
        "size_bytes": len(content),
        "prediction": None,
        "confidence": None,
        "message": "Image received. No validated medical vision model is installed, so the app will not fabricate a diagnosis.",
    }


@app.post("/chat")
def chat(data: ChatRequest, user: User = Depends(get_current_user)):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"reply": local_health_assistant(data.message), "configured": False, "mode": "local-safe-assistant"}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
            instructions=(
                "You are a health-information assistant, not a doctor. "
                "Give concise general educational information. Never diagnose, never invent test results, "
                "and advise professional care for urgent or concerning symptoms."
            ),
            input=data.message,
            max_output_tokens=500,
        )
        return {"reply": response.output_text, "configured": True, "mode": "openai"}
    except Exception:
        return {"reply": local_health_assistant(data.message), "configured": True, "mode": "safe-fallback"}


@app.get("/")
def serve_app():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{path:path}")
def static_files(path: str):
    candidate = (FRONTEND_DIR / path).resolve()
    if candidate.is_file() and str(candidate).startswith(str(FRONTEND_DIR.resolve())):
        return FileResponse(candidate)
    return FileResponse(FRONTEND_DIR / "index.html")
