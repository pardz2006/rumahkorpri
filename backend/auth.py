import os
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr
from bson import ObjectId

from db import db, clean

JWT_ALGORITHM = "HS256"

ROLES = {"consumer", "admin_korpri", "admin_developer", "btn_evaluator"}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Tidak terautentikasi")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User tidak ditemukan")
        if user.get("disabled"):
            raise HTTPException(status_code=403, detail="Akun Anda dinonaktifkan. Hubungi Admin KORPRI.")
        return clean(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token kedaluwarsa")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token tidak valid")


async def get_optional_user(request: Request) -> dict | None:
    """Like get_current_user but returns None instead of raising when unauthenticated."""
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        return clean(user) if user else None
    except Exception:
        return None


def require_roles(*roles):
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Akses ditolak untuk peran ini")
        return user
    return checker


router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterInput(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    nik: str | None = None
    instansi: str | None = None
    monthly_income: float | None = None
    city: str | None = None
    province: str | None = None


class LoginInput(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
async def register(inp: RegisterInput):
    email = inp.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    doc = {
        "name": inp.name,
        "email": email,
        "password_hash": hash_password(inp.password),
        "role": "consumer",
        "phone": inp.phone,
        "nik": inp.nik,
        "instansi": inp.instansi,
        "monthly_income": inp.monthly_income,
        "city": inp.city,
        "province": inp.province,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.users.insert_one(doc)
    user = await db.users.find_one({"_id": res.inserted_id})
    token = create_access_token(str(res.inserted_id), email, "consumer")
    return {"token": token, "user": clean(user)}


@router.post("/login")
async def login(inp: LoginInput):
    email = inp.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(inp.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    if user.get("disabled"):
        raise HTTPException(status_code=403, detail="Akun Anda dinonaktifkan. Hubungi Admin KORPRI.")
    token = create_access_token(str(user["_id"]), email, user["role"])
    return {"token": token, "user": clean(user)}


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(inp: ChangePasswordInput, user: dict = Depends(get_current_user)):
    if len(inp.new_password) < 6:
        raise HTTPException(status_code=400, detail="Kata sandi baru minimal 6 karakter")
    doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not doc or not verify_password(inp.current_password, doc["password_hash"]):
        raise HTTPException(status_code=400, detail="Kata sandi saat ini salah")
    await db.users.update_one({"_id": ObjectId(user["id"])},
                              {"$set": {"password_hash": hash_password(inp.new_password)}})
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
