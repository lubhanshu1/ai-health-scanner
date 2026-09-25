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
    history: list[dict[str, str]] = Field(default_factory=list, max_length=8)


def local_health_assistant(message: str, history: list[dict[str, str]] | None = None) -> str:
    q = message.strip().lower()
    previous = " ".join(str(x.get("content","")) for x in (history or [])[-4:]).lower()
    combined = q + " " + previous

    if any(x in q for x in ["hello", "hi", "hey", "who are you"]):
        return "Hi — I’m your Nexus Health Assistant. I can explain screening inputs, risk factors, and general health information. What are you checking today?"
    if any(x in q for x in ["thank", "thanks"]):
        return "You’re welcome. If you share what you’re trying to understand, I can break it into simple steps."
    if any(x in q for x in ["chest pain", "difficulty breathing", "can't breathe", "cannot breathe", "fainting", "passed out"]):
        return "Chest pain, severe breathing difficulty, fainting, or sudden severe symptoms can need urgent assessment. Please seek urgent medical care or contact local emergency services rather than relying on this app."
    if any(x in q for x in ["glucose", "blood sugar", "sugar level", "diabetes"]):
        if any(x in q for x in ["129", "126", "100", "high", "elevated"]):
            return "For glucose, the meaning depends on whether the measurement was fasting, after eating, or part of another test. A single reading does not establish a diagnosis. If you’re concerned about a repeated abnormal result, discuss it with a clinician."
        return "Glucose is one input used in diabetes screening. Interpretation depends on context such as fasting status, other measurements, symptoms, and medical history. This app provides a screening estimate rather than a diagnosis."
    if any(x in q for x in ["blood pressure", "bp", "systolic", "diastolic"]):
        return "Blood pressure is usually interpreted using repeated measurements rather than one isolated reading. Systolic pressure is the upper number and diastolic is the lower number. If readings are repeatedly elevated, consider discussing them with a healthcare professional."
    if any(x in q for x in ["heart", "cholesterol", "heart rate", "oldpeak"]):
        return "The heart screen uses several measurements together, including age, resting blood pressure, cholesterol, maximum heart rate, and an exercise-related ECG feature. The combined model output is a screening estimate, not a diagnosis."
    if "bmi" in q or "body mass" in q:
        return "BMI is calculated from weight and height. It is a population-level screening measure and does not by itself diagnose health conditions. It is best interpreted alongside other clinical information."
    if any(x in q for x in ["risk", "risk factors", "why", "result", "score"]):
        return "Risk scores combine several inputs into an estimate. A higher score does not prove that a person has a disease, and a lower score does not rule one out. I can explain any factor shown in your latest screening artifact."
    if any(x in q for x in ["fever", "temperature", "cold", "flu"]):
        return "For fever or an acute illness, focus on hydration, rest, symptom monitoring, and appropriate medical advice. Seek prompt care for severe symptoms, breathing difficulty, confusion, significant dehydration, or worsening illness."
    if any(x in q for x in ["diet", "food", "eat", "exercise", "workout"]):
        return "General healthy habits often include a varied diet, regular physical activity appropriate for your condition, adequate sleep, and avoiding tobacco. Specific medical or dietary plans should be individualized with a qualified professional."
    if any(x in q for x in ["fields", "inputs", "what do i enter", "how does this work"]):
        return "Overview uses age, glucose, systolic blood pressure, and BMI. Heart uses age, sex, resting BP, cholesterol, maximum heart rate, and oldpeak. Diabetes uses the standard screening variables shown in the form. I can explain any one of them."
    if any(x in combined for x in ["explain fields", "screening fields"]):
        return "Sure. Start with the field you’re unsure about — glucose, blood pressure, BMI, cholesterol, heart rate, or another input — and I’ll explain what it represents and why it appears in the screen."
    return "I can help with glucose, blood pressure, BMI, heart-risk inputs, diabetes-risk inputs, screening scores, or general health information. Tell me what you want to understand and I’ll answer that specific question."


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
