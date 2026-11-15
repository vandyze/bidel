"""پاک‌سازی HTML ورودی (مثلاً متن خوانش‌ها) با فهرست سفید تگ‌ها."""
import html as html_lib
import re
from html.parser import HTMLParser

ALLOWED_TAGS = {
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "em", "i",
    "u", "ul", "ol", "li", "blockquote", "a", "span", "div", "sup", "sub",
}
VOID_TAGS = {"br", "hr"}
DROP_CONTENT = {"script", "style", "iframe", "object", "embed", "noscript", "template"}
SAFE_URL = re.compile(r"^(https?://|mailto:|/|#)", re.I)


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT:
            self.skip += 1
            return
        if self.skip or tag not in ALLOWED_TAGS:
            return
        attr_s = ""
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v and SAFE_URL.match(v.strip()):
                    attr_s = f' href="{html_lib.escape(v.strip(), quote=True)}" rel="noopener noreferrer"'
        self.out.append(f"<{tag}{attr_s}>")

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html_lib.escape(data, quote=False))


def sanitize_html(source: str) -> str:
    p = _Sanitizer()
    p.feed(source or "")
    p.close()
    return "".join(p.out)
