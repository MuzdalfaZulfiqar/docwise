import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from .. import db
from ..config import settings
from ..deps import current_user
from ..security import create_token, hash_password, verify_password
from ..services.quotas import tokens_used_today

router = APIRouter(prefix="/auth", tags=["auth"])


class Creds(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


@router.post("/register", status_code=201)
async def register(c: Creds):
    if not settings.allow_registration:
        raise HTTPException(403, "Sign-ups are closed on this demo. Use the demo account listed in the README.")
    try:
        uid = await db.pool.fetchval(
            "INSERT INTO users (email, password_hash, daily_token_quota, max_documents) VALUES ($1,$2,$3,$4) RETURNING id",
            c.email.lower(), hash_password(c.password), settings.default_daily_token_quota, settings.default_max_documents)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Email already registered")
    return {"token": create_token(str(uid))}


@router.post("/login")
async def login(c: Creds):
    row = await db.pool.fetchrow("SELECT id, password_hash FROM users WHERE email = $1", c.email.lower())
    if not row or not verify_password(c.password, row["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    return {"token": create_token(str(row["id"]))}


@router.get("/me")
async def me(user: dict = Depends(current_user)):
    used = await tokens_used_today(user["id"])
    return {"id": str(user["id"]), "email": user["email"],
            "daily_token_quota": user["daily_token_quota"], "tokens_used_today": used}
