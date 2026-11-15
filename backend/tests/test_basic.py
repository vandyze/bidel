from sanitize import sanitize_html


def test_sanitize_strips_dangerous_markup():
    out = sanitize_html('<p onclick="x">a</p><a href="javascript:1">l</a><img src=x onerror=1>')
    assert "onclick" not in out and "javascript:" not in out and "<img" not in out


def test_root(client):
    assert client.get("/").status_code == 200


def test_search_normalizes_arabic_letters(client):
    import models
    from database import SessionLocal
    db = SessionLocal()
    db.add(models.Ghazal(number=1, title="t", couplets=[["عشق بیدل", "دل"]]))
    db.commit()
    db.close()
    r = client.get("/poems/search", params={"q": "عشق", "type": "g"})
    assert r.json()["count"] == 1


def test_sitemap_uses_database_counts(client):
    xml = client.get("/sitemap.xml").text
    assert "/ghazal/1<" in xml and "/ghazal/2<" not in xml
    assert client.get("/sitemap.xml").headers["cache-control"].startswith("public")


def test_bot_page_has_og_and_escapes(client):
    import models
    from database import SessionLocal
    db = SessionLocal()
    db.add(models.Keyword(word="<x>", meaning='"q"'))
    db.commit()
    db.close()
    html = client.get("/keywords/%3Cx%3E/html", params={"preview": 1}).text
    assert "<x>" not in html.replace("&lt;x&gt;", "") and 'property="og:title"' in html
