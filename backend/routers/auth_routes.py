import asyncio
import html as html_lib
import os
import random
import re
import secrets
import shutil
import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import neighbors_index
import soluk
from auth import hash_password, verify_password, create_access_token, decode_access_token
from neighbors_index import cached_live_neighbors, matched_bayts
from sanitize import sanitize_html
from timeutil import utcnow
from text_utils import normalize, tokenize
from deps import (
    ADMIN_USER_ID, BOT_AGENTS, IRAN_TZ, MAQAM_BY_ID, MAQAM_COLORS, MAQAM_IDS, MAQAM_NEUTRAL,
    PAJVAK_MEDIA_DIR, esc, get_current_user, get_db, require_admin, tehran_today,
    touch_activity, with_og,
)

router = APIRouter()


def user_token(user: models.User) -> str:
    return create_access_token({"sub": str(user.id), "ver": int(user.token_version or 0)})

# --- Telegram Notification ---

async def notify_telegram(msg: str):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg}
            )
    except Exception as e:
        print(f"[telegram] failed: {e}", flush=True)

# ── کاوه‌نگار SMS ──
SMS_IR_API_KEY = os.getenv("SMS_IR_API_KEY", "")
SMS_IR_TEMPLATE_ID = int(os.getenv("SMS_IR_TEMPLATE_ID", "0"))

async def send_sms_otp(phone: str, code: str):
    import sys
    if not SMS_IR_API_KEY:
        print(f"[OTP] {phone} → {code}", flush=True)
        sys.stdout.flush()
        return
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://api.sms.ir/v1/send/verify",
            headers={"x-api-key": SMS_IR_API_KEY, "Content-Type": "application/json"},
            json={
                "mobile": phone.lstrip('0'),
                "templateId": SMS_IR_TEMPLATE_ID,
                "parameters": [{"name": "OTP", "value": code}]
            }
        )
        if resp.status_code >= 400:
            print(f"[sms] send failed: {resp.status_code} {resp.text[:200]}", flush=True)
            raise HTTPException(status_code=502, detail="ارسال پیامک ناموفق بود")

def gen_otp() -> str:
    return str(secrets.randbelow(90000) + 10000)

def validate_phone(phone: str) -> bool:
    return bool(re.match(r'^09\d{9}$', phone))


# --- Schemas ---

class SendOTPInput(BaseModel):
    phone: str
    purpose: str  # 'register' | 'login' | 'reset'

class VerifyOTPInput(BaseModel):
    phone: str
    code: str
    purpose: str

class RegisterWithOTPInput(BaseModel):
    name: str
    username: str
    phone: str
    password: str
    otp_token: str  # JWT کوتاه‌مدت که بعد از verify برگشت

class ResetPasswordInput(BaseModel):
    phone: str
    new_password: str
    otp_token: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    login_id: str  # username | email | phone
    password: str

class UpdateMeRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    current_password: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone: Optional[str] = None
    created_at: str
    access_token: Optional[str] = None  # فقط بعد از تغییر رمز پر می‌شود

    class Config:
        from_attributes = True


# --- Routes ---

@router.get("/")
def root():
    return {"message": "سلام از بیدل API"}


@router.post("/auth/send-otp")
async def send_otp(data: SendOTPInput, db: Session = Depends(get_db)):
    if not validate_phone(data.phone):
        raise HTTPException(status_code=400, detail="شماره تلفن معتبر نیست")

    # بررسی rate limit: حداکثر ۵ بار در ۱۰ دقیقه
    ten_min_ago = utcnow() - timedelta(minutes=10)
    recent_count = db.query(models.OTPCode).filter(
        models.OTPCode.phone == data.phone,
        models.OTPCode.created_at > ten_min_ago
    ).count()
    if recent_count >= 5:
        raise HTTPException(status_code=429, detail="تعداد درخواست‌های OTP بیش از حد مجاز است")

    # بررسی شرایط خاص purpose
    if data.purpose == "register":
        existing = db.query(models.User).filter(models.User.phone == data.phone).first()
        if existing:
            raise HTTPException(status_code=400, detail="این شماره قبلاً ثبت شده است")
    elif data.purpose in ("login", "reset"):
        user = db.query(models.User).filter(models.User.phone == data.phone).first()
        if not user:
            raise HTTPException(status_code=404, detail="این شماره در سیستم ثبت نشده است")

    db.query(models.OTPCode).filter(
        models.OTPCode.created_at < utcnow() - timedelta(days=1)
    ).delete(synchronize_session=False)

    code = gen_otp()
    expires = utcnow() + timedelta(minutes=2)
    otp = models.OTPCode(phone=data.phone, code=code, purpose=data.purpose, expires_at=expires)
    db.add(otp)
    db.commit()

    await send_sms_otp(data.phone, code)
    return {"status": "sent"}


@router.post("/auth/verify-otp")
def verify_otp(data: VerifyOTPInput, db: Session = Depends(get_db)):
    otp = db.query(models.OTPCode).filter(
        models.OTPCode.phone == data.phone,
        models.OTPCode.purpose == data.purpose,
        models.OTPCode.used == False
    ).order_by(models.OTPCode.created_at.desc()).first()

    if not otp:
        raise HTTPException(status_code=400, detail="کد OTP پیدا نشد. دوباره درخواست دهید")
    if utcnow() > otp.expires_at:
        raise HTTPException(status_code=400, detail="کد منقضی شده است")
    if otp.attempts >= 3:
        raise HTTPException(status_code=400, detail="کد باطل شده است. دوباره ارسال کنید")
    if otp.code != data.code:
        otp.attempts += 1
        db.commit()
        remaining = 3 - otp.attempts
        if remaining <= 0:
            raise HTTPException(status_code=400, detail="کد باطل شد؛ دوباره ارسال کنید")
        raise HTTPException(status_code=400, detail=f"کد اشتباه است. {remaining} تلاش باقی مانده")

    otp.used = True
    db.commit()

    otp_token = create_access_token({"sub": data.phone, "purpose": data.purpose}, expires_delta=timedelta(minutes=10))
    return {"otp_token": otp_token}


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterWithOTPInput, db: Session = Depends(get_db)):
    # تأیید otp_token
    try:
        payload = decode_access_token(data.otp_token)
        if payload is None or payload.get("purpose") != "register" or payload.get("sub") != data.phone:
            raise HTTPException(status_code=400, detail="توکن نامعتبر")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="توکن منقضی یا نامعتبر")

    if not data.name.strip():
        raise HTTPException(status_code=400, detail="نام الزامی است")
    if not data.username.strip():
        raise HTTPException(status_code=400, detail="نام کاربری الزامی است")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="رمز عبور حداقل ۶ کاراکتر")

    existing = db.query(models.User).filter(
        (models.User.username == data.username) | (models.User.phone == data.phone)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="نام کاربری یا شماره قبلاً ثبت شده")

    user = models.User(
        name=data.name,
        username=data.username,
        email=f"{data.username}@phone.local",
        phone=data.phone,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    await notify_telegram(f"ثبت‌نام جدید: {data.username} | {data.phone}")

    token = user_token(user)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/reset-password")
def reset_password(data: ResetPasswordInput, db: Session = Depends(get_db)):
    try:
        payload = decode_access_token(data.otp_token)
        if payload is None or payload.get("purpose") != "reset" or payload.get("sub") != data.phone:
            raise HTTPException(status_code=400, detail="توکن نامعتبر")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="توکن منقضی یا نامعتبر")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="رمز عبور حداقل ۶ کاراکتر")

    user = db.query(models.User).filter(models.User.phone == data.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربر پیدا نشد")

    user.hashed_password = hash_password(data.new_password)
    user.token_version = int(user.token_version or 0) + 1
    db.commit()

    token = user_token(user)
    return {"access_token": token, "token_type": "bearer"}


_LOGIN_FAILS = {}  # (ip, login_id) -> [timestamps]
_LOGIN_MAX = 8
_LOGIN_WINDOW = 600


def _login_throttled(key) -> bool:
    now = time.time()
    hits = [t for t in _LOGIN_FAILS.get(key, []) if now - t < _LOGIN_WINDOW]
    _LOGIN_FAILS[key] = hits
    return len(hits) >= _LOGIN_MAX


@router.post("/auth/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "")
    key = (ip, body.login_id)
    if _login_throttled(key):
        raise HTTPException(status_code=429, detail="تلاش‌های ناموفق زیاد است؛ چند دقیقه بعد دوباره امتحان کنید")
    user = db.query(models.User).filter(
        (models.User.username == body.login_id) |
        (models.User.email == body.login_id) |
        (models.User.phone == body.login_id)
    ).first()
    if not user or not verify_password(body.password, user.hashed_password):
        _LOGIN_FAILS.setdefault(key, []).append(time.time())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="اطلاعات ورود اشتباه است")
    _LOGIN_FAILS.pop(key, None)

    token = user_token(user)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/login-otp")
def login_otp(data: VerifyOTPInput, db: Session = Depends(get_db)):
    otp = db.query(models.OTPCode).filter(
        models.OTPCode.phone == data.phone,
        models.OTPCode.purpose == "login",
        models.OTPCode.used == False
    ).order_by(models.OTPCode.created_at.desc()).first()

    if not otp or utcnow() > otp.expires_at:
        raise HTTPException(status_code=400, detail="کد منقضی شده یا پیدا نشد")
    if otp.attempts >= 3:
        raise HTTPException(status_code=400, detail="کد باطل شده است")
    if otp.code != data.code:
        otp.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="کد اشتباه است")

    otp.used = True
    db.commit()

    user = db.query(models.User).filter(models.User.phone == data.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربر پیدا نشد")

    token = user_token(user)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me", response_model=UserResponse)
def me(current_user: models.User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        created_at=current_user.created_at.isoformat(),
    )


@router.put("/auth/me", response_model=UserResponse)
def update_me(
    body: UpdateMeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    password_changed = False
    if body.username and body.username != current_user.username:
        if db.query(models.User).filter(models.User.username == body.username).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این نام کاربری قبلاً ثبت شده")
        current_user.username = body.username

    if body.email and body.email != current_user.email:
        if db.query(models.User).filter(models.User.email == body.email).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این ایمیل قبلاً ثبت شده")
        current_user.email = body.email

    if body.password:
        if not body.current_password or not verify_password(body.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="رمز عبور فعلی اشتباه است")
        if len(body.password) < 6:
            raise HTTPException(status_code=400, detail="رمز عبور حداقل ۶ کاراکتر")
        current_user.hashed_password = hash_password(body.password)
        current_user.token_version = int(current_user.token_version or 0) + 1
        password_changed = True

    db.commit()
    db.refresh(current_user)
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        created_at=current_user.created_at.isoformat(),
        access_token=user_token(current_user) if password_changed else None,
    )


@router.post("/auth/logout")
def logout(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # همهٔ توکن‌های قبلی این کاربر (روی همهٔ دستگاه‌ها) باطل می‌شوند
    current_user.token_version = int(current_user.token_version or 0) + 1
    db.commit()
    return {"message": "خروج موفق"}


@router.post("/auth/refresh")
def refresh(current_user: models.User = Depends(get_current_user)):
    """تمدید نشست: توکن جدید با ۷ روز اعتبار تازه."""
    return {"access_token": user_token(current_user), "token_type": "bearer"}
