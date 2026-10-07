"""Serve the built website (build/web) locally the way Vercel will serve it.

Applies the same rewrite (every unknown path -> index.html) and the same response headers as
vercel.json, so routing and the Content-Security-Policy can be checked before deploying.
Local preview only: binds to 127.0.0.1 and uses only the standard library.

    flutter build web --release --csp --no-web-resources-cdn --dart-define-from-file=config/<file>.json
    python tool/serve_web.py [--port 8080]
"""

from __future__ import annotations

import argparse
import functools
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = APP_DIR / "build" / "web"
ALL_PATHS = "/(.*)"


def load_vercel_config() -> list[tuple[str, str]]:
    """Return the headers vercel.json applies; refuse rules this preview cannot reproduce."""
    config = json.loads((APP_DIR / "vercel.json").read_text(encoding="utf-8"))
    rewrites = config.get("rewrites", [])
    if rewrites != [{"source": ALL_PATHS, "destination": "/index.html"}]:
        raise SystemExit("serve_web: vercel.json rewrites changed; update this preview to match")
    headers: list[tuple[str, str]] = []
    for rule in config.get("headers", []):
        if rule["source"] != ALL_PATHS:
            raise SystemExit(f"serve_web: unsupported header source {rule['source']!r}")
        headers += [(h["key"], h["value"]) for h in rule["headers"]]
    return headers


class SiteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, extra_headers: list[tuple[str, str]], **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.extra_headers = extra_headers
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def send_head(self):  # type: ignore[no-untyped-def]
        # Vercel serves existing files first and rewrites everything else to index.html.
        path = Path(self.translate_path(self.path))
        if not path.is_file():
            self.path = "/index.html"
        return super().send_head()

    def end_headers(self) -> None:
        for key, value in self.extra_headers:
            # HSTS is meaningless over plain http on localhost.
            if key != "Strict-Transport-Security":
                self.send_header(key, value)
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    if not (SITE_DIR / "index.html").is_file():
        raise SystemExit(f"serve_web: {SITE_DIR} has no build; run `flutter build web` first")
    handler = functools.partial(SiteHandler, extra_headers=load_vercel_config())
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Serving {SITE_DIR} at http://localhost:{args.port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
