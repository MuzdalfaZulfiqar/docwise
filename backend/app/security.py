import time

import bcrypt
import jwt

from .config import settings


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def create_token(user_id: str) -> str:
    exp = int(time.time()) + settings.jwt_expire_minutes * 60
    return jwt.encode({"sub": user_id, "exp": exp}, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> str:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])["sub"]
