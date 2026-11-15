import asyncio
import html as html_lib
import os
import random
import re
import secrets
import shutil
import threading
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
from text_utils import normalize, tokenize
from deps import (
    ADMIN_USER_ID, BOT_AGENTS, IRAN_TZ, MAQAM_BY_ID, MAQAM_COLORS, MAQAM_IDS, MAQAM_NEUTRAL,
    PAJVAK_MEDIA_DIR, esc, get_current_user, get_db, require_admin, tehran_today,
    touch_activity, with_og,
)

router = APIRouter()

# ─── PAJVAK ────────────────────────────────────────────────────────────

PAJVAK_UPLOAD_EXT = {
    "cover": {".jpg", ".jpeg", ".png", ".webp"},
    "audio": {".mp3", ".ogg", ".wav", ".m4a"},
}

_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9_-]{1,64}\.[A-Za-z0-9]{1,5}$")


def _check_filename(v):
    if v is not None and not _SAFE_FILENAME.match(v):
        raise ValueError("invalid filename")
    return v


def _safe_remove(kind: str, filename: str):
    if not _SAFE_FILENAME.match(filename or ""):
        return
    try:
        os.remove(os.path.join(PAJVAK_MEDIA_DIR, kind, filename))
    except OSError:
        pass


class PajvakCredit(BaseModel):
    role: str
    name: str

class PajvakCreate(BaseModel):
    title: str
    slug: str
    ref_type: str  # beit | ghazal | band
    ref_ghazal_number: Optional[int] = None
    ref_beit_index: Optional[int] = None
    ref_terjee_number: Optional[int] = None
    cover_filename: Optional[str] = None
    audio_filename: Optional[str] = None
    audio_duration: Optional[int] = None
    video_url: Optional[str] = None
    poem: Optional[List[List[str]]] = None
    narrative: Optional[List[str]] = None
    credits: Optional[List[PajvakCredit]] = None
    published_at: Optional[datetime] = None

    @field_validator("cover_filename", "audio_filename")
    @classmethod
    def _v_filename(cls, v):
        return _check_filename(v)

    @field_validator("slug")
    @classmethod
    def _v_slug(cls, v):
        if not re.match(r"^[\w-]{1,100}$", v):
            raise ValueError("invalid slug")
        return v


def _pajvak_ref_info(p: models.Pajvak, db: Session):
    """برچسب و متن بیتِ مرجعِ یک پژواک را برمی‌گرداند."""
    if p.ref_type == "beit" and p.ref_ghazal_number is not None and p.ref_beit_index is not None:
        g = db.query(models.Ghazal).filter(models.Ghazal.number == p.ref_ghazal_number).first()
        v = g.couplets[p.ref_beit_index] if g and g.couplets and p.ref_beit_index < len(g.couplets) else ["", ""]
        return {
            "type": "beit", "ghazal_number": p.ref_ghazal_number, "beit_index": p.ref_beit_index,
            "label": f"غزل {p.ref_ghazal_number}، بیت {p.ref_beit_index + 1}", "verse": v,
        }
    if p.ref_type == "ghazal" and p.ref_ghazal_number is not None:
        g = db.query(models.Ghazal).filter(models.Ghazal.number == p.ref_ghazal_number).first()
        v = g.couplets[0] if g and g.couplets else ["", ""]
        return {
            "type": "ghazal", "ghazal_number": p.ref_ghazal_number, "beit_index": None,
            "label": f"غزل {p.ref_ghazal_number}", "verse": v,
        }
    if p.ref_type == "band" and p.ref_terjee_number is not None:
        t = db.query(models.Terjee).filter(models.Terjee.number == p.ref_terjee_number).first()
        v = t.couplets[0] if t and t.couplets else ["", ""]
        return {
            "type": "band", "terjee_number": p.ref_terjee_number, "beit_index": None,
            "label": f"ترجیع‌بند، بند {p.ref_terjee_number}", "verse": v,
        }
    return {"type": p.ref_type, "label": "", "verse": ["", ""]}


def _pajvak_summary(p: models.Pajvak, db: Session):
    return {
        "id": p.id,
        "slug": p.slug,
        "title": p.title,
        "ref": _pajvak_ref_info(p, db),
        "cover_url": f"/media/pajvak/cover/{p.cover_filename}" if p.cover_filename else None,
        "has_audio": bool(p.audio_filename),
        "audio_url": f"/media/pajvak/audio/{p.audio_filename}" if p.audio_filename else None,
        "audio_duration": p.audio_duration,
        "has_video": bool(p.video_url),
        "has_poem": bool(p.poem),
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _pajvak_detail(p: models.Pajvak, db: Session):
    d = _pajvak_summary(p, db)
    d.update({
        "audio_url": f"/media/pajvak/audio/{p.audio_filename}" if p.audio_filename else None,
        "video_url": p.video_url,
        "poem": p.poem,
        "narrative": p.narrative,
        "credits": p.credits or [],
    })
    return d


@router.get("/pajvak")
def get_pajvak_list(db: Session = Depends(get_db)):
    items = db.query(models.Pajvak).order_by(models.Pajvak.published_at.desc().nullslast(), models.Pajvak.created_at.desc()).all()
    return [_pajvak_summary(p, db) for p in items]


@router.get("/pajvak/ghazal/{number}")
def get_pajvak_for_ghazal(number: int, db: Session = Depends(get_db)):
    items = db.query(models.Pajvak).filter(
        models.Pajvak.ref_type.in_(["beit", "ghazal"]),
        models.Pajvak.ref_ghazal_number == number,
    ).order_by(models.Pajvak.published_at.desc().nullslast()).all()
    return [_pajvak_summary(p, db) for p in items]


@router.get("/pajvak/terjee/{number}")
def get_pajvak_for_terjee(number: int, db: Session = Depends(get_db)):
    items = db.query(models.Pajvak).filter(
        models.Pajvak.ref_type == "band",
        models.Pajvak.ref_terjee_number == number,
    ).order_by(models.Pajvak.published_at.desc().nullslast()).all()
    return [_pajvak_summary(p, db) for p in items]


@router.get("/pajvak/{slug}/html", include_in_schema=False)
def get_pajvak_html(slug: str, request: Request, preview: int = 0, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "").lower()
    if not preview and not any(b in ua for b in BOT_AGENTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    p = db.query(models.Pajvak).filter(models.Pajvak.slug == slug).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="پژواک یافت نشد")

    ref = _pajvak_ref_info(p, db)
    poem_html = "".join(f"<p>{esc(a)}<br>{esc(b)}</p>" for a, b in (p.poem or []))
    narrative_html = "".join(f"<p>{esc(para)}</p>" for para in (p.narrative or []))

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>{esc(p.title)} | پژواک‌های دیوان بیدل دهلوی</title>
<meta name="description" content="اثری الهام‌گرفته از {esc(ref['label'])} بیدل دهلوی">
<link rel="canonical" href="https://bideli.ir/pajvak/{slug}">
<style>
  body{{font-family:serif;max-width:600px;margin:2rem auto;padding:0 1rem;direction:rtl;line-height:2}}
  h1{{font-size:1.4rem;margin-bottom:0.3rem}}
  .meta{{color:#888;font-size:0.9rem;margin-bottom:2rem}}
  .back{{display:block;margin-top:2rem;color:#5a7048}}
</style>
</head>
<body>
<h1>{esc(p.title)}</h1>
<div class="meta">الهام از بیدل · {esc(ref['label'])}</div>
<main>{poem_html}{narrative_html}</main>
<a class="back" href="https://bideli.ir/pajvak/{slug}">مشاهده در سایت بیدلی ←</a>
</body>
</html>"""

    return HTMLResponse(content=with_og(html))


@router.get("/pajvak/{slug}")
def get_pajvak(slug: str, db: Session = Depends(get_db)):
    p = db.query(models.Pajvak).filter(models.Pajvak.slug == slug).first()
    if not p:
        raise HTTPException(status_code=404, detail="not found")
    return _pajvak_detail(p, db)


@router.post("/pajvak")
def create_pajvak(
    data: PajvakCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    existing = db.query(models.Pajvak).filter(models.Pajvak.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="slug already exists")
    p = models.Pajvak(
        title=data.title,
        slug=data.slug,
        ref_type=data.ref_type,
        ref_ghazal_number=data.ref_ghazal_number,
        ref_beit_index=data.ref_beit_index,
        ref_terjee_number=data.ref_terjee_number,
        cover_filename=data.cover_filename,
        audio_filename=data.audio_filename,
        audio_duration=data.audio_duration,
        video_url=data.video_url,
        poem=data.poem,
        narrative=data.narrative,
        credits=[c.dict() for c in data.credits] if data.credits else None,
        published_at=data.published_at,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"status": "ok", "id": p.id, "slug": p.slug}


@router.put("/pajvak/{slug}")
def update_pajvak(
    slug: str,
    data: PajvakCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    p = db.query(models.Pajvak).filter(models.Pajvak.slug == slug).first()
    if not p:
        raise HTTPException(status_code=404, detail="not found")
    p.title = data.title
    p.slug = data.slug
    p.ref_type = data.ref_type
    p.ref_ghazal_number = data.ref_ghazal_number
    p.ref_beit_index = data.ref_beit_index
    p.ref_terjee_number = data.ref_terjee_number
    p.cover_filename = data.cover_filename
    p.audio_filename = data.audio_filename
    p.audio_duration = data.audio_duration
    p.video_url = data.video_url
    p.poem = data.poem
    p.narrative = data.narrative
    p.credits = [c.dict() for c in data.credits] if data.credits else None
    if data.published_at is not None:
        p.published_at = data.published_at
    db.commit()
    return {"status": "ok"}


@router.delete("/pajvak/{slug}")
def delete_pajvak(
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    p = db.query(models.Pajvak).filter(models.Pajvak.slug == slug).first()
    if not p:
        raise HTTPException(status_code=404, detail="not found")
    if p.cover_filename:
        _safe_remove("cover", p.cover_filename)
    if p.audio_filename:
        _safe_remove("audio", p.audio_filename)
    db.delete(p)
    db.commit()
    return {"status": "ok"}


@router.post("/pajvak/upload")
async def upload_pajvak_media(
    kind: str = Query(...),
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_admin)
):
    if kind not in PAJVAK_UPLOAD_EXT:
        raise HTTPException(status_code=400, detail="invalid kind")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in PAJVAK_UPLOAD_EXT[kind]:
        raise HTTPException(status_code=400, detail="invalid file type")
    fname = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(PAJVAK_MEDIA_DIR, kind, fname)
    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out)
    return {"filename": fname, "url": f"/media/pajvak/{kind}/{fname}"}
