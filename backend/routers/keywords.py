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

# --- Keyword Routes ---
# NOTE: specific paths (/featured, /categories, /graph, /graph/{maqam}) must be
# defined before /keywords/{word}

_KW_NORM = {"t": 0.0, "map": {}}
_KW_NORM_TTL = 600


def _keyword_norm_map(db):
    now = time.time()
    if now - _KW_NORM["t"] > _KW_NORM_TTL or not _KW_NORM["map"]:
        _KW_NORM["map"] = {normalize(w): w for (w,) in db.query(models.Keyword.word).all()}
        _KW_NORM["t"] = now
    return _KW_NORM["map"]


def _find_keyword_by_norm(db, qnorm: str):
    if not qnorm:
        return None
    word = _keyword_norm_map(db).get(qnorm)
    if word is None:
        return None
    return db.query(models.Keyword).filter(models.Keyword.word == word).first()


def _keywords_by_ids(db, ids):
    ids = list(set(ids))
    if not ids:
        return {}
    return {k.id: k for k in db.query(models.Keyword).filter(models.Keyword.id.in_(ids)).all()}


def _example_bayt_text(word: str):
    """متن یک بیتِ نمونه که واژه را دارد (از ایندکس)."""
    toks = set(tokenize(word))
    if not toks:
        return ""
    plists = [neighbors_index.INDEX.postings.get(t) for t in toks]
    if any(p is None for p in plists):
        return ""
    matched = set.intersection(*plists)
    if not matched:
        return ""
    bid = min(matched)
    return neighbors_index.INDEX.bayts[bid]


# ── همسایه و گراف ────────────────────────────────────────────────────────

@router.get("/poems/neighbors")
def poems_neighbors(
    q: str = Query(..., min_length=2),
    type: str = Query("all", pattern="^(g|tr|all)$"),
    db: Session = Depends(get_db),
):
    if not neighbors_index.INDEX.ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="index building")

    qnorm = normalize(q)
    kw = _find_keyword_by_norm(db, qnorm)
    matched = matched_bayts(q)

    if kw is not None:
        rows = (
            db.query(models.KeywordCooccurrence)
            .filter(models.KeywordCooccurrence.keyword_a_id == kw.id)
            .order_by(models.KeywordCooccurrence.score.desc())
            .limit(5)
            .all()
        )
        neighbors = []
        others = _keywords_by_ids(db, [r.keyword_b_id for r in rows])
        for r in rows:
            other = others.get(r.keyword_b_id)
            if not other:
                continue
            neighbors.append({
                "word": other.word,
                "co": r.co_count,
                "score": r.score,
                "in_dictionary": True,
                "maqam": other.maqam,
                "example": _example_bayt_text(other.word),
            })
        return {"query": q, "source": "table", "matched_bayts": matched, "neighbors": neighbors}

    ns = cached_live_neighbors(qnorm, 5)
    neighbors = []
    for n in ns:
        nkw = _find_keyword_by_norm(db, normalize(n["word"]))
        neighbors.append({
            "word": n["word"],
            "co": n["co"],
            "score": n["score"],
            "in_dictionary": nkw is not None,
            "maqam": nkw.maqam if nkw else None,
            "example": _example_bayt_text(n["word"]),
        })
    return {"query": q, "source": "live", "matched_bayts": matched, "neighbors": neighbors}


@router.get("/keywords/{word}/neighbors")
def keyword_neighbors(
    word: str,
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    kw = db.query(models.Keyword).filter(models.Keyword.word == word).first()
    if not kw:
        raise HTTPException(status_code=404, detail="کلمه کلیدی یافت نشد")

    rows = (
        db.query(models.KeywordCooccurrence)
        .filter(models.KeywordCooccurrence.keyword_a_id == kw.id)
        .order_by(models.KeywordCooccurrence.score.desc())
        .limit(limit)
        .all()
    )
    neighbors = []
    others = _keywords_by_ids(db, [r.keyword_b_id for r in rows])
    for r in rows:
        other = others.get(r.keyword_b_id)
        if not other:
            continue
        color = MAQAM_COLORS.get(other.maqam) or MAQAM_NEUTRAL
        neighbors.append({
            "word": other.word,
            "co": r.co_count,
            "score": r.score,
            "maqam": other.maqam,
            "color": color,
        })
    return {"word": word, "neighbors": neighbors}


@router.get("/keywords/graph")
def keywords_graph(db: Session = Depends(get_db)):
    kw_maqam = {}
    maqam_counts = {}
    for k in db.query(models.Keyword).all():
        if k.maqam and k.maqam in MAQAM_IDS:
            kw_maqam[k.id] = MAQAM_IDS[k.maqam]
            maqam_counts[k.maqam] = maqam_counts.get(k.maqam, 0) + 1

    nodes = [
        {"id": mid, "label": persian, "color": MAQAM_COLORS[persian],
         "size": maqam_counts.get(persian, 0)}
        for persian, mid in MAQAM_IDS.items()
    ]

    edges = {}
    rows = db.query(models.KeywordCooccurrence).filter(
        models.KeywordCooccurrence.keyword_a_id < models.KeywordCooccurrence.keyword_b_id
    ).all()
    for r in rows:
        ma = kw_maqam.get(r.keyword_a_id)
        mb = kw_maqam.get(r.keyword_b_id)
        if not ma or not mb or ma == mb:
            continue
        key = (ma, mb) if ma < mb else (mb, ma)
        edges[key] = edges.get(key, 0) + r.co_count

    edge_list = [
        {"source": a, "target": b, "weight": w}
        for (a, b), w in edges.items()
    ]
    edge_list.sort(key=lambda e: -e["weight"])
    return {"nodes": nodes, "edges": edge_list}


@router.get("/keywords/graph/{maqam}")
def keywords_graph_maqam(maqam: str, db: Session = Depends(get_db)):
    persian = MAQAM_BY_ID.get(maqam)
    if not persian:
        raise HTTPException(status_code=404, detail="مقام یافت نشد")

    kws = db.query(models.Keyword).filter(models.Keyword.maqam == persian).all()
    kws.sort(key=lambda k: -(k.count or 0))
    top = kws[:10]
    word_by_id = {k.id: k.word for k in top}
    ids = {k.id for k in top}

    rows = db.query(models.KeywordCooccurrence).filter(
        models.KeywordCooccurrence.keyword_a_id < models.KeywordCooccurrence.keyword_b_id,
        models.KeywordCooccurrence.keyword_a_id.in_(ids),
        models.KeywordCooccurrence.keyword_b_id.in_(ids),
    ).all()
    edges = [
        {"source": word_by_id[r.keyword_a_id], "target": word_by_id[r.keyword_b_id],
         "weight": r.co_count}
        for r in rows
    ]
    edges.sort(key=lambda e: -e["weight"])

    deg = {}
    for e in edges:
        deg[e["source"]] = deg.get(e["source"], 0) + 1
        deg[e["target"]] = deg.get(e["target"], 0) + 1

    nodes = [
        {"word": k.word, "size": k.count or 0, "degree": deg.get(k.word, 0)}
        for k in top
    ]
    return {
        "maqam": maqam,
        "label": persian,
        "color": MAQAM_COLORS[persian],
        "nodes": nodes,
        "edges": edges,
    }


@router.get("/keywords/featured")
def get_featured_keywords(db: Session = Depends(get_db)):
    keywords = db.query(models.Keyword).order_by(models.Keyword.id).all()
    if not keywords:
        return []

    today = tehran_today()
    seed = today.year * 10000 + today.month * 100 + today.day
    rng = random.Random(seed)
    selected = rng.sample(keywords, min(6, len(keywords)))

    return [
        {
            "word": k.word,
            "count": k.count,
            "category": k.category,
            "meaning": k.meaning,
        }
        for k in selected
    ]


@router.get("/keywords/categories")
def get_keyword_categories(db: Session = Depends(get_db)):
    rows = db.query(models.Keyword.category, models.Keyword.maqam).all()
    categories = sorted({r.category for r in rows if r.category})
    maqams = sorted({r.maqam for r in rows if r.maqam})
    return {"categories": categories, "maqams": maqams}


@router.get("/keywords")
def list_keywords(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=250),
    category: str | None = Query(None),
    maqam: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Keyword)
    if category:
        q = q.filter(models.Keyword.category == category)
    if maqam:
        q = q.filter(models.Keyword.maqam == maqam)
    total = q.count()
    keywords = q.order_by(models.Keyword.word).offset((page - 1) * limit).limit(limit).all()
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "results": [
            {
                "word": k.word,
                "count": k.count,
                "percentage": k.percentage,
                "meaning": k.meaning,
                "category": k.category,
                "maqam": k.maqam,
                "contrast": k.contrast,
            }
            for k in keywords
        ],
    }


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(db: Session = Depends(get_db)):
    BASE = "https://bideli.ir"

    def url(loc, priority, changefreq="monthly"):
        return f"  <url>\n    <loc>{loc}</loc>\n    <changefreq>{changefreq}</changefreq>\n    <priority>{priority}</priority>\n  </url>"

    urls = []

    urls.append(url(f"{BASE}/",        "1.0", "weekly"))
    urls.append(url(f"{BASE}/ghazals", "0.9"))
    urls.append(url(f"{BASE}/terjee",  "0.8"))
    urls.append(url(f"{BASE}/keywords","0.8"))
    urls.append(url(f"{BASE}/zand",    "0.7"))
    urls.append(url(f"{BASE}/khanesh", "0.7", "weekly"))

    for (n,) in db.query(models.Ghazal.number).order_by(models.Ghazal.number).all():
        urls.append(url(f"{BASE}/ghazal/{n}", "0.8"))

    for (n,) in db.query(models.Terjee.number).order_by(models.Terjee.number).all():
        urls.append(url(f"{BASE}/terjee/{n}", "0.7"))

    for (slug,) in db.query(models.Pajvak.slug).filter(models.Pajvak.published_at.isnot(None)).order_by(models.Pajvak.slug).all():
        urls.append(url(f"{BASE}/pajvak/{quote(slug, safe='')}", "0.6"))

    zand_numbers = db.query(models.Zand.number).order_by(models.Zand.number).all()
    for (n,) in zand_numbers:
        urls.append(url(f"{BASE}/zand/{n}", "0.6"))

    keywords = db.query(models.Keyword.word).order_by(models.Keyword.word).all()
    for (word,) in keywords:
        urls.append(url(f"{BASE}/keywords/{quote(word, safe='')}", "0.7"))

    khanesh_slugs = db.query(models.Khanesh.slug).order_by(models.Khanesh.slug).all()
    for (slug,) in khanesh_slugs:
        urls.append(url(f"{BASE}/khanesh/{quote(slug, safe='')}", "0.7", "monthly"))

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls)
    xml += "\n</urlset>"
    return Response(content=xml, media_type="application/xml")


@router.get("/keywords/{word}/html", include_in_schema=False)
def get_keyword_html(word: str, request: Request, preview: int = 0, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "").lower()
    if not preview and not any(b in ua for b in BOT_AGENTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    kw = db.query(models.Keyword).filter(models.Keyword.word == word).first()
    if not kw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کلمه کلیدی یافت نشد")

    description = kw.meaning or f"واژه {word} در دیوان بیدل دهلوی"

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>{esc(word)} در دیوان بیدل دهلوی</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="https://bideli.ir/keywords/{quote(word, safe='')}">
<style>
  body{{font-family:serif;max-width:600px;margin:2rem auto;padding:0 1rem;direction:rtl;line-height:2}}
  h1{{font-size:1.6rem;margin-bottom:0.3rem}}
  .meta{{color:#888;font-size:0.9rem;margin-bottom:1.5rem}}
  .field{{margin-bottom:0.8rem}}
  .label{{color:#888;font-size:0.85rem}}
  .value{{font-size:1rem}}
  .meaning{{font-size:1.05rem;line-height:1.9;margin-bottom:1.5rem;border-right:3px solid #5a7048;padding-right:0.8rem}}
  .back{{display:block;margin-top:2rem;color:#5a7048}}
</style>
</head>
<body>
<h1>{esc(word)}</h1>
<div class="meta">دیوان بیدل دهلوی · {kw.count or 0} بار تکرار</div>
{"<div class='meaning'>" + esc(kw.meaning) + "</div>" if kw.meaning else ""}
<div class="field"><span class="label">مقام: </span><span class="value">{esc(kw.maqam or '—')}</span></div>
<div class="field"><span class="label">دسته‌بندی: </span><span class="value">{esc(kw.category or '—')}</span></div>
<div class="field"><span class="label">تعداد تکرار: </span><span class="value">{kw.count or 0}</span></div>
<a class="back" href="https://bideli.ir/keywords/{quote(word, safe='')}">مشاهده در سایت بیدلی ←</a>
</body>
</html>"""

    return HTMLResponse(content=with_og(html))


@router.get("/poems/terjee/{number}/html", include_in_schema=False)
def get_terjee_html(number: int, request: Request, preview: int = 0, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "").lower()
    if not preview and not any(b in ua for b in BOT_AGENTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    band = db.query(models.Terjee).filter(models.Terjee.number == number).first()
    if not band:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="بند یافت نشد")

    first = band.couplets[0] if band.couplets else ["", ""]
    description = " / ".join(p for p in first if p) or f"ترجیع‌بند شماره {number} از دیوان بیدل دهلوی"

    couplets_html = ""
    for m1, m2 in band.couplets:
        couplets_html += f'<div class="couplet"><p>{esc(m1)}</p>'
        if m2:
            couplets_html += f'<p class="m2">{esc(m2)}</p>'
        couplets_html += "</div>\n"

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>ترجیع‌بند {number} | دیوان بیدل دهلوی</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="https://bideli.ir/terjee/{number}">
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
<h1>ترجیع‌بند حیرت — بند {number}</h1>
<div class="meta">دیوان بیدل دهلوی · {len(band.couplets)} بیت</div>
<main>
{couplets_html}</main>
<a class="back" href="https://bideli.ir/terjee/{number}">مشاهده در سایت بیدلی ←</a>
</body>
</html>"""

    return HTMLResponse(content=with_og(html))


@router.get("/poems/zand/{number}/html", include_in_schema=False)
def get_zand_html(number: int, request: Request, preview: int = 0, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "").lower()
    if not preview and not any(b in ua for b in BOT_AGENTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    section = db.query(models.Zand).filter(models.Zand.number == number).first()
    if not section or not section.content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="بخش یافت نشد")

    description = section.content.strip().replace("\n", " ")[:200]

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>{esc(section.title)} — زند بیدل | دیوان بیدل دهلوی</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="https://bideli.ir/zand/{number}">
<style>
  body{{font-family:serif;max-width:600px;margin:2rem auto;padding:0 1rem;direction:rtl;line-height:2}}
  h1{{font-size:1.4rem;margin-bottom:0.3rem}}
  .meta{{color:#888;font-size:0.9rem;margin-bottom:2rem}}
  main{{white-space:pre-line}}
  .back{{display:block;margin-top:2rem;color:#5a7048}}
</style>
</head>
<body>
<h1>{esc(section.title)}</h1>
<div class="meta">زند بیدل · شرح شروین وکیلی بر دیوان بیدل دهلوی</div>
<main>{esc(section.content)}</main>
<a class="back" href="https://bideli.ir/zand/{number}">مشاهده در سایت بیدلی ←</a>
</body>
</html>"""

    return HTMLResponse(content=with_og(html))


@router.get("/khanesh/{slug}/html", include_in_schema=False)
def get_khanesh_html(slug: str, request: Request, preview: int = 0, db: Session = Depends(get_db)):
    ua = request.headers.get("user-agent", "").lower()
    if not preview and not any(b in ua for b in BOT_AGENTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    k = db.query(models.Khanesh).filter(models.Khanesh.slug == slug).first()
    if not k:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="خوانش یافت نشد")

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>{esc(k.title)} | خوانش‌های دیوان بیدل دهلوی</title>
<meta name="description" content="خوانشِ بندِ {k.terjee_number} ترجیع‌بند بیدل، به قلم {esc(k.instructor)}">
<link rel="canonical" href="https://bideli.ir/khanesh/{slug}">
<style>
  body{{font-family:serif;max-width:600px;margin:2rem auto;padding:0 1rem;direction:rtl;line-height:2}}
  h1{{font-size:1.4rem;margin-bottom:0.3rem}}
  .meta{{color:#888;font-size:0.9rem;margin-bottom:2rem}}
  .back{{display:block;margin-top:2rem;color:#5a7048}}
</style>
</head>
<body>
<h1>{esc(k.title)}</h1>
<div class="meta">ترجیع‌بند · بند {k.terjee_number} · به خوانشِ {esc(k.instructor)}</div>
<main>{sanitize_html(k.content)}</main>
<a class="back" href="https://bideli.ir/khanesh/{slug}">مشاهده در سایت بیدلی ←</a>
</body>
</html>"""

    return HTMLResponse(content=with_og(html))


def _find_matching_couplet(couplets, word):
    for c in couplets:
        if any(word in hemistich for hemistich in c):
            return c
    return couplets[0] if couplets else ["", ""]


@router.get("/keywords/{word}")
def get_keyword(word: str, db: Session = Depends(get_db)):
    kw = db.query(models.Keyword).filter(models.Keyword.word == word).first()
    if not kw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کلمه کلیدی یافت نشد")

    ghazals = [
        {
            "number": gk.ghazal.number,
            "title": gk.ghazal.title,
            "count": gk.count,
            "couplet": _find_matching_couplet(gk.ghazal.couplets, kw.word),
        }
        for gk in sorted(kw.ghazals, key=lambda x: x.count, reverse=True)
    ]
    terjees = [
        {
            "number": tk.terjee.number,
            "count": tk.count,
            "couplet": _find_matching_couplet(tk.terjee.couplets, kw.word),
        }
        for tk in sorted(kw.terjees, key=lambda x: x.count, reverse=True)
    ]

    return {
        "word": kw.word,
        "count": kw.count,
        "percentage": kw.percentage,
        "meaning": kw.meaning,
        "category": kw.category,
        "maqam": kw.maqam,
        "contrast": kw.contrast,
        "ghazals": ghazals,
        "terjees": terjees,
    }
