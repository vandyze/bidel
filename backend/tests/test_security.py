import pytest

KHANESH = {"title": "t", "slug": "s1", "content": "<p>hi</p><script>alert(1)</script>",
           "terjee_number": 1, "instructor": "i"}


def test_admin_routes_reject_anonymous(client):
    assert client.post("/khanesh", json=KHANESH).status_code in (401, 403)


def test_admin_routes_reject_normal_user(client, tokens):
    r = client.post("/khanesh", json=KHANESH, headers=tokens["normal"])
    assert r.status_code == 403
    assert client.delete("/pajvak/x", headers=tokens["normal"]).status_code == 403


def test_khanesh_html_is_sanitized(client, tokens):
    import models
    from database import SessionLocal
    db = SessionLocal()
    db.add(models.Terjee(number=1, couplets=[["a", "b"]]))
    db.commit()
    db.close()
    r = client.post("/khanesh", json=KHANESH, headers=tokens["admin"])
    assert r.status_code == 200, r.text
    body = client.get("/khanesh/s1").json()["content"]
    assert "<script" not in body and "<p>hi</p>" in body


@pytest.mark.parametrize("name", ["../../main.py", "a/b.jpg", "x.jpg/../../y"])
def test_pajvak_rejects_path_traversal(client, tokens, name):
    data = {"title": "t", "slug": "p1", "ref_type": "band", "cover_filename": name}
    assert client.post("/pajvak", json=data, headers=tokens["admin"]).status_code == 422


def test_otp_token_is_not_a_login_token(client):
    from auth import create_access_token
    tok = create_access_token({"sub": "09120000000", "purpose": "login"})
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


def test_login_is_rate_limited(client):
    codes = [client.post("/auth/login", json={"login_id": "nobody", "password": "x"}).status_code
             for _ in range(10)]
    assert 429 in codes


def test_cors_rejects_foreign_origin(client):
    r = client.get("/", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_weak_secret_key_refused():
    import subprocess, sys, os
    env = {**os.environ, "SECRET_KEY": "short"}
    out = subprocess.run([sys.executable, "-c", "import auth"], env=env, cwd=os.path.join(os.path.dirname(__file__), ".."),
                         capture_output=True, text=True)
    assert out.returncode != 0
