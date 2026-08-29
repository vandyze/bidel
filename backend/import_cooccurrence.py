"""پر کردن جدول keyword_cooccurrence (idempotent).

اجرا بدون آرگومان:  python import_cooccurrence.py
منطق:
  ۱. ساخت ایندکس (همان build_index)
  ۲. برای هر بیت، مجموعهٔ واژه‌های واژه‌نامه‌ای که در آن هستند
  ۳. برای هر جفت، co_count را زیاد کن
  ۴. PPMI هر جفت با همان فرمول بخش ۳.۵
  ۵. جدول را TRUNCATE و دوباره پر کن
"""
import math
from collections import defaultdict

from database import SessionLocal
import models
from neighbors_index import build_index
from text_utils import normalize

MIN_CO = 3
MIN_PPMI = 0.2
DISCOUNT_K = 2


def main():
    db = SessionLocal()
    try:
        print("building index...", flush=True)
        idx = build_index(db)

        keywords = db.query(models.Keyword).all()
        norm_to_kid = {}
        for kw in keywords:
            n = normalize(kw.word)
            if n:
                norm_to_kid.setdefault(n, kw.id)

        n_bayts = max(idx.n_bayts, 1)
        co = defaultdict(int)
        kw_bayt_count = defaultdict(int)

        for toks in idx.bayt_tokens:
            present = set()
            for t in toks:
                kid = norm_to_kid.get(t)
                if kid is not None:
                    present.add(kid)
            for kid in present:
                kw_bayt_count[kid] += 1
            ids = sorted(present)
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    a, b = ids[i], ids[j]
                    co[(a, b)] += 1
                    co[(b, a)] += 1

        print(f"index ready: {idx.n_bayts} bayts; raw pairs: {len(co)}", flush=True)

        rows = []
        for (a, b), c in co.items():
            if c < MIN_CO:
                continue
            pa = kw_bayt_count[a] / n_bayts
            pb = kw_bayt_count[b] / n_bayts
            if pa <= 0 or pb <= 0:
                continue
            pmi = math.log2((c / n_bayts) / (pa * pb))
            ppmi = max(0.0, pmi) * (c / (c + DISCOUNT_K))
            if ppmi >= MIN_PPMI:
                rows.append((a, b, c, round(ppmi, 3)))

        # TRUNCATE + refill
        db.query(models.KeywordCooccurrence).delete()
        db.bulk_save_objects([
            models.KeywordCooccurrence(
                keyword_a_id=a, keyword_b_id=b, co_count=c, score=s)
            for a, b, c, s in rows
        ])
        db.commit()
        print(f"written {len(rows)} co-occurrence records", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
