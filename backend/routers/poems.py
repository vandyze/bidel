import asyncio
import html as html_lib
import json
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


@router.get("/poems/chahar")
def list_chahar(db: Session = Depends(get_db)):
    sections = db.query(models.ChaharOnsor).order_by(models.ChaharOnsor.number).all()
    return [
        {"number": s.number, "title": s.title, "part": s.part,
         "type": s.type, "has_content": bool(s.content)}
        for s in sections
    ]


@router.get("/poems/chahar/html", include_in_schema=False)
def get_chahar_list_html(request: Request, preview: int = 0, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "").lower()
    if not preview and not any(b in ua for b in BOT_AGENTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    sections = db.query(models.ChaharOnsor).order_by(models.ChaharOnsor.number).all()
    if not sections:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کتاب یافت نشد")

    grouped = []
    current = object()
    for s in sections:
        part = s.part or ""
        if part != current:
            grouped.append((part, []))
            current = part
        grouped[-1][1].append(s)

    list_html = ""
    for part, items in grouped:
        if part:
            list_html += f"<h2>{esc(part)}</h2>\n"
        list_html += "<ul>\n"
        for s in items:
            list_html += f'<li><a href="/chahar/{s.number}">{esc(s.title)}</a></li>\n'
        list_html += "</ul>\n"

    description = "بازنویسی خودزندگینامهٔ بیدل دهلوی (چهار عنصر) به فارسی امروز؛ ۱۶۳ فصل، از دیباچه تا پایان عنصر چهارم."
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": "چهار عنصر",
        "alternateName": "خودزندگینامهٔ بیدل دهلوی",
        "author": {"@type": "Person", "name": "بیدل دهلوی",
                   "sameAs": ["https://fa.wikipedia.org/wiki/%D8%A8%DB%8C%D8%AF%D9%84_%D8%AF%D9%87%D9%84%D9%88%DB%8C",
                              "https://www.wikidata.org/wiki/Q2355593"]},
        "inLanguage": "fa",
        "url": "https://bideli.ir/chahar",
        "description": description,
    }

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>چهار عنصر — خودزندگینامهٔ بیدل دهلوی | دیوان بیدل</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="https://bideli.ir/chahar">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script type="application/ld+json">
{json.dumps(jsonld, ensure_ascii=False)}
</script>
<style>
  body{{font-family:serif;max-width:720px;margin:2rem auto;padding:0 1rem;direction:rtl;line-height:2}}
  h1{{font-size:1.8rem;margin-bottom:0.3rem}}
  h2{{font-size:1.2rem;margin-top:1.6rem;border-bottom:1px solid #ddd;padding-bottom:0.3rem}}
  ul{{padding-right:1.2rem}}
  li{{margin:0.3rem 0}}
  a{{color:#5a7048;text-decoration:none}}
  a:hover{{text-decoration:underline}}
  .meta{{color:#777;font-size:0.9rem;margin-bottom:1.4rem}}
  .back{{display:block;margin-top:2rem;color:#5a7048}}
</style>
</head>
<body>
<h1>چهار عنصر</h1>
<div class="meta">خودزندگینامهٔ بیدل دهلوی · بازنویسی به فارسی امروز · {len(sections)} فصل</div>
<main>
{list_html}</main>
<a class="back" href="https://bideli.ir/chahar">مشاهده در سایت بیدلی ←</a>
</body>
</html>"""

    return HTMLResponse(content=with_og(html))


@router.get("/poems/chahar/{number}/html", include_in_schema=False)
def get_chahar_html(number: int, request: Request, preview: int = 0, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "").lower()
    if not preview and not any(b in ua for b in BOT_AGENTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    section = db.query(models.ChaharOnsor).filter(models.ChaharOnsor.number == number).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="بخش یافت نشد")

    content = section.content or ""
    description = re.sub(r"<[^>]+>", " ", content)
    description = re.sub(r"\s+", " ", description).strip()[:160]
    part = section.part or ""
    title = (f"{section.title} — چهار عنصر | دیوان بیدل دهلوی")
    canonical = f"https://bideli.ir/chahar/{number}"
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Chapter",
        "name": section.title,
        "isPartOf": {"@type": "Book", "name": "چهار عنصر", "url": "https://bideli.ir/chahar"},
        "author": {"@type": "Person", "name": "بیدل دهلوی"},
        "inLanguage": "fa",
        "url": canonical,
    }

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script type="application/ld+json">
{json.dumps(jsonld, ensure_ascii=False)}
</script>
<style>
  body{{font-family:serif;max-width:720px;margin:2rem auto;padding:0 1rem;direction:rtl;line-height:2}}
  h1{{font-size:1.8rem;margin-bottom:0.3rem}}
  .meta{{color:#777;font-size:0.9rem;margin-bottom:1.4rem}}
  .content p{{margin-bottom:0.9rem}}
  .content h3{{font-size:1.2rem;margin:1.4rem 0 0.6rem}}
  .content h4{{font-size:1.05rem;margin:1.2rem 0 0.5rem;color:#5a7048}}
  .content h5{{font-size:1rem;margin:1rem 0 0.4rem;color:#5a7048}}
  .content blockquote{{margin:1rem 0;padding:0.6rem 1rem;border-right:3px solid #c89030;background:#f7f3e6}}
  .content blockquote em{{color:#777}}
  .back{{display:block;margin-top:2rem;color:#5a7048}}
</style>
</head>
<body>
<h1>{esc(section.title)}</h1>
<div class="meta">{esc(part) + ' · ' if part else ''}چهار عنصر · خودزندگینامهٔ بیدل دهلوی</div>
<main class="content">
{content}</main>
<a class="back" href="https://bideli.ir/chahar">بازگشت به فهرست چهار عنصر ←</a>
</body>
</html>"""

    return HTMLResponse(content=with_og(html))


@router.get("/poems/chahar/{number}")
def get_chahar(number: int, db: Session = Depends(get_db)):
    section = db.query(models.ChaharOnsor).filter(models.ChaharOnsor.number == number).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="بخش یافت نشد")
    return {"number": section.number, "title": section.title, "part": section.part,
            "type": section.type, "content": section.content}


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
