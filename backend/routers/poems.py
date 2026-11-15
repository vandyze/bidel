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

# --- Poem Routes ---

@router.get("/poems/ghazals")
def list_ghazals(db: Session = Depends(get_db)):
    ghazals = db.query(models.Ghazal).order_by(models.Ghazal.number).all()
    return [
        {"number": g.number, "title": g.title, "first_couplet": g.couplets[0] if g.couplets else []}
        for g in ghazals
    ]


@router.get("/poems/terjees")
def list_terjees(db: Session = Depends(get_db)):
    bands = db.query(models.Terjee).order_by(models.Terjee.number).all()
    return [
        {"number": b.number, "first_couplet": b.couplets[0] if b.couplets else []}
        for b in bands
    ]


@router.get("/poems/ghazal/random")
def random_ghazal(db: Session = Depends(get_db)):
    count = db.query(models.Ghazal).count()
    if not count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="داده‌ای یافت نشد")
    ghazal = db.query(models.Ghazal).offset(random.randint(0, count - 1)).first()
    return {"number": ghazal.number, "title": ghazal.title, "couplets": ghazal.couplets, "vazn": ghazal.vazn}


@router.get("/poems/ghazal/{number}")
def get_ghazal(number: int, db: Session = Depends(get_db)):
    ghazal = db.query(models.Ghazal).filter(models.Ghazal.number == number).first()
    if not ghazal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="غزل یافت نشد")
    return {"number": ghazal.number, "title": ghazal.title, "couplets": ghazal.couplets, "vazn": ghazal.vazn}


@router.get("/poems/terjee/{number}")
def get_terjee(number: int, db: Session = Depends(get_db)):
    band = db.query(models.Terjee).filter(models.Terjee.number == number).first()
    if not band:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="بند یافت نشد")
    return {"number": band.number, "couplets": band.couplets}


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _plain_text(source: str) -> str:
    """متن خالص از محتوای HTML خوانش‌ها، برای جست‌وجو و ساخت snippet."""
    text = _HTML_TAG_RE.sub(" ", source or "")
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _snippet_around(text: str, q: str, idx: int, pad: int = 40) -> str:
    start = max(0, idx - pad)
    end = min(len(text), idx + len(q) + pad)
    out = text[start:end]
    if start > 0:
        out = "…" + out
    if end < len(text):
        out = out + "…"
    return out


_POEM_CACHE = {"g": (0.0, []), "t": (0.0, [])}
_POEM_CACHE_TTL = 600


class _PoemRow:
    __slots__ = ("number", "title", "couplets")

    def __init__(self, number, title, couplets):
        self.number, self.title, self.couplets = number, title, couplets


def _cached_poems(kind, loader):
    ts, rows = _POEM_CACHE[kind]
    now = time.time()
    if rows and now - ts < _POEM_CACHE_TTL:
        return rows
    rows = loader()
    _POEM_CACHE[kind] = (now, rows)
    return rows


def _all_ghazals(db):
    return _cached_poems("g", lambda: [
        _PoemRow(g.number, g.title, g.couplets or [])
        for g in db.query(models.Ghazal).order_by(models.Ghazal.number).all()])


def _all_terjees(db):
    return _cached_poems("t", lambda: [
        _PoemRow(t.number, None, t.couplets or [])
        for t in db.query(models.Terjee).order_by(models.Terjee.number).all()])


@router.get("/poems/search")
def search_poems(
    q: str = Query(..., min_length=2),
    type: str = Query("g", pattern="^(g|t|z|kh)$"),
    db: Session = Depends(get_db),
):
    results = []
    q = q.replace("ي", "ی").replace("ك", "ک").strip()
    if len(q) < 2:
        return {"query": q, "count": 0, "results": []}
    if type == "g":
        ghazals = _all_ghazals(db)
        for ghazal in ghazals:
            matched = [
                {"couplet_index": ci, "couplet": c}
                for ci, c in enumerate(ghazal.couplets)
                if any(q in hemistich for hemistich in c)
            ]
            if matched:
                results.append({
                    "type": "g",
                    "number": ghazal.number,
                    "title": ghazal.title,
                    "matches": matched,
                })
    elif type == "t":
        bands = _all_terjees(db)
        for band in bands:
            matched = [
                {"couplet_index": ci, "couplet": c}
                for ci, c in enumerate(band.couplets)
                if any(q in hemistich for hemistich in c)
            ]
            if matched:
                results.append({
                    "type": "t",
                    "number": band.number,
                    "matches": matched,
                })
    elif type == "kh":
        # خوانش‌ها: عنوان، برچسب‌ها و متن مقاله. محتوا HTML است، پس روی متن خالص جست‌وجو می‌شود.
        items = (
            db.query(models.Khanesh)
            .order_by(models.Khanesh.published_at.desc().nullslast(), models.Khanesh.created_at.desc())
            .all()
        )
        for k in items:
            plain = _plain_text(k.content)
            title = k.title or ""
            tags = k.tags or []
            idx = plain.find(q)
            in_title = q in title
            in_tags = any(q in str(t) for t in tags)
            if idx == -1 and not in_title and not in_tags:
                continue
            if idx != -1:
                snippet = _snippet_around(plain, q, idx)
            else:
                snippet = plain[:90] + ("…" if len(plain) > 90 else "")
            results.append({
                "type": "kh",
                "slug": k.slug,
                "title": title,
                "terjee_number": k.terjee_number,
                "instructor": k.instructor,
                "tags": tags,
                "snippet": snippet,
                "count": plain.count(q),
                "published_at": k.published_at.isoformat() if k.published_at else None,
            })
    else:
        sections = db.query(models.Zand).filter(models.Zand.content.isnot(None)).all()
        for section in sections:
            content = section.content or ""
            idx = content.find(q)
            if idx == -1:
                continue
            start = max(0, idx - 40)
            end = min(len(content), idx + len(q) + 40)
            snippet = content[start:end].replace("\n", " ")
            if start > 0:
                snippet = "…" + snippet
            if end < len(content):
                snippet = snippet + "…"
            results.append({
                "type": "z",
                "number": section.number,
                "title": section.title,
                "snippet": snippet,
                "count": content.count(q),
            })
    return {"query": q, "count": len(results), "results": results}


@router.get("/poems/zand")
def list_zand(db: Session = Depends(get_db)):
    sections = db.query(models.Zand).order_by(models.Zand.number).all()
    return [
        {"number": z.number, "title": z.title, "type": z.type, "has_content": bool(z.content)}
        for z in sections
    ]


@router.get("/poems/zand/{number}")
def get_zand(number: int, db: Session = Depends(get_db)):
    section = db.query(models.Zand).filter(models.Zand.number == number).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="بخش یافت نشد")
    return {"number": section.number, "title": section.title, "type": section.type, "content": section.content}


@router.get("/poems/ghazal/{number}/html", include_in_schema=False)
def get_ghazal_html(number: int, request: Request, preview: int = 0, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "").lower()
    if not preview and not any(b in ua for b in BOT_AGENTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    ghazal = db.query(models.Ghazal).filter(models.Ghazal.number == number).first()
    if not ghazal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="غزل یافت نشد")

    first = ghazal.couplets[0] if ghazal.couplets else ["", ""]
    description = " / ".join(p for p in first if p)

    couplets_html = ""
    for i, (m1, m2) in enumerate(ghazal.couplets, 1):
        couplets_html += f'<div class="couplet"><p>{esc(m1)}</p>'
        if m2:
            couplets_html += f'<p class="m2">{esc(m2)}</p>'
        couplets_html += "</div>\n"

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>غزل {number} — {esc(ghazal.title)} | دیوان بیدل دهلوی</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="https://bideli.ir/ghazal/{number}">
<style>
  body{{font-family:serif;max-width:600px;margin:2rem auto;padding:0 1rem;direction:rtl;line-height:2}}
  .couplet{{margin-bottom:1.2rem;border-bottom:1px solid #eee;padding-bottom:0.8rem}}
  .m2{{color:#555}}
  h1{{font-size:1.4rem;margin-bottom:0.3rem}}
  .meta{{color:#888;font-size:0.9rem;margin-bottom:2rem}}
  .back{{display:block;margin-top:2rem;color:#5a7048}}
</style>
</head>
<body>
<h1>غزل {number} — {esc(ghazal.title)}</h1>
<div class="meta">دیوان بیدل دهلوی · {len(ghazal.couplets)} بیت{f' · وزن: {esc(ghazal.vazn)}' if ghazal.vazn else ''}</div>
<main>
{couplets_html}</main>
<a class="back" href="https://bideli.ir/ghazal/{number}">مشاهده در سایت بیدلی ←</a>
</body>
</html>"""

    return HTMLResponse(content=with_og(html))


@router.get("/poems/ghazal/{number}/keywords")
def get_ghazal_keywords(number: int, db: Session = Depends(get_db)):
    ghazal = db.query(models.Ghazal).filter(models.Ghazal.number == number).first()
    if not ghazal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="غزل یافت نشد")
    return [
        {
            "word": gk.keyword.word,
            "count": gk.count,
            "meaning": gk.keyword.meaning,
            "category": gk.keyword.category,
            "maqam": gk.keyword.maqam,
        }
        for gk in sorted(ghazal.keywords, key=lambda x: x.count, reverse=True)
    ]


@router.get("/poems/terjee/{number}/keywords")
def get_terjee_keywords(number: int, db: Session = Depends(get_db)):
    band = db.query(models.Terjee).filter(models.Terjee.number == number).first()
    if not band:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="بند یافت نشد")
    return [
        {
            "word": tk.keyword.word,
            "count": tk.count,
            "meaning": tk.keyword.meaning,
            "category": tk.keyword.category,
            "maqam": tk.keyword.maqam,
        }
        for tk in sorted(band.keywords, key=lambda x: x.count, reverse=True)
    ]


@router.get("/poems/verse-of-day")
def verse_of_day(db: Session = Depends(get_db)):
    total = db.query(models.Ghazal).count()
    if not total:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="داده‌ای یافت نشد")

    today = tehran_today()
    seed = today.year * 10000 + today.month * 100 + today.day
    ghazal_offset = seed % total
    ghazal = db.query(models.Ghazal).order_by(models.Ghazal.number).offset(ghazal_offset).first()

    couplet_index = seed % len(ghazal.couplets)
    couplet = ghazal.couplets[couplet_index]

    return {
        "poem_id": ghazal.id,
        "ghazal_number": ghazal.number,
        "ghazal_title": ghazal.title,
        "couplet_index": couplet_index,
        "text1": couplet[0] if len(couplet) > 0 else "",
        "text2": couplet[1] if len(couplet) > 1 else "",
    }
