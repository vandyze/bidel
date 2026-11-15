import os
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.chdir(_tmp)  # main.py می‌سازد: media/ در cwd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    import main
    with TestClient(main.app) as c:
        yield c


def _make_user(username, user_id=None):
    import models
    from auth import hash_password
    from database import SessionLocal
    db = SessionLocal()
    try:
        u = models.User(id=user_id, username=username, email=f"{username}@t.local",
                        phone=None, hashed_password=hash_password("secret123"))
        db.add(u)
        db.commit()
        db.refresh(u)
        return u.id
    finally:
        db.close()


@pytest.fixture(scope="session")
def tokens(client):
    from auth import create_access_token
    admin = _make_user("admin", user_id=1)
    normal = _make_user("normal", user_id=2)
    return {
        "admin": {"Authorization": "Bearer " + create_access_token({"sub": str(admin)})},
        "normal": {"Authorization": "Bearer " + create_access_token({"sub": str(normal)})},
    }
