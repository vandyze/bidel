"""تبدیل نسخهٔ مارک‌داونِ «چهار عنصر» به بخش‌های HTML برای نمایش در سایت."""
import re
from pathlib import Path


def _inline(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    return text


def _render(lines):
    out = []
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].rstrip()
        if not s.strip():
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            level = min(6, len(m.group(1)) + 1)
            out.append(f"<h{level}>{_inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        if re.match(r"^-{3,}\s*$", s.strip()):
            out.append("<hr>")
            i += 1
            continue

        if s.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            segs = [_inline(x.strip()) for x in buf if x.strip()]
            out.append("<blockquote>" + "<br>".join(segs) + "</blockquote>")
            continue

        if re.match(r"^[-*+]\s+", s.strip()):
            items = []
            while i < n:
                mm = re.match(r"^[-*+]\s+(.*)$", lines[i].strip())
                if not mm:
                    break
                items.append("<li>" + _inline(mm.group(1)) + "</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        buf = [s.strip()]
        i += 1
        while i < n:
            t = lines[i].strip()
            if not t or re.match(r"^(#{1,6}\s|>|[-*+]\s+|--+\s*$)", t):
                break
            buf.append(t)
            i += 1
        out.append("<p>" + _inline(" ".join(buf)) + "</p>")

    return "\n".join(out)


def parse_book(md_path):
    text = Path(md_path).read_text(encoding="utf-8")
    lines = text.splitlines()

    book_title = ""
    sections = []
    part_title = ""
    current = None
    seen_h1 = False

    def flush():
        nonlocal current
        if current is None:
            return
        body = [l for l in current["lines"]
                if not re.match(r"^-{3,}\s*$", l.strip())]
        html = _render(body)
        if html.strip():
            sections.append({
                "id": len(sections) + 1,
                "title": current["title"],
                "part": current["part"],
                "type": current["type"],
                "content": html,
            })
        current = None

    for line in lines:
        m1 = re.match(r"^#\s+(.*)$", line)
        m2 = re.match(r"^##\s+(.*)$", line)
        m3 = re.match(r"^###\s+(.*)$", line)

        if m1:
            flush()
            if not seen_h1:
                seen_h1 = True
                book_title = m1.group(1).strip()
                part_title = ""
                current = None
            else:
                part_title = m1.group(1).strip()
                current = {
                    "title": part_title,
                    "part": part_title,
                    "type": "goftar",
                    "lines": [],
                }
            continue

        if m2:
            flush()
            heading = m2.group(1).strip()
            current = {
                "title": heading,
                "part": part_title,
                "type": "bakhsh",
                "lines": [],
            }
            continue

        if m3:
            flush()
            heading = m3.group(1).strip()
            current = {
                "title": heading,
                "part": part_title,
                "type": "goftar",
                "lines": [],
            }
            continue

        if current is not None:
            current["lines"].append(line)

    flush()

    if sections and not sections[0]["part"]:
        sections[0]["type"] = "dibache"

    return book_title, sections
