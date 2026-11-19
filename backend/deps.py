"""وابستگی‌ها و ابزارهای مشترک بین routerها."""
import html as html_lib
import os
import re
from datetime import date, datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

import models
from auth import decode_access_token, generate_public_id
from database import SessionLocal

ADMIN_USER_ID = 1  # your user id

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))  # ایران ساعت تابستانی ندارد


def tehran_today() -> date:
    return datetime.now(IRAN_TZ).date()


PAJVAK_MEDIA_DIR = os.path.join("media", "pajvak")
os.makedirs(os.path.join(PAJVAK_MEDIA_DIR, "cover"), exist_ok=True)
os.makedirs(os.path.join(PAJVAK_MEDIA_DIR, "audio"), exist_ok=True)


# --- هفت مقام سلوک: نگاشت لاتین ↔ فارسی و رنگ (هماهنگ با MOODS فرانت) ---

MAQAM_COLORS = {
    "طلب": "#b0823e",
    "عشق": "#b0566a",
    "معرفت": "#6a7bb0",
    "استغنا": "#5d8f7e",
    "توحید": "#5d8f5d",
    "حیرت": "#7b6cae",
    "فنا": "#8a8076",
}
MAQAM_IDS = {
    "طلب": "talab",
    "عشق": "eshgh",
    "معرفت": "marefat",
    "استغنا": "esteghna",
    "توحید": "towhid",
    "حیرت": "heyrat",
    "فنا": "fana",
}
MAQAM_BY_ID = {v: k for k, v in MAQAM_IDS.items()}
MAQAM_NEUTRAL = "#9a9482"



bearer_scheme = HTTPBearer()


_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
_DESC_RE = re.compile(r'<meta name="description" content="(.*?)">', re.S)
_CANON_RE = re.compile(r'<link rel="canonical" href="(.*?)">', re.S)


def with_og(page: str) -> str:
    """تگ‌های Open Graph را از title/description/canonical صفحه می‌سازد (پیش‌نمایش تلگرام و واتس‌اپ)."""
    t, d, c = _TITLE_RE.search(page), _DESC_RE.search(page), _CANON_RE.search(page)
    if not (t and c):
        return page
    og = (f'<meta property="og:type" content="article">\n'
          f'<meta property="og:site_name" content="بیدلی">\n'
          f'<meta property="og:title" content="{t.group(1)}">\n'
          f'<meta property="og:url" content="{c.group(1)}">\n'
          f'<meta property="og:image" content="https://bideli.ir/assets/logo-lockup.png">\n'
          f'<meta property="og:image:width" content="1260">\n'
          f'<meta property="og:image:height" content="1260">\n'
          f'<meta property="og:locale" content="fa_IR">\n'
          f'<meta name="twitter:card" content="summary_large_image">\n'
          f'<meta name="twitter:title" content="{t.group(1)}">\n'
          f'<meta name="twitter:image" content="https://bideli.ir/assets/logo-lockup.png">\n')
    if d:
        og += f'<meta property="og:description" content="{d.group(1)}">\n'
        og += f'<meta name="twitter:description" content="{d.group(1)}">\n'
    return page.replace("</head>", og + "</head>", 1)


# --- Dependencies ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None or "purpose" in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توکن نامعتبر است")

    user = db.query(models.User).filter(models.User.public_id == str(payload.get("sub"))).first()
    # توکن‌های قدیمی، شناسهٔ عددی دارند؛ تا انقضای همان نشست پشتیبانی می‌شوند
    if user is None and str(payload.get("sub", "")).isdigit():
        user = db.query(models.User).filter(models.User.id == int(payload.get("sub"))).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="کاربر یافت نشد")
    if not user.public_id:
        user.public_id = generate_public_id()
        db.commit()
        db.refresh(user)
    # توکن‌های قدیمی فیلد ver ندارند و با نسخهٔ ۰ برابرند؛ خروج یا تغییر رمز نسخه را بالا می‌برد
    if int(payload.get("ver", 0)) != int(user.token_version or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نشست منقضی شده است")
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.id != ADMIN_USER_ID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی مجاز نیست")
    return current_user


def touch_activity(db, user_id: int):
    """ثبت یک ردیف «روز فعال» برای کاربر — بدون race condition (ON CONFLICT DO NOTHING)."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    today = tehran_today()
    try:
        stmt = pg_insert(models.UserActivity).values(user_id=user_id, date=today)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "date"])
        db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        exists = db.query(models.UserActivity).filter_by(user_id=user_id, date=today).first()
        if not exists:
            db.add(models.UserActivity(user_id=user_id, date=today))
            db.commit()




def esc(v) -> str:
    return html_lib.escape(str(v if v is not None else ""), quote=True)


BOT_AGENTS = ("googlebot", "bingbot", "facebookexternalhit", "twitterbot", "crawler", "spider", "bot")

