import threading

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import neighbors_index
from database import Base, SessionLocal, engine
from neighbors_index import build_index
import deps  # noqa: F401  (ساخت پوشهٔ media)
from routers import auth_routes, user_routes, poems, keywords, khanesh, pajvak

# migrationهای قدیمی فرض می‌کنند جدول‌ها از قبل هست، پس create_all فعلاً لازم است
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/media", StaticFiles(directory="media"), name="media")


# --- ساخت ایندکس همسایه در پس‌زمینه (اپ منتظر نمی‌ماند) ---

def _build_neighbors_index():
    db = SessionLocal()
    try:
        build_index(db)
        print(f"[neighbors] index ready: {neighbors_index.INDEX.n_bayts} bayts, {len(neighbors_index.INDEX.df)} tokens", flush=True)
    except Exception as e:
        print(f"[neighbors] index build failed: {e}", flush=True)
    finally:
        db.close()


@app.on_event("startup")
def _startup_build_neighbors_index():
    threading.Thread(target=_build_neighbors_index, daemon=True).start()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bideli.ir", "https://www.bideli.ir"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


_CACHEABLE = {"/poems/ghazals", "/poems/terjees", "/poems/zand", "/keywords/graph",
              "/keywords/categories", "/sitemap.xml"}


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if request.method == "GET" and response.status_code == 200 and (
        path in _CACHEABLE or path.startswith("/keywords/graph/")
    ) and "cache-control" not in response.headers:
        response.headers["Cache-Control"] = "public, max-age=3600"
    return response



# ترتیب include مهم است: مسیرهای خاص‌تر باید قبل از مسیرهای پارامتری بیایند
for _r in (auth_routes, user_routes, poems, keywords, khanesh, pajvak):
    app.include_router(_r.router)
