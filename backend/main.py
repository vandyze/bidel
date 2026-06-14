import asyncio
import os
import random as random_module
from datetime import date, datetime
from typing import List, Optional
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
import models
from auth import hash_password, verify_password, create_access_token, decode_access_token

Base.metadata.create_all(bind=engine)

ADMIN_USER_ID = 1  # your user id

app = FastAPI()


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
    except:
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer()


# --- Schemas ---

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UpdateMeRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: str

    class Config:
        from_attributes = True


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
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توکن نامعتبر است")

    user = db.query(models.User).filter(models.User.id == payload.get("sub")).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="کاربر یافت نشد")
    return user


# --- Routes ---

@app.get("/")
def root():
    return {"message": "سلام از بیدل API"}


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این ایمیل قبلاً ثبت شده")
    if db.query(models.User).filter(models.User.username == body.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این نام کاربری قبلاً ثبت شده")

    user = models.User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    asyncio.create_task(notify_telegram(f"🎉 کاربر جدید: {user.username}\nایمیل: {user.email}"))
    return {"message": "ثبت‌نام با موفقیت انجام شد", "user_id": user.id}


@app.post("/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ایمیل یا رمز عبور اشتباه است")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse)
def me(current_user: models.User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at.isoformat(),
    )


@app.put("/auth/me", response_model=UserResponse)
def update_me(
    body: UpdateMeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if body.username and body.username != current_user.username:
        if db.query(models.User).filter(models.User.username == body.username).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این نام کاربری قبلاً ثبت شده")
        current_user.username = body.username

    if body.email and body.email != current_user.email:
        if db.query(models.User).filter(models.User.email == body.email).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="این ایمیل قبلاً ثبت شده")
        current_user.email = body.email

    if body.password:
        current_user.hashed_password = hash_password(body.password)

    db.commit()
    db.refresh(current_user)
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at.isoformat(),
    )


@app.post("/auth/logout")
def logout(current_user: models.User = Depends(get_current_user)):
    return {"message": "خروج موفق"}


# --- Bookmark Schemas ---

class BookmarkRequest(BaseModel):
    poem_type: str
    poem_id: int
    couplet_index: int | None = None

class BookmarkResponse(BaseModel):
    id: int
    poem_type: str
    poem_id: int
    couplet_index: int | None
    created_at: str


# --- Bookmark Routes ---

@app.post("/bookmarks", status_code=status.HTTP_200_OK)
def toggle_bookmark(
    body: BookmarkRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    existing = db.query(models.Bookmark).filter(
        models.Bookmark.user_id == current_user.id,
        models.Bookmark.poem_type == body.poem_type,
        models.Bookmark.poem_id == body.poem_id,
        models.Bookmark.couplet_index == body.couplet_index,
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"action": "removed"}

    bookmark = models.Bookmark(
        user_id=current_user.id,
        poem_type=body.poem_type,
        poem_id=body.poem_id,
        couplet_index=body.couplet_index,
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return {"action": "added", "id": bookmark.id}


@app.delete("/bookmarks/{poem_type}/{poem_id}/{couplet_index}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    poem_type: str,
    poem_id: int,
    couplet_index: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    bookmark = db.query(models.Bookmark).filter(
        models.Bookmark.user_id == current_user.id,
        models.Bookmark.poem_type == poem_type,
        models.Bookmark.poem_id == poem_id,
        models.Bookmark.couplet_index == couplet_index,
    ).first()
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="بوکمارک یافت نشد")
    db.delete(bookmark)
    db.commit()


@app.get("/bookmarks", response_model=list[BookmarkResponse])
def get_bookmarks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    bookmarks = db.query(models.Bookmark).filter(models.Bookmark.user_id == current_user.id).all()
    return [
        BookmarkResponse(
            id=b.id,
            poem_type=b.poem_type,
            poem_id=b.poem_id,
            couplet_index=b.couplet_index,
            created_at=b.created_at.isoformat(),
        )
        for b in bookmarks
    ]


# --- Note Schemas ---

class NoteRequest(BaseModel):
    poem_type: str
    poem_id: int
    couplet_index: int | None = None
    text: str

class NoteResponse(BaseModel):
    id: int
    poem_type: str
    poem_id: int
    couplet_index: int | None
    text: str
    created_at: str


# --- Note Routes ---

@app.post("/notes", status_code=status.HTTP_200_OK)
def upsert_note(
    body: NoteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    existing = db.query(models.Note).filter(
        models.Note.user_id == current_user.id,
        models.Note.poem_type == body.poem_type,
        models.Note.poem_id == body.poem_id,
        models.Note.couplet_index == body.couplet_index,
    ).first()

    if existing:
        existing.text = body.text
        db.commit()
        db.refresh(existing)
        return {"action": "updated", "id": existing.id}

    note = models.Note(
        user_id=current_user.id,
        poem_type=body.poem_type,
        poem_id=body.poem_id,
        couplet_index=body.couplet_index,
        text=body.text,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"action": "created", "id": note.id}


@app.delete("/notes/{poem_type}/{poem_id}/{couplet_index}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    poem_type: str,
    poem_id: int,
    couplet_index: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    note = db.query(models.Note).filter(
        models.Note.user_id == current_user.id,
        models.Note.poem_type == poem_type,
        models.Note.poem_id == poem_id,
        models.Note.couplet_index == couplet_index,
    ).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="یادداشت یافت نشد")
    db.delete(note)
    db.commit()


@app.get("/notes", response_model=list[NoteResponse])
def get_notes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    notes = db.query(models.Note).filter(models.Note.user_id == current_user.id).all()
    return [
        NoteResponse(
            id=n.id,
            poem_type=n.poem_type,
            poem_id=n.poem_id,
            couplet_index=n.couplet_index,
            text=n.text,
            created_at=n.created_at.isoformat(),
        )
        for n in notes
    ]


# --- History Routes ---

@app.post("/history/ghazal/{number}")
def record_ghazal_view(
    number: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ghazal = db.query(models.Ghazal).filter(models.Ghazal.number == number).first()
    if not ghazal:
        raise HTTPException(status_code=404, detail="Ghazal not found")
    view = db.query(models.GhazalView).filter(
        models.GhazalView.user_id == current_user.id,
        models.GhazalView.ghazal_id == ghazal.id,
    ).first()
    from datetime import date
    today = datetime.utcnow().date()
    if view:
        if view.last_viewed_at.date() < today:
            view.view_count += 1
            view.last_viewed_at = datetime.utcnow()
    else:
        view = models.GhazalView(user_id=current_user.id, ghazal_id=ghazal.id)
        db.add(view)
    db.commit()
    return {"view_count": view.view_count, "last_viewed_at": view.last_viewed_at}


@app.get("/history/ghazal/{number}")
def get_ghazal_view(
    number: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ghazal = db.query(models.Ghazal).filter(models.Ghazal.number == number).first()
    if not ghazal:
        raise HTTPException(status_code=404, detail="Ghazal not found")
    view = db.query(models.GhazalView).filter(
        models.GhazalView.user_id == current_user.id,
        models.GhazalView.ghazal_id == ghazal.id,
    ).first()
    if not view:
        return None
    return {"view_count": view.view_count, "last_viewed_at": view.last_viewed_at}


@app.get("/history/ghazals")
def get_ghazal_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    views = (
        db.query(models.GhazalView, models.Ghazal)
        .join(models.Ghazal, models.GhazalView.ghazal_id == models.Ghazal.id)
        .filter(models.GhazalView.user_id == current_user.id)
        .order_by(models.GhazalView.last_viewed_at.desc())
        .all()
    )
    return [
        {
            "ghazal_number": ghazal.number,
            "ghazal_title": ghazal.title,
            "view_count": view.view_count,
            "last_viewed_at": view.last_viewed_at,
        }
        for view, ghazal in views
    ]


# --- Poem Routes ---

@app.get("/poems/ghazals")
def list_ghazals(db: Session = Depends(get_db)):
    ghazals = db.query(models.Ghazal).order_by(models.Ghazal.number).all()
    return [
        {"number": g.number, "title": g.title, "first_couplet": g.couplets[0] if g.couplets else []}
        for g in ghazals
    ]


@app.get("/poems/terjees")
def list_terjees(db: Session = Depends(get_db)):
    bands = db.query(models.Terjee).order_by(models.Terjee.number).all()
    return [
        {"number": b.number, "first_couplet": b.couplets[0] if b.couplets else []}
        for b in bands
    ]


@app.get("/poems/ghazal/random")
def random_ghazal(db: Session = Depends(get_db)):
    count = db.query(models.Ghazal).count()
    if not count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="داده‌ای یافت نشد")
    ghazal = db.query(models.Ghazal).offset(random_module.randint(0, count - 1)).first()
    return {"number": ghazal.number, "title": ghazal.title, "couplets": ghazal.couplets}


@app.get("/poems/ghazal/{number}")
def get_ghazal(number: int, db: Session = Depends(get_db)):
    ghazal = db.query(models.Ghazal).filter(models.Ghazal.number == number).first()
    if not ghazal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="غزل یافت نشد")
    return {"number": ghazal.number, "title": ghazal.title, "couplets": ghazal.couplets}


@app.get("/poems/terjee/{number}")
def get_terjee(number: int, db: Session = Depends(get_db)):
    band = db.query(models.Terjee).filter(models.Terjee.number == number).first()
    if not band:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="بند یافت نشد")
    return {"number": band.number, "couplets": band.couplets}


@app.get("/poems/search")
def search_poems(
    q: str = Query(..., min_length=2),
    type: str = Query("g", pattern="^(g|t)$"),
    db: Session = Depends(get_db),
):
    results = []
    if type == "g":
        ghazals = db.query(models.Ghazal).all()
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
    else:
        bands = db.query(models.Terjee).all()
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
    return {"query": q, "count": len(results), "results": results}


@app.get("/poems/zand")
def list_zand(db: Session = Depends(get_db)):
    sections = db.query(models.Zand).order_by(models.Zand.number).all()
    return [
        {"number": z.number, "title": z.title, "type": z.type, "has_content": bool(z.content)}
        for z in sections
    ]


@app.get("/poems/zand/{number}")
def get_zand(number: int, db: Session = Depends(get_db)):
    section = db.query(models.Zand).filter(models.Zand.number == number).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="بخش یافت نشد")
    return {"number": section.number, "title": section.title, "type": section.type, "content": section.content}


BOT_AGENTS = ("googlebot", "bingbot", "facebookexternalhit", "twitterbot", "crawler", "spider", "bot")

@app.get("/poems/ghazal/{number}/html", include_in_schema=False)
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
        couplets_html += f'<div class="couplet"><p>{m1}</p>'
        if m2:
            couplets_html += f'<p class="m2">{m2}</p>'
        couplets_html += "</div>\n"

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>غزل {number} — {ghazal.title} | دیوان بیدل دهلوی</title>
<meta name="description" content="{description}">
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
<h1>غزل {number} — {ghazal.title}</h1>
<div class="meta">دیوان بیدل دهلوی · {len(ghazal.couplets)} بیت</div>
<main>
{couplets_html}</main>
<a class="back" href="https://bideli.ir/ghazal/{number}">مشاهده در سایت بیدلی ←</a>
</body>
</html>"""

    return HTMLResponse(content=html)


@app.get("/poems/ghazal/{number}/keywords")
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


@app.get("/poems/terjee/{number}/keywords")
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


@app.get("/poems/verse-of-day")
def verse_of_day(db: Session = Depends(get_db)):
    total = db.query(models.Ghazal).count()
    if not total:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="داده‌ای یافت نشد")

    today = date.today()
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


# --- Keyword Routes ---
# NOTE: specific paths (/featured, /categories) must be defined before /keywords/{word}

@app.get("/keywords/featured")
def get_featured_keywords(db: Session = Depends(get_db)):
    keywords = db.query(models.Keyword).order_by(models.Keyword.id).all()
    if not keywords:
        return []

    today = date.today()
    seed = today.year * 10000 + today.month * 100 + today.day
    rng = random_module.Random(seed)
    selected = rng.sample(keywords, min(4, len(keywords)))

    return [
        {
            "word": k.word,
            "count": k.count,
            "category": k.category,
            "meaning": k.meaning,
        }
        for k in selected
    ]


@app.get("/keywords/categories")
def get_keyword_categories(db: Session = Depends(get_db)):
    rows = db.query(models.Keyword.category, models.Keyword.maqam).all()
    categories = sorted({r.category for r in rows if r.category})
    maqams = sorted({r.maqam for r in rows if r.maqam})
    return {"categories": categories, "maqams": maqams}


@app.get("/keywords")
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


@app.get("/sitemap.xml", include_in_schema=False)
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

    for n in range(1, 2828):
        urls.append(url(f"{BASE}/ghazal/{n}", "0.8"))

    for n in range(1, 35):
        urls.append(url(f"{BASE}/terjee/{n}", "0.7"))

    zand_numbers = db.query(models.Zand.number).order_by(models.Zand.number).all()
    for (n,) in zand_numbers:
        urls.append(url(f"{BASE}/zand/{n}", "0.6"))

    keywords = db.query(models.Keyword.word).order_by(models.Keyword.word).all()
    for (word,) in keywords:
        urls.append(url(f"{BASE}/keywords/{quote(word, safe='')}", "0.7"))

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls)
    xml += "\n</urlset>"
    return Response(content=xml, media_type="application/xml")


@app.get("/keywords/{word}/html", include_in_schema=False)
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
<title>{word} در دیوان بیدل دهلوی</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://bideli.ir/keywords/{word}">
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
<h1>{word}</h1>
<div class="meta">دیوان بیدل دهلوی · {kw.count or 0} بار تکرار</div>
{"<div class='meaning'>" + kw.meaning + "</div>" if kw.meaning else ""}
<div class="field"><span class="label">مقام: </span><span class="value">{kw.maqam or '—'}</span></div>
<div class="field"><span class="label">دسته‌بندی: </span><span class="value">{kw.category or '—'}</span></div>
<div class="field"><span class="label">تعداد تکرار: </span><span class="value">{kw.count or 0}</span></div>
<a class="back" href="https://bideli.ir/keywords/{word}">مشاهده در سایت بیدلی ←</a>
</body>
</html>"""

    return HTMLResponse(content=html)


@app.get("/keywords/{word}")
def get_keyword(word: str, db: Session = Depends(get_db)):
    kw = db.query(models.Keyword).filter(models.Keyword.word == word).first()
    if not kw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="کلمه کلیدی یافت نشد")

    ghazals = [
        {
            "number": gk.ghazal.number,
            "title": gk.ghazal.title,
            "count": gk.count,
        }
        for gk in sorted(kw.ghazals, key=lambda x: x.count, reverse=True)
    ]
    terjees = [
        {
            "number": tk.terjee.number,
            "count": tk.count,
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


# ─── KHANESH ───────────────────────────────────────────────────────────

class KhaneshCreate(BaseModel):
    title: str
    slug: str
    content: str
    terjee_number: int
    instructor: str
    role: Optional[str] = None
    tags: List[str] = []
    published_at: Optional[datetime] = None

@app.get("/khanesh")
def get_khanesh_list(db: Session = Depends(get_db)):
    items = db.query(models.Khanesh).order_by(models.Khanesh.published_at.desc().nullslast(), models.Khanesh.created_at.desc()).all()
    return [
        {
            "id": k.id,
            "title": k.title,
            "slug": k.slug,
            "terjee_number": k.terjee_number,
            "instructor": k.instructor,
            "role": k.role,
            "tags": k.tags or [],
            "published_at": k.published_at.isoformat() if k.published_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        }
        for k in items
    ]

@app.get("/khanesh/terjee/{number}")
def get_khanesh_by_terjee(number: int, db: Session = Depends(get_db)):
    items = db.query(models.Khanesh).filter(models.Khanesh.terjee_number == number).order_by(models.Khanesh.published_at.desc().nullslast(), models.Khanesh.created_at.desc()).all()
    return [
        {
            "id": k.id,
            "title": k.title,
            "slug": k.slug,
            "terjee_number": k.terjee_number,
            "instructor": k.instructor,
            "role": k.role,
            "tags": k.tags or [],
            "published_at": k.published_at.isoformat() if k.published_at else None,
        }
        for k in items
    ]

@app.get("/khanesh/{slug}")
def get_khanesh(slug: str, db: Session = Depends(get_db)):
    k = db.query(models.Khanesh).filter(models.Khanesh.slug == slug).first()
    if not k:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "id": k.id,
        "title": k.title,
        "slug": k.slug,
        "content": k.content,
        "terjee_number": k.terjee_number,
        "instructor": k.instructor,
        "role": k.role,
        "tags": k.tags or [],
        "published_at": k.published_at.isoformat() if k.published_at else None,
        "created_at": k.created_at.isoformat() if k.created_at else None,
    }

@app.post("/khanesh")
def create_khanesh(
    data: KhaneshCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    existing = db.query(models.Khanesh).filter(models.Khanesh.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="slug already exists")
    k = models.Khanesh(
        title=data.title,
        slug=data.slug,
        content=data.content,
        terjee_number=data.terjee_number,
        instructor=data.instructor,
        role=data.role,
        tags=data.tags,
        published_at=data.published_at or datetime.utcnow(),
    )
    db.add(k)
    db.commit()
    db.refresh(k)
    return {"status": "ok", "id": k.id, "slug": k.slug}

@app.put("/khanesh/{slug}")
def update_khanesh(
    slug: str,
    data: KhaneshCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    k = db.query(models.Khanesh).filter(models.Khanesh.slug == slug).first()
    if not k:
        raise HTTPException(status_code=404, detail="not found")
    k.title = data.title
    k.slug = data.slug
    k.content = data.content
    k.terjee_number = data.terjee_number
    k.instructor = data.instructor
    k.role = data.role
    k.tags = data.tags
    if data.published_at:
        k.published_at = data.published_at
    db.commit()
    return {"status": "ok"}

@app.delete("/khanesh/{slug}")
def delete_khanesh(
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    k = db.query(models.Khanesh).filter(models.Khanesh.slug == slug).first()
    if not k:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(k)
    db.commit()
    return {"status": "ok"}
