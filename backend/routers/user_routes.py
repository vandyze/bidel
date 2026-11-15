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

@router.post("/bookmarks", status_code=status.HTTP_200_OK)
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
        soluk.invalidate(current_user.id)
        return {"action": "removed"}

    bookmark = models.Bookmark(
        user_id=current_user.id,
        poem_type=body.poem_type,
        poem_id=body.poem_id,
        couplet_index=body.couplet_index,
    )
    db.add(bookmark)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"action": "added"}
    db.refresh(bookmark)
    touch_activity(db, current_user.id)
    soluk.invalidate(current_user.id)
    return {"action": "added", "id": bookmark.id}


@router.delete("/bookmarks/{poem_type}/{poem_id}/{couplet_index}", status_code=status.HTTP_204_NO_CONTENT)
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
    soluk.invalidate(current_user.id)


@router.get("/bookmarks", response_model=list[BookmarkResponse])
def get_bookmarks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    bookmarks = db.query(models.Bookmark).filter(models.Bookmark.user_id == current_user.id).order_by(models.Bookmark.created_at.desc()).all()
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

@router.post("/notes", status_code=status.HTTP_200_OK)
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
        soluk.invalidate(current_user.id)
        return {"action": "updated", "id": existing.id}

    note = models.Note(
        user_id=current_user.id,
        poem_type=body.poem_type,
        poem_id=body.poem_id,
        couplet_index=body.couplet_index,
        text=body.text,
    )
    db.add(note)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="یادداشت هم‌زمان ثبت شد؛ دوباره تلاش کنید")
    db.refresh(note)
    touch_activity(db, current_user.id)
    soluk.invalidate(current_user.id)
    return {"action": "created", "id": note.id}


@router.delete("/notes/{poem_type}/{poem_id}/{couplet_index}", status_code=status.HTTP_204_NO_CONTENT)
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
    soluk.invalidate(current_user.id)


@router.get("/notes", response_model=list[NoteResponse])
def get_notes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    notes = db.query(models.Note).filter(models.Note.user_id == current_user.id).order_by(models.Note.created_at.desc()).all()
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

@router.post("/history/ghazal/{number}")
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
    today = tehran_today()
    if view:
        if view.last_viewed_at.replace(tzinfo=timezone.utc).astimezone(IRAN_TZ).date() < today:
            view.view_count += 1
            view.last_viewed_at = utcnow()
    else:
        view = models.GhazalView(user_id=current_user.id, ghazal_id=ghazal.id)
        db.add(view)
    db.commit()
    touch_activity(db, current_user.id)
    return {"view_count": view.view_count, "last_viewed_at": view.last_viewed_at}


@router.get("/history/ghazal/{number}")
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


@router.get("/history/ghazals")
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


# --- Profile / Soluk Routes ---

@router.get("/profile/soluk")
def get_soluk(db: Session = Depends(get_db),
              current_user: models.User = Depends(get_current_user)):
    return soluk.get_profile(db, current_user.id)


@router.get("/profile/soluk/maqam/{maqam_id}")
def get_soluk_maqam(
    maqam_id: str,
    limit: int = Query(6, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    payload = soluk.maqam_couplets(db, current_user.id, maqam_id, limit, offset)
    if payload is None:
        raise HTTPException(status_code=404, detail="مقام یافت نشد")
    return payload
