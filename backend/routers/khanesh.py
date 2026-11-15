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

@router.get("/khanesh")
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

@router.get("/khanesh/terjee/{number}")
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

@router.get("/khanesh/{slug}")
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

@router.post("/khanesh")
def create_khanesh(
    data: KhaneshCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    existing = db.query(models.Khanesh).filter(models.Khanesh.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="slug already exists")
    k = models.Khanesh(
        title=data.title,
        slug=data.slug,
        content=sanitize_html(data.content),
        terjee_number=data.terjee_number,
        instructor=data.instructor,
        role=data.role,
        tags=data.tags,
        published_at=data.published_at or utcnow(),
    )
    db.add(k)
    db.commit()
    db.refresh(k)
    return {"status": "ok", "id": k.id, "slug": k.slug}

@router.put("/khanesh/{slug}")
def update_khanesh(
    slug: str,
    data: KhaneshCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    k = db.query(models.Khanesh).filter(models.Khanesh.slug == slug).first()
    if not k:
        raise HTTPException(status_code=404, detail="not found")
    k.title = data.title
    k.slug = data.slug
    k.content = sanitize_html(data.content)
    k.terjee_number = data.terjee_number
    k.instructor = data.instructor
    k.role = data.role
    k.tags = data.tags
    if data.published_at:
        k.published_at = data.published_at
    db.commit()
    return {"status": "ok"}

@router.delete("/khanesh/{slug}")
def delete_khanesh(
    slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    k = db.query(models.Khanesh).filter(models.Khanesh.slug == slug).first()
    if not k:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(k)
    db.commit()
    return {"status": "ok"}
