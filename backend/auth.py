import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "your-secret-key-here" or len(SECRET_KEY) < 16:
    raise RuntimeError("SECRET_KEY تنظیم نشده یا ضعیف است (حداقل ۱۶ کاراکتر در backend/.env)")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 365  # 1 year (rolling: refreshed daily)


def generate_public_id() -> str:
    """شناسهٔ عمومیِ تصادفی کاربر؛ عدد ترتیبیِ دیتابیس را لو نمی‌دهد."""
    return "u" + secrets.token_hex(8)


def _pw_bytes(password: str) -> bytes:
    # bcrypt فقط ۷۲ بایت اول را می‌خواند؛ همان رفتار passlib برای سازگاری با هش‌های قبلی
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw_bytes(password), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(plain_password), hashed_password.encode("ascii"))
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    payload = data.copy()
    expire = expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["exp"] = datetime.now(timezone.utc) + expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
