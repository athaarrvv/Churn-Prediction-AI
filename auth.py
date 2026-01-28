from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import jwt
import json
import os
import bcrypt

# ------------------ ROUTER ------------------
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# ------------------ CONFIG ------------------
SECRET_KEY = "Sample_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
USERS_FILE = "users.json"

security = HTTPBearer()

# ------------------ MODELS ------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

# ------------------ FILE UTILS ------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)

    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ------------------ PASSWORD UTILS ------------------
def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

# ------------------ TOKEN UTILS ------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ------------------ DEPENDENCY ------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    return verify_token(credentials.credentials)

# ------------------ REGISTER ------------------
@auth_router.post("/register", response_model=TokenResponse)
async def register_user(user: UserRegister):

    users = load_users()

    if user.username in users:
        raise HTTPException(status_code=409, detail="Username already exists")

    users[user.username] = {
        "password": hash_password(user.password)
    }

    save_users(users)

    try:
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


# ------------------ LOGIN --------------------
@auth_router.post("/login", response_model=TokenResponse)
async def login_user(user: UserLogin):

    users = load_users()

    if user.username not in users:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(user.password, users[user.username]["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


