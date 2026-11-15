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


def test_password_change_requires_current_password(client, tokens):
    h = tokens["normal"]
    assert client.put("/auth/me", json={"password": "newpass1"}, headers=h).status_code == 400
    assert client.put("/auth/me", json={"password": "newpass1", "current_password": "wrong"}, headers=h).status_code == 400
    assert client.put("/auth/me", json={"password": "newpass1", "current_password": "secret123"}, headers=h).status_code == 200
    assert client.post("/auth/login", json={"login_id": "normal", "password": "newpass1"}).status_code == 200


def test_logout_revokes_tokens_and_refresh_works(client):
    from auth import create_access_token
    import models
    from database import SessionLocal
    db = SessionLocal()
    from conftest import _make_user
    uid = _make_user("revoke_me")
    h = {"Authorization": "Bearer " + create_access_token({"sub": str(uid), "ver": 0})}
    r = client.post("/auth/refresh", headers=h)
    assert r.status_code == 200
    h2 = {"Authorization": "Bearer " + r.json()["access_token"]}
    assert client.get("/auth/me", headers=h2).status_code == 200
    assert client.post("/auth/logout", headers=h).status_code == 200
    assert client.get("/auth/me", headers=h).status_code == 401
    assert client.get("/auth/me", headers=h2).status_code == 401
    db.close()


def test_password_change_returns_fresh_token_and_kills_old(client):
    from auth import create_access_token
    from conftest import _make_user
    uid = _make_user("pw_changer")
    old = {"Authorization": "Bearer " + create_access_token({"sub": str(uid)})}  # بدون ver = قدیمی
    r = client.put("/auth/me", json={"password": "another1", "current_password": "secret123"}, headers=old)
    assert r.status_code == 200
    new = {"Authorization": "Bearer " + r.json()["access_token"]}
    assert client.get("/auth/me", headers=new).status_code == 200
    assert client.get("/auth/me", headers=old).status_code == 401
