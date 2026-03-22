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
from openai import OpenAI

# ================= ENV =================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")

print("🔑 OPENAI_API_KEY:", OPENAI_API_KEY)  # DEBUG

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

# ================= CHAT =================
@app.post("/chat")
def chat(data: ChatRequest):

    if not OPENAI_API_KEY:
        return {"reply": "❌ OPENAI_API_KEY not set on server"}

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI health assistant."},
                {"role": "user", "content": data.message}
            ]
        )

        return {"reply": response.choices[0].message.content}

    except Exception as e:
        return {"reply": f"❌ ERROR: {str(e)}"}