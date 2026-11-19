#!/usr/bin/env python3
"""سرور محلی فرانت‌اند با پشتیبانی از مسیرهای SPA.

python3 -m http.server برای مسیرهایی مثل /chahar یا /ghazals فایل پیدا نمی‌کند و 404
برمی‌گرداند. این سرور همان فایل‌های استاتیک را سرو می‌کند، اما برای مسیرهای بدون پسوند
به index.html برمی‌گردد تا ناوبری SPA در محیط توسعه هم مثل nginx کار کند.
"""
import argparse
import os
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")


class SpaHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)

        # /bidel-dehlavi بدون ریدایرکت به نسخهٔ اسلش‌دار
        if path in ("/bidel-dehlavi", "/bidel-dehlavi/"):
            self.path = "/bidel-dehlavi/index.html"
            return super().do_GET()
        if path in ("/en/bidel-dehlavi", "/en/bidel-dehlavi/"):
            self.path = "/en/bidel-dehlavi/index.html"
            return super().do_GET()
        if path in ("/hi/bidel-dehlavi", "/hi/bidel-dehlavi/"):
            self.path = "/hi/bidel-dehlavi/index.html"
            return super().do_GET()
        if path in ("/en", "/en/"):
            self.path = "/en/index.html"
            return super().do_GET()
        if path in ("/hi", "/hi/"):
            self.path = "/hi/index.html"
            return super().do_GET()

        fs_path = os.path.normpath(os.path.join(ROOT, path.lstrip("/")))
        if os.path.isfile(fs_path) or os.path.isdir(fs_path):
            return super().do_GET()

        # مسیرهای بدون پسوند = مسیر SPA
        if not os.path.splitext(path)[1]:
            self.path = "/index.html"
            return super().do_GET()

        return super().do_GET()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("port", nargs="?", type=int, default=3001)
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.bind, args.port), SpaHandler)
    print(f"Frontend: http://{args.bind}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
