import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

import models
from text_utils import tokenize


@dataclass
class NeighborIndex:
    bayts: list[str] = field(default_factory=list)          # متن هر بیت
    bayt_tokens: list[frozenset] = field(default_factory=list)
    bayt_ref: list[tuple] = field(default_factory=list)     # ('g'|'tr', number, couplet_index)
    df: Counter = field(default_factory=Counter)            # token → تعداد بیت
    postings: dict = field(default_factory=lambda: defaultdict(set))  # token → {bayt_id}
    n_bayts: int = 0
    ready: bool = False


INDEX = NeighborIndex()


def build_index(db) -> NeighborIndex:
    idx = NeighborIndex()
    sources = [
        ("g", db.query(models.Ghazal).all()),
        ("tr", db.query(models.Terjee).all()),
    ]
    for ptype, rows in sources:
        for row in rows:
            for ci, couplet in enumerate(row.couplets or []):
                text = " ".join(couplet) if isinstance(couplet, list) else str(couplet)
                toks = frozenset(tokenize(text))
                if not toks:
                    continue
                bid = len(idx.bayts)
                idx.bayts.append(text)
                idx.bayt_tokens.append(toks)
                idx.bayt_ref.append((ptype, row.number, ci))
                for t in toks:
                    idx.df[t] += 1
                    idx.postings[t].add(bid)
    idx.n_bayts = len(idx.bayts)
    idx.ready = True
    global INDEX
    INDEX = idx
    return idx


MIN_CO = 3          # حداقل هم‌وقوعی
MIN_PPMI = 0.2
DISCOUNT_K = 2      # ضریب تخفیف برای مهار سوگیری PPMI به رویدادهای کمیاب


def live_neighbors(query: str, limit: int = 5) -> list[dict]:
    idx = INDEX
    if not idx.ready:
        raise RuntimeError("index not ready")

    qtoks = set(tokenize(query))
    if not qtoks:
        return []

    # تقاطع posting listها — به‌جای پیمایش کل کورپوس
    plists = [idx.postings.get(t) for t in qtoks]
    if any(p is None for p in plists):
        return []
    matched = set.intersection(*plists)
    n_q = len(matched)
    if n_q == 0:
        return []

    co = Counter()
    example = {}
    for bid in matched:
        for t in idx.bayt_tokens[bid] - qtoks:      # خودِ واژه هرگز همسایهٔ خودش نیست
            co[t] += 1
            if t not in example:
                example[t] = bid

    out = []
    for t, c in co.items():
        if c < MIN_CO:
            continue
        pmi = math.log2((c / n_q) / (idx.df[t] / idx.n_bayts))
        ppmi = max(0.0, pmi) * (c / (c + DISCOUNT_K))
        if ppmi >= MIN_PPMI:
            out.append({"word": t, "co": c, "score": round(ppmi, 3),
                        "example_bayt_id": example[t]})
    out.sort(key=lambda r: -r["score"])
    return out[:limit]


@lru_cache(maxsize=512)
def cached_live_neighbors(query_norm: str, limit: int):
    return tuple(live_neighbors(query_norm, limit))


def matched_bayts(query: str) -> int:
    """تعداد بیت‌های حاوی همهٔ توکن‌های نرمال‌شدهٔ کوئری."""
    idx = INDEX
    qtoks = set(tokenize(query))
    if not qtoks:
        return 0
    plists = [idx.postings.get(t) for t in qtoks]
    if any(p is None for p in plists):
        return 0
    return len(set.intersection(*plists))
