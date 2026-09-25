import base64
import binascii
import os
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

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Development-only fallback. Production must provide SECRET_KEY.
    SECRET_KEY = "dev-only-change-me"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'users.db'}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

app = FastAPI(title="AI Health Scanner", version="2.0.0")
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


def classify(score: float) -> tuple[str, float]:
    score = max(0.0, min(1.0, score))
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


def diabetes_screen(data: DiabetesRequest) -> tuple[str, float, list[str]]:
    score = 0.05
    reasons = []
    if data.glucose >= 126:
        score += 0.40; reasons.append("elevated glucose")
    elif data.glucose >= 100:
        score += 0.20; reasons.append("borderline glucose")
    if data.bmi >= 30:
        score += 0.20; reasons.append("BMI in obesity range")
    elif data.bmi >= 25:
        score += 0.10; reasons.append("BMI in overweight range")
    if data.age >= 45:
        score += 0.10; reasons.append("age-related risk factor")
    if data.blood_pressure >= 140:
        score += 0.10; reasons.append("elevated blood pressure")
    if data.pregnancies >= 4:
        score += 0.05; reasons.append("higher pregnancy count")
    if data.diabetes_pedigree >= 0.5:
        score += 0.05; reasons.append("higher family-history proxy")
    level, score = classify(score)
    return level, score, reasons


def heart_screen(data: HeartRequest) -> tuple[str, float, list[str]]:
    score = 0.05
    reasons = []
    if data.age >= 55:
        score += 0.20; reasons.append("age-related risk factor")
    elif data.age >= 45:
        score += 0.10; reasons.append("age-related risk factor")
    if data.trestbps >= 140:
        score += 0.25; reasons.append("elevated resting blood pressure")
    elif data.trestbps >= 130:
        score += 0.10; reasons.append("borderline blood pressure")
    if data.chol >= 240:
        score += 0.20; reasons.append("high cholesterol")
    elif data.chol >= 200:
        score += 0.10; reasons.append("borderline cholesterol")
    if data.thalach < 100:
        score += 0.15; reasons.append("low maximum heart rate")
    if data.oldpeak >= 2:
        score += 0.15; reasons.append("higher exercise-related ST depression")
    elif data.oldpeak >= 1:
        score += 0.05; reasons.append("exercise-related ST depression")
    if data.sex == 1:
        score += 0.05
    level, score = classify(score)
    return level, score, reasons


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version, "time": datetime.utcnow().isoformat()}


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
    save_result(db, user, "Simple", risk, score)
    return {
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons,
        "method": "rule-based screening",
        "disclaimer": "Screening only; not a diagnosis.",
    }


@app.post("/predict-heart")
@app.post("/heart-risk")
def predict_heart(data: HeartRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    risk, score, reasons = heart_screen(data)
    save_result(db, user, "Heart", risk, score)
    return {
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons,
        "method": "rule-based screening",
        "disclaimer": "Screening only; not a diagnosis.",
    }


@app.post("/predict-diabetes")
@app.post("/diabetes-risk")
def predict_diabetes(data: DiabetesRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    risk, score, reasons = diabetes_screen(data)
    save_result(db, user, "Diabetes", risk, score)
    return {
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons,
        "method": "rule-based screening",
        "disclaimer": "Screening only; not a diagnosis.",
    }


@app.post("/scan-image")
async def scan_image(
    image: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP images are supported")
    content = await image.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 5 MB or smaller")
    if not content:
        raise HTTPException(status_code=400, detail="Empty image")

    # No diagnostic vision model is bundled with this repository. Do not fabricate a disease.
    return {
        "status": "received",
        "filename": image.filename,
        "size_bytes": len(content),
        "prediction": None,
        "confidence": None,
        "message": "Image received successfully. A validated medical image model is not installed, so no diagnosis is returned.",
    }


@app.post("/chat")
def chat(data: ChatRequest, user: User = Depends(get_current_user)):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "reply": "I can help explain health information, but the AI chat service is not configured yet. For urgent or severe symptoms, contact a qualified medical professional.",
            "configured": False,
        }
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
            instructions=(
                "You are a health-information assistant, not a doctor. "
                "Give general educational information, do not diagnose, do not invent test results, "
                "and recommend professional care for urgent or concerning symptoms."
            ),
            input=data.message,
            max_output_tokens=500,
        )
        return {"reply": response.output_text, "configured": True}
    except Exception:
        return {
            "reply": "The AI assistant is temporarily unavailable. Please try again later or contact a healthcare professional for urgent concerns.",
            "configured": True,
        }


@app.get("/")
def serve_app():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{path:path}")
def static_files(path: str):
    # Keep API routes above this catch-all. Only serve known files.
    candidate = (FRONTEND_DIR / path).resolve()
    if candidate.is_file() and str(candidate).startswith(str(FRONTEND_DIR.resolve())):
        return FileResponse(candidate)
    return FileResponse(FRONTEND_DIR / "index.html")
