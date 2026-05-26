import csv
import sys
from pathlib import Path

from database import SessionLocal, engine
import models

CSV_PATH = Path(__file__).resolve().parent / "data" / "keywords.csv"

COL_WORD       = "کلمه"
COL_COUNT      = "تعداد"
COL_PERCENTAGE = "درصد از کل"
COL_MEANING    = "معنی (دهخدا)"
COL_CATEGORY   = "دسته‌بندی موضوعی"
COL_MAQAM      = "مقامات سلوک"
COL_CONTRAST   = "دوگانه‌های متضاد"


def import_keywords(db) -> dict[str, int]:
    """Import keywords from CSV. Returns {word: keyword_id}."""
    existing = db.query(models.Keyword).count()
    if existing > 0:
        print(f"Keywords already imported ({existing} records) — loading from DB.")
        return {k.word: k.id for k in db.query(models.Keyword).all()}

    if not CSV_PATH.exists():
        print(f"Error: {CSV_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    records = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row.get(COL_WORD, "").strip()
            if not word:
                continue
            records.append(models.Keyword(
                word=word,
                count=int(row[COL_COUNT]) if row.get(COL_COUNT, "").strip().isdigit() else None,
                percentage=row.get(COL_PERCENTAGE, "").strip() or None,
                meaning=row.get(COL_MEANING, "").strip() or None,
                category=row.get(COL_CATEGORY, "").strip() or None,
                maqam=row.get(COL_MAQAM, "").strip() or None,
                contrast=row.get(COL_CONTRAST, "").strip() or None,
            ))

    db.bulk_save_objects(records)
    db.commit()
    print(f"Imported {len(records)} keywords.")

    return {k.word: k.id for k in db.query(models.Keyword).all()}


def poem_text(couplets: list) -> str:
    """Flatten couplet list to a single searchable string."""
    parts = []
    for couplet in couplets:
        if isinstance(couplet, list):
            parts.extend(h for h in couplet if h)
    return " ".join(parts)


def link_ghazals(db, keyword_map: dict[str, int]) -> int:
    existing = db.query(models.GhazalKeyword).count()
    if existing > 0:
        print(f"GhazalKeyword already linked ({existing} records) — skipping.")
        return existing

    ghazals = db.query(models.Ghazal).all()
    relations = []
    for ghazal in ghazals:
        text = poem_text(ghazal.couplets)
        for word, kid in keyword_map.items():
            cnt = text.count(word)
            if cnt > 0:
                relations.append(models.GhazalKeyword(
                    ghazal_id=ghazal.id,
                    keyword_id=kid,
                    count=cnt,
                ))

    db.bulk_save_objects(relations)
    db.commit()
    print(f"Processed {len(ghazals)} ghazals → {len(relations)} GhazalKeyword relations.")
    return len(relations)


def link_terjees(db, keyword_map: dict[str, int]) -> int:
    existing = db.query(models.TerjeeKeyword).count()
    if existing > 0:
        print(f"TerjeeKeyword already linked ({existing} records) — skipping.")
        return existing

    terjees = db.query(models.Terjee).all()
    relations = []
    for terjee in terjees:
        text = poem_text(terjee.couplets)
        for word, kid in keyword_map.items():
            cnt = text.count(word)
            if cnt > 0:
                relations.append(models.TerjeeKeyword(
                    terjee_id=terjee.id,
                    keyword_id=kid,
                    count=cnt,
                ))

    db.bulk_save_objects(relations)
    db.commit()
    print(f"Processed {len(terjees)} terjee bands → {len(relations)} TerjeeKeyword relations.")
    return len(relations)


if __name__ == "__main__":
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        keyword_map = import_keywords(db)
        g_relations = link_ghazals(db, keyword_map)
        t_relations = link_terjees(db, keyword_map)

        print("\n── آمار ──────────────────────────")
        print(f"  کلمات کلیدی:       {len(keyword_map)}")
        print(f"  غزل‌های پردازش‌شده: {db.query(models.Ghazal).count()}")
        print(f"  بندهای پردازش‌شده: {db.query(models.Terjee).count()}")
        print(f"  روابط غزل:         {g_relations}")
        print(f"  روابط ترجیع:       {t_relations}")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()
