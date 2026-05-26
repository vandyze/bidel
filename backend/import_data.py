import json
import os
import sys
from pathlib import Path

from database import SessionLocal, engine
import models

DATA_DIR = Path(__file__).resolve().parent / "data"
GHAZALS_PATH = DATA_DIR / "ghazals.json"
TERJEE_PATH = DATA_DIR / "terjee.json"
ZAND_PATH = DATA_DIR / "zand.json"


def import_ghazals(db):
    existing = db.query(models.Ghazal).count()
    if existing > 0:
        print(f"Ghazals already imported ({existing} records). Skipping.")
        return

    with open(GHAZALS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    records = [
        models.Ghazal(number=int(num), title=entry["t"], couplets=entry["c"])
        for num, entry in data.items()
    ]
    db.bulk_save_objects(records)
    db.commit()
    print(f"Imported {len(records)} ghazals.")


def import_terjee(db):
    existing = db.query(models.Terjee).count()
    if existing > 0:
        print(f"Terjee bands already imported ({existing} records). Skipping.")
        return

    with open(TERJEE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    bands = data[0]["bands"]
    records = [
        models.Terjee(number=band["num"], couplets=band["couplets"])
        for band in bands
    ]
    db.bulk_save_objects(records)
    db.commit()
    print(f"Imported {len(records)} terjee bands.")


def import_zand(db):
    existing = db.query(models.Zand).count()
    if existing > 0:
        print(f"Zand already imported ({existing} records). Skipping.")
        return

    with open(ZAND_PATH, encoding="utf-8") as f:
        data = json.load(f)

    records = [
        models.Zand(
            number=int(item["id"]),
            title=item["title"],
            type=item["type"],
            content=item.get("content") or None,
        )
        for item in data
    ]
    db.bulk_save_objects(records)
    db.commit()
    print(f"Imported {len(records)} zand sections.")


if __name__ == "__main__":
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        import_ghazals(db)
        import_terjee(db)
        import_zand(db)
        print("Done.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()
