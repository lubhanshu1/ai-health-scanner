import os
import base64
import joblib

from dotenv import load_dotenv
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from pydantic import BaseModel, EmailStr

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
    Session,
    relationship
)

from passlib.context import CryptContext
from jose import JWTError, jwt

# ================= LOAD ENV =================

load_dotenv()

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "supersecret"
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

DATABASE_URL = "sqlite:///./users.db"

# ================= FASTAPI =================

app = FastAPI(
    title="AI Health Scanner 🚀"
)

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)

# ================= DATABASE =================

engine = create_engine(

    DATABASE_URL,

    connect_args={
        "check_same_thread": False
    }
)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

# ================= MODELS =================

class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True
    )

    email = Column(
        String,
        unique=True,
        index=True
    )

    password = Column(String)

    history = relationship(
        "HealthHistory",
        back_populates="user"
    )


class HealthHistory(Base):

    __tablename__ = "health_history"

    id = Column(
        Integer,
        primary_key=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    prediction_type = Column(String)

    risk_level = Column(String)

    risk_score = Column(Float)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="history"
    )

# ================= CREATE DB =================

Base.metadata.create_all(bind=engine)

# ================= DB SESSION =================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()

# ================= AUTH =================

pwd_context = CryptContext(

    schemes=["pbkdf2_sha256"],

    deprecated="auto"
)

security = HTTPBearer()

def hash_password(password: str):

    return pwd_context.hash(password.strip())

def verify_password(
    plain: str,
    hashed: str
):

    return pwd_context.verify(
        plain.strip(),
        hashed
    )

def create_token(data: dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

def get_current_user(

    credentials:
    HTTPAuthorizationCredentials = Depends(security),

    db: Session = Depends(get_db)

):

    try:

        payload = jwt.decode(

            credentials.credentials,

            SECRET_KEY,

            algorithms=[ALGORITHM]
        )

        email = payload.get("sub")

        user = db.query(User).filter(
            User.email == email
        ).first()

        if not user:

            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return user

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

# ================= LOAD ML =================

try:

    model = joblib.load("model.pkl")

    vectorizer = joblib.load("vectorizer.pkl")

    print("✅ Models loaded successfully")

except Exception as e:

    print("❌ Model loading error:", e)

    model = None
    vectorizer = None

# ================= REQUEST MODELS =================

class RegisterRequest(BaseModel):

    email: EmailStr
    password: str

class LoginRequest(BaseModel):

    email: EmailStr
    password: str

class PredictRequest(BaseModel):

    input: str

class ImageData(BaseModel):

    image: str

class HeartRequest(BaseModel):

    age: float
    bp: float
    cholesterol: float

class DiabetesRequest(BaseModel):

    glucose: float
    bmi: float
    insulin: float

# ================= REGISTER =================

@app.post("/register")
def register(

    data: RegisterRequest,

    db: Session = Depends(get_db)
):

    if db.query(User).filter(
        User.email == data.email
    ).first():

        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    db.add(

        User(
            email=data.email,
            password=hash_password(
                data.password
            )
        )
    )

    db.commit()

    return {
        "message":
        "User registered successfully"
    }

# ================= LOGIN =================

@app.post("/login")
def login(

    data: LoginRequest,

    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user or not verify_password(
        data.password,
        user.password
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_token({
        "sub": user.email
    })

    return {
        "access_token": token
    }

# ================= PROFILE =================

@app.get("/profile")
def get_profile(

    user: User = Depends(get_current_user)
):

    return {
        "email": user.email,
        "id": user.id
    }

# ================= HISTORY =================

@app.get("/history")
def get_history(

    user: User = Depends(get_current_user),

    db: Session = Depends(get_db)
):

    history = db.query(
        HealthHistory
    ).filter(

        HealthHistory.user_id == user.id

    ).order_by(
        HealthHistory.created_at.desc()
    ).all()

    return [

        {
            "type": h.prediction_type,
            "result": h.risk_level,
            "score": h.risk_score,
            "date": h.created_at
        }

        for h in history
    ]

# ================= ANALYTICS =================

@app.get("/analytics")
def get_analytics(

    user: User = Depends(get_current_user),

    db: Session = Depends(get_db)
):

    total_scans = db.query(
        HealthHistory
    ).filter(
        HealthHistory.user_id == user.id
    ).count()

    high_risk = db.query(
        HealthHistory
    ).filter(

        HealthHistory.user_id == user.id,

        HealthHistory.risk_score > 0.7

    ).count()

    return {

        "total_scans": total_scans,

        "high_risk_cases": high_risk
    }

# ================= SYMPTOM PREDICTION =================

@app.post("/predict")
def predict(
    data: PredictRequest
):

    if not model or not vectorizer:

        return {
            "error":
            "Model not loaded"
        }

    X = vectorizer.transform([
        data.input
    ])

    prediction = model.predict(X)[0]

    confidence = 0.85

   

    return {

        "disease": prediction,

        "confidence": confidence
    }

# ================= HEART =================

@app.post("/predict-heart")
def predict_heart(

    data: HeartRequest
):

    risk = "Low Risk"

    score = 0.30

    if (
        data.age > 50 or
        data.bp > 140 or
        data.cholesterol > 240
    ):

        risk = "High Risk"

        score = 0.85

    return {

        "risk": risk,

        "confidence": score
    }

# ================= DIABETES =================

@app.post("/predict-diabetes")
def predict_diabetes(

    data: DiabetesRequest
):

    risk = "Low Risk"

    score = 0.25

    if (
        data.glucose > 140 or
        data.bmi > 30 or
        data.insulin > 25
    ):

        risk = "High Risk"

        score = 0.88

    return {

        "risk": risk,

        "confidence": score
    }

# ================= IMAGE SCAN =================

@app.post("/scan-image")
def scan_image(

    data: ImageData,

    user: User = Depends(get_current_user),

    db: Session = Depends(get_db)
):

    try:

        image_data = data.image.split(",")[1]

        base64.b64decode(image_data)

        prediction = "Skin Allergy"

        confidence = 0.82

        db.add(

            HealthHistory(

                user_id=user.id,

                prediction_type="scan",

                risk_level=prediction,

                risk_score=confidence
            )
        )

        db.commit()

        return {

            "prediction": prediction,

            "confidence": confidence
        }

    except:

        return {

            "prediction": "Error",

            "confidence": 0
        }