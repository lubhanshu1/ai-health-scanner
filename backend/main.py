import os
import joblib
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
from openai import OpenAI

# ================= LOAD ENV =================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

DATABASE_URL = "sqlite:///./users.db"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ================= APP =================
app = FastAPI(title="AI Health Scanner 🚀")

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

# ================= MODELS =================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    avatar = Column(String, default="https://i.pravatar.cc/150")

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

# ================= DB =================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ================= AUTH =================
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()

def hash_password(password: str):
    return pwd_context.hash(password.strip())

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain.strip(), hashed)

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                     db: Session = Depends(get_db)):

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
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

class AvatarUpdate(BaseModel):
    avatar: str

class SimpleInput(BaseModel):
    age: float
    glucose: float
    bp: float
    bmi: float

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

# ================= AUTH =================
@app.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    db.add(User(email=data.email, password=hash_password(data.password)))
    db.commit()

    return {"message": "User registered successfully"}

@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"sub": user.email})

    return {"access_token": token}

# ================= PROFILE =================
@app.get("/profile")
def profile(user: User = Depends(get_current_user)):
    return {"email": user.email, "avatar": user.avatar}

@app.post("/upload-avatar")
def upload_avatar(data: AvatarUpdate,
                  user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):

    user.avatar = data.avatar
    db.commit()
    return {"message": "Avatar updated"}

# ================= LOAD MODELS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

diabetes_model = joblib.load(os.path.join(BASE_DIR, "diabetes_model.pkl"))
heart_model = joblib.load(os.path.join(BASE_DIR, "heart_model.pkl"))

# ================= SAVE FUNCTION =================
def save_history(db, user, type_, level, prob):
    db.add(HealthHistory(
        user_id=user.id,
        prediction_type=type_,
        risk_level=level,
        risk_score=prob
    ))
    db.commit()

# ================= PREDICTIONS =================
@app.post("/predict-simple")
def predict_simple(data: SimpleInput,
                   user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):

    prob = float(diabetes_model.predict_proba([[0, data.glucose, data.bp, 0, 0, data.bmi, 0.5, data.age]])[0][1])
    level = "Low" if prob < 0.4 else "Moderate" if prob < 0.7 else "High"

    save_history(db, user, "Simple", level, prob)

    return {"risk_level": level, "risk_score": prob}


@app.post("/heart-risk")
def heart_risk(data: HeartRiskInput,
               user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):

    prob = float(heart_model.predict_proba([[data.age, data.sex, data.trestbps,
                                            data.chol, data.thalach, data.oldpeak]])[0][1])

    level = "Low" if prob < 0.4 else "Moderate" if prob < 0.7 else "High"

    save_history(db, user, "Heart", level, prob)

    return {"risk_level": level, "risk_score": prob}


@app.post("/diabetes-risk")
def diabetes_risk(data: DiabetesRiskInput,
                  user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):

    prob = float(diabetes_model.predict_proba([[data.Pregnancies, data.Glucose, data.BloodPressure,
                                               data.SkinThickness, data.Insulin, data.BMI,
                                               data.DiabetesPedigreeFunction, data.Age]])[0][1])

    level = "Low" if prob < 0.4 else "Moderate" if prob < 0.7 else "High"

    save_history(db, user, "Diabetes", level, prob)

    return {"risk_level": level, "risk_score": prob}

# ================= HISTORY =================
@app.get("/history")
def history(user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):

    records = db.query(HealthHistory)\
        .filter_by(user_id=user.id)\
        .order_by(HealthHistory.id.desc())\
        .all()

    return [{
        "type": r.prediction_type,
        "risk": r.risk_level,
        "score": round(r.risk_score * 100, 1),
        "time": str(r.created_at)
    } for r in records]

# ================= ANALYTICS (NEW 🔥) =================
@app.get("/analytics")
def analytics(user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):

    records = db.query(HealthHistory).filter_by(user_id=user.id).all()

    total = len(records)
    high = sum(1 for r in records if r.risk_level == "High")
    moderate = sum(1 for r in records if r.risk_level == "Moderate")
    low = sum(1 for r in records if r.risk_level == "Low")

    return {
        "total": total,
        "high": high,
        "moderate": moderate,
        "low": low
    }

# ================= CHAT =================
@app.post("/chat")
def chat(data: ChatRequest):

    if not OPENAI_API_KEY:
        return {"reply": "❌ OPENAI_API_KEY not set"}

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful health assistant."},
            {"role": "user", "content": data.message}
        ]
    )

    return {"reply": response.choices[0].message.content}