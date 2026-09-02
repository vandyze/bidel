# محاسبه‌ی پروفایل «سلوک من»
#
# منابع سیگنال: یادداشت (وزن ۵)، نشان (وزن ۳)، بازدید غزل (وزن ۱ × count کلیدواژه)
# خروجی بر پایه‌ی هفت مقام سلوک که نسبت به توزیع خود دیوان نرمال می‌شود.

import random
import re
import threading
import time
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from text_utils import normalize

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
# ترتیب هفت وادی — هماهنگ با MOODS فرانت (از بالا، در جهت عقربه‌های ساعت)
MAQAM_ORDER = ["talab", "eshgh", "marefat", "esteghna", "towhid", "heyrat", "fana"]

THRESHOLD = 8
SOLUK_TTL = 600  # ثانیه

_LOCK = threading.Lock()

# --- کش‌های فرایند ---
_KEYWORDS = None        # [(word_norm, pm)]
_WORD_MAP = None        # word_norm -> pm
_MAQAM_RE = None        # pm -> regex ترکیبی
_BASELINE = None        # pm -> سهم مقام در کل دیوان (0..1)
_GHAZAL_MAQAM = None    # number -> مقام غالب غزل
_TERJEE_MAQAM = None    # number -> مقام غالب ترجیع‌بند
_GHAZAL_NUM_BY_ID = None  # ghazal.id -> number

_PROFILE_CACHE = {}     # user_id -> (time, payload)


def invalidate(user_id: int):
    _PROFILE_CACHE.pop(user_id, None)


def _load_keyword_caches(db: Session):
    global _KEYWORDS, _WORD_MAP, _MAQAM_RE, _BASELINE
    global _GHAZAL_MAQAM, _TERJEE_MAQAM, _GHAZAL_NUM_BY_ID
    if _KEYWORDS is not None:
        return
    with _LOCK:
        if _KEYWORDS is not None:
            return
        maqam_set = list(MAQAM_IDS)
        word_map = {}
        buckets = {pm: [] for pm in maqam_set}
        rows = db.query(models.Keyword).all()
        kws = []
        for k in rows:
            if not k.maqam or k.maqam == "سایر" or k.maqam not in MAQAM_IDS:
                continue
            w = normalize(k.word)
            kws.append((w, k.maqam))
            word_map[w] = k.maqam
            buckets[k.maqam].append(w)
        _KEYWORDS = kws
        _WORD_MAP = word_map
        _MAQAM_RE = {
            pm: re.compile(r"(?:" + "|".join(re.escape(w) for w in ws) + ")")
            for pm, ws in buckets.items() if ws
        }

        # پایه‌ی دیوان: توزیع مقام‌ها در کل GhazalKeyword
        b_rows = (
            db.query(models.Keyword.maqam, func.sum(models.GhazalKeyword.count))
            .join(models.GhazalKeyword, models.GhazalKeyword.keyword_id == models.Keyword.id)
            .filter(models.Keyword.maqam.in_(maqam_set))
            .group_by(models.Keyword.maqam)
            .all()
        )
        b_total = sum((c or 0) for _, c in b_rows) or 1
        _BASELINE = {pm: 0.0 for pm in maqam_set}
        for pm, c in b_rows:
            _BASELINE[pm] = (c or 0) / b_total

        # مقام غالب غزل‌ها (بر اساس شمارهٔ غزل، چون بوکمارک/یادداشت با number اند)
        num_by_id = dict(db.query(models.Ghazal.id, models.Ghazal.number).all())
        _GHAZAL_NUM_BY_ID = num_by_id
        per_gh = {}
        g_rows = (
            db.query(models.GhazalKeyword.ghazal_id, models.Keyword.maqam,
                     func.sum(models.GhazalKeyword.count))
            .join(models.Keyword, models.GhazalKeyword.keyword_id == models.Keyword.id)
            .filter(models.Keyword.maqam.in_(maqam_set))
            .group_by(models.GhazalKeyword.ghazal_id, models.Keyword.maqam)
            .all()
        )
        for gid, pm, c in g_rows:
            num = num_by_id.get(gid)
            if num is None:
                continue
            per_gh.setdefault(num, []).append((c or 0, pm))
        _GHAZAL_MAQAM = {num: max(lst)[1] for num, lst in per_gh.items()}

        t_num_by_id = dict(db.query(models.Terjee.id, models.Terjee.number).all())
        per_tj = {}
        t_rows = (
            db.query(models.TerjeeKeyword.terjee_id, models.Keyword.maqam,
                     func.sum(models.TerjeeKeyword.count))
            .join(models.Keyword, models.TerjeeKeyword.keyword_id == models.Keyword.id)
            .filter(models.Keyword.maqam.in_(maqam_set))
            .group_by(models.TerjeeKeyword.terjee_id, models.Keyword.maqam)
            .all()
        )
        for tid, pm, c in t_rows:
            num = t_num_by_id.get(tid)
            if num is None:
                continue
            per_tj.setdefault(num, []).append((c or 0, pm))
        _TERJEE_MAQAM = {num: max(lst)[1] for num, lst in per_tj.items()}


def _match_couplet(text_norm: str):
    """واژه‌های ۲۲۲گانه‌ی موجود در متن → (map مقام->تعداد, map واژه->تعداد)."""
    maqam_counts = {}
    word_counts = {}
    for pm, rx in _MAQAM_RE.items():
        found = rx.findall(text_norm)
        if found:
            maqam_counts[pm] = len(found)
            for w in found:
                word_counts[w] = word_counts.get(w, 0) + 1
    return maqam_counts, word_counts


def _poem_dominant(poem_type: str, poem_id: int):
    if poem_type == "g":
        return _GHAZAL_MAQAM.get(poem_id)
    if poem_type == "t":
        return _TERJEE_MAQAM.get(poem_id)
    return None


def _pair(entry):
    if isinstance(entry, (list, tuple)):
        return [str(entry[0] or ""), str(entry[1] or "")]
    return [str(entry or ""), ""]


def _couplet_maqam(poem_type, poem_id, ci, couplets):
    """مقام یک بیت: از واژه‌های خود بیت، وگرنه fallback به مقام غالب کل غزل."""
    if not couplets or ci is None or ci < 0 or ci >= len(couplets):
        return None, {}
    pair = _pair(couplets[ci])
    text_norm = normalize(pair[0] + " " + pair[1])
    mc, _ = _match_couplet(text_norm)
    if mc:
        return max(mc, key=mc.get), mc
    return _poem_dominant(poem_type, poem_id), {}


def _month_add(d, dt, pm, val):
    if dt is None:
        return
    key = dt.strftime("%Y-%m")
    d.setdefault(key, {})
    d[key][pm] = d[key].get(pm, 0) + val


def _streaks(dates):
    if not dates:
        return 0, 0
    ds = sorted(set(dates))
    longest, cur = 1, 1
    prev = ds[0]
    for d in ds[1:]:
        if (d - prev).days == 1:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 1
        prev = d
    today = date.today()
    cur_streak = 0
    if ds[-1] >= today - timedelta(days=1) and ds[-1] <= today:
        cur_streak = 1
        i = len(ds) - 2
        while i >= 0 and (ds[i + 1] - ds[i]).days == 1:
            cur_streak += 1
            i -= 1
    return longest, cur_streak


def _accumulate(db, bookmarks, notes, views):
    """جمع‌آوری سیگنال‌ها → (raw, top_words, month_raw, couplet_meta)."""
    bm_sigs = [b for b in bookmarks if b.poem_type in ("g", "t")]
    nt_sigs = [n for n in notes if n.poem_type in ("g", "t")]

    gh_nums = {b.poem_id for b in bm_sigs if b.poem_type == "g"} | \
              {n.poem_id for n in nt_sigs if n.poem_type == "g"}
    tj_nums = {b.poem_id for b in bm_sigs if b.poem_type == "t"} | \
              {n.poem_id for n in nt_sigs if n.poem_type == "t"}

    ghazal_cps = {}
    if gh_nums:
        ghazal_cps = {g.number: g.couplets for g in
                      db.query(models.Ghazal).filter(models.Ghazal.number.in_(gh_nums)).all()}
    terjee_cps = {}
    if tj_nums:
        terjee_cps = {t.number: t.couplets for t in
                      db.query(models.Terjee).filter(models.Terjee.number.in_(tj_nums)).all()}

    def get_couplets(ptype, pid):
        return ghazal_cps.get(pid) if ptype == "g" else terjee_cps.get(pid)

    raw = {pm: 0 for pm in MAQAM_IDS}
    top_words = {}
    month_raw = {}
    couplet_meta = []

    def add_couplet_signal(ptype, pid, ci, created_at, weight):
        cps = get_couplets(ptype, pid)
        if not cps or ci is None or ci < 0 or ci >= len(cps):
            return
        pair = _pair(cps[ci])
        text_norm = normalize(pair[0] + " " + pair[1])
        mc, wc = _match_couplet(text_norm)
        if mc:
            for pm, n in mc.items():
                val = weight * n
                raw[pm] += val
                _month_add(month_raw, created_at, pm, val)
            for w, n in wc.items():
                top_words[w] = top_words.get(w, 0) + weight * n
        else:
            pm = _poem_dominant(ptype, pid)
            if pm:
                raw[pm] += weight
                _month_add(month_raw, created_at, pm, weight)
        couplet_meta.append({
            "type": ptype, "id": pid, "ci": ci,
            "pair": pair, "mc": mc, "w": weight,
            "created_at": created_at or datetime.min,
        })

    for b in bm_sigs:
        add_couplet_signal(b.poem_type, b.poem_id, b.couplet_index, b.created_at, 3)
    for n in nt_sigs:
        add_couplet_signal(n.poem_type, n.poem_id, n.couplet_index, n.created_at, 5)

    # بازدید غزل‌ها: GhazalKeyword با ضرب در count
    gids = [v.ghazal_id for v in views]
    kw_rows = []
    if gids:
        kw_rows = (
            db.query(models.GhazalKeyword, models.Keyword)
            .join(models.Keyword, models.GhazalKeyword.keyword_id == models.Keyword.id)
            .filter(models.GhazalKeyword.ghazal_id.in_(gids))
            .all()
        )
    by_g = {}
    for gk, kw in kw_rows:
        if not kw.maqam or kw.maqam not in MAQAM_IDS:
            continue
        by_g.setdefault(gk.ghazal_id, []).append((gk, kw))

    for v in views:
        for gk, kw in by_g.get(v.ghazal_id, []):
            val = 1 * (gk.count or 1)
            pm = kw.maqam
            raw[pm] += val
            top_words[kw.word] = top_words.get(kw.word, 0) + val
            _month_add(month_raw, v.last_viewed_at, pm, val)

    return raw, top_words, month_raw, couplet_meta


def _index_map(raw):
    total = sum(raw.values())
    if total <= 0:
        return None
    share = {pm: raw[pm] / total for pm in MAQAM_IDS}
    index = {}
    for pm in MAQAM_IDS:
        denom = _BASELINE.get(pm) or 0.0
        index[pm] = (share[pm] / denom) if denom else 0.0
    return index


def _month_dominant(month_dist):
    share_total = sum(month_dist.values())
    if share_total <= 0:
        return None
    index = {}
    for pm in MAQAM_IDS:
        share = month_dist.get(pm, 0) / share_total
        denom = _BASELINE.get(pm) or 0.0
        index[pm] = (share / denom) if denom else 0.0
    if not any(index.values()):
        return None
    return max(index, key=index.get)


def _pick_highlight(couplet_meta, dominant_pm):
    cands = [m for m in couplet_meta if m["pair"][0] or m["pair"][1]]
    if not cands:
        return None
    return max(
        cands,
        key=lambda m: (m["mc"].get(dominant_pm, 0), m["w"],
                       m["created_at"] or datetime.min),
    )


def _compute_profile(db: Session, user_id: int):
    _load_keyword_caches(db)
    bookmarks = db.query(models.Bookmark).filter_by(user_id=user_id).all()
    notes = db.query(models.Note).filter_by(user_id=user_id).all()
    views = db.query(models.GhazalView).filter_by(user_id=user_id).all()

    signals_count = len(bookmarks) + len(notes) + len(views)
    if signals_count < THRESHOLD:
        return {"ready": False, "signals_count": signals_count, "threshold": THRESHOLD}

    raw, top_words, month_raw, couplet_meta = _accumulate(db, bookmarks, notes, views)
    index = _index_map(raw)
    if index is None:
        return {"ready": False, "signals_count": signals_count, "threshold": THRESHOLD}

    # ── رادار ──
    total_raw = sum(raw.values())
    share = {pm: cnt / total_raw for pm, cnt in raw.items()}
    max_idx = max(index.values()) or 1.0
    radar = [
        {
            "id": lid,
            "label": MAQAM_BY_ID[lid],
            "value": round(index[MAQAM_BY_ID[lid]] / max_idx, 4),
            "raw": raw[MAQAM_BY_ID[lid]],
            "share": round(share[MAQAM_BY_ID[lid]], 4),
            "baseline": round(_BASELINE[MAQAM_BY_ID[lid]], 4),
            "index": round(index[MAQAM_BY_ID[lid]], 4),
        }
        for lid in MAQAM_ORDER
    ]

    # ── مقام غالب ──
    order90 = sorted(MAQAM_ORDER, key=lambda pid: index[MAQAM_BY_ID[pid]], reverse=True)
    top1_id = order90[0]
    top1_idx = index[MAQAM_BY_ID[top1_id]]
    tied = None
    if len(order90) > 1:
        top2_idx = index[MAQAM_BY_ID[order90[1]]]
        if top1_idx > 0 and (top1_idx - top2_idx) / top1_idx < 0.10:
            tied = order90[1]
    dominant = {"id": top1_id, "label": MAQAM_BY_ID[top1_id], "tied_with": tied}
    dominant_pm = dominant["label"]

    # ── سیر سلوک ──
    months = sorted(month_raw.keys())
    timeline = []
    if len(months) >= 2:
        timeline = [
            {"month": m, "dominant": MAQAM_IDS[_month_dominant(month_raw[m])]}
            for m in months if _month_dominant(month_raw[m])
        ]

    # ── واژه‌های من ──
    tops = sorted(top_words.items(), key=lambda kv: (-kv[1], kv[0]))[:12]
    top_words_out = [
        {"word": w, "count": c, "maqam": _WORD_MAP.get(w, "")} for w, c in tops
    ]

    # ── بیت شاخص ──
    highlight = None
    hl = _pick_highlight(couplet_meta, dominant_pm)
    if hl:
        highlight = {
            "poem_type": hl["type"],
            "poem_id": hl["id"],
            "couplet_index": hl["ci"],
            "couplet": hl["pair"],
        }

    # ── وادیِ نرفته + پیشنهاد ──
    least_id = min(MAQAM_ORDER, key=lambda pid: index[MAQAM_BY_ID[pid]])
    least = {"id": least_id, "label": MAQAM_BY_ID[least_id]}
    least_pm = least["label"]
    viewed_nums = {_GHAZAL_NUM_BY_ID.get(v.ghazal_id) for v in views}
    viewed_nums.discard(None)
    cands = [num for num, pm in _GHAZAL_MAQAM.items()
             if pm == least_pm and num not in viewed_nums]
    random.shuffle(cands)
    cands = cands[:3]
    suggestions = []
    if cands:
        gh_map = {g.number: g for g in
                  db.query(models.Ghazal).filter(models.Ghazal.number.in_(cands)).all()}
        suggestions = [
            {"number": num, "title": (gh_map[num].title if gh_map.get(num) else "") or ""}
            for num in cands
        ]

    # ── خواندن ──
    act_dates = [
        r[0] for r in db.query(models.UserActivity.date)
        .filter_by(user_id=user_id).order_by(models.UserActivity.date).all()
    ]
    longest_streak, current_streak = _streaks(act_dates)
    reading = {
        "ghazals_read": len(views),
        "active_days": len(act_dates),
        "current_streak": current_streak,
        "longest_streak": longest_streak,
    }

    return {
        "ready": True,
        "signals_count": signals_count,
        "threshold": THRESHOLD,
        "radar": radar,
        "dominant": dominant,
        "timeline": timeline,
        "top_words": top_words_out,
        "highlight": highlight,
        "least_maqam": least,
        "suggestions": suggestions,
        "reading": reading,
    }


def get_profile(db: Session, user_id: int):
    now = time.time()
    cached = _PROFILE_CACHE.get(user_id)
    if cached and now - cached[0] < SOLUK_TTL:
        return cached[1]
    payload = _compute_profile(db, user_id)
    _PROFILE_CACHE[user_id] = (now, payload)
    return payload


def maqam_couplets(db: Session, user_id: int, maqam_id: str, limit: int, offset: int):
    _load_keyword_caches(db)
    pm = MAQAM_BY_ID.get(maqam_id)
    if not pm:
        return None
    bookmarks = [b for b in db.query(models.Bookmark).filter_by(user_id=user_id).all()
                 if b.poem_type in ("g", "t")]
    notes = [n for n in db.query(models.Note).filter_by(user_id=user_id).all()
             if n.poem_type in ("g", "t")]

    gh_nums = {b.poem_id for b in bookmarks if b.poem_type == "g"} | \
              {n.poem_id for n in notes if n.poem_type == "g"}
    tj_nums = {b.poem_id for b in bookmarks if b.poem_type == "t"} | \
              {n.poem_id for n in notes if n.poem_type == "t"}
    ghazal_cps = {}
    if gh_nums:
        ghazal_cps = {g.number: g.couplets for g in
                      db.query(models.Ghazal).filter(models.Ghazal.number.in_(gh_nums)).all()}
    terjee_cps = {}
    if tj_nums:
        terjee_cps = {t.number: t.couplets for t in
                      db.query(models.Terjee).filter(models.Terjee.number.in_(tj_nums)).all()}

    items = []
    for b in bookmarks:
        cps = ghazal_cps.get(b.poem_id) if b.poem_type == "g" else terjee_cps.get(b.poem_id)
        found, _ = _couplet_maqam(b.poem_type, b.poem_id, b.couplet_index, cps)
        if found != pm:
            continue
        pair = _pair(cps[b.couplet_index])
        items.append((b.created_at or datetime.min,
                      {"poem_type": b.poem_type, "poem_id": b.poem_id,
                       "couplet_index": b.couplet_index, "couplet": pair}))
    for n in notes:
        cps = ghazal_cps.get(n.poem_id) if n.poem_type == "g" else terjee_cps.get(n.poem_id)
        found, _ = _couplet_maqam(n.poem_type, n.poem_id, n.couplet_index, cps)
        if found != pm:
            continue
        pair = _pair(cps[n.couplet_index])
        items.append((n.created_at or datetime.min,
                      {"poem_type": n.poem_type, "poem_id": n.poem_id,
                       "couplet_index": n.couplet_index, "couplet": pair}))

    items.sort(key=lambda t: t[0], reverse=True)
    page = [it for _, it in items][offset:offset + limit]
    return {"total": len(items), "items": page}