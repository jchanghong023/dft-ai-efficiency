"""Serve the offline portal on all IPv4 interfaces, port 9333, using Python 3.11+."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HOST = "0.0.0.0"
PORT = 9333
MOUNTS = ("site", "yellow/.site", "yellow/docs")


def resolve_file(root: Path, url: str) -> Path | None:
    """Map website URLs without exposing other repository files or symlinks."""
    try:
        path = unquote(urlsplit(url).path, errors="strict")
        if not path.startswith("/") or any(c in path for c in ("\\", "\x00", ":")):
            return None
        relative = path.lstrip("/")
        mount = next((m for m in MOUNTS if relative == m or relative.startswith(m + "/")), None)
        if mount is None:
            return None
        remainder = relative[len(mount):].strip("/")
        if any(part.startswith(".") for part in remainder.split("/") if part):
            return None
        target = root / relative
        if any(p.is_symlink() for p in (target, *target.parents) if p != root and root in p.parents):
            return None
        resolved = target.resolve()
        if not resolved.is_relative_to(root / mount):
            return None
        return resolved
    except (ValueError, OSError, UnicodeError):
        return None


class SiteHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".md": "text/plain; charset=utf-8",
    }

    def __init__(self, *args, root: Path, **kwargs):
        self.root = root
        super().__init__(*args, directory=str(root), **kwargs)

    def send_head(self):
        if urlsplit(self.path).path == "/":
            self.send_response(302)
            self.send_header("Location", "/site/index.html")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        self.file_path = resolve_file(self.root, self.path)
        if self.file_path is None:
            self.send_error(404, "Not found")
            return None
        # SimpleHTTPRequestHandler otherwise follows an index symlink in a directory.
        if self.file_path.is_dir():
            for name in ("index.html", "index.htm"):
                if (self.file_path / name).is_symlink():
                    self.send_error(404, "Not found")
                    return None
        return super().send_head()

    def translate_path(self, path):
        return str(self.file_path)

    def list_directory(self, path):
        self.send_error(404, "Not found")
        return None

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def create_server(root: Path = ROOT, port: int = PORT) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((HOST, port), partial(SiteHandler, root=root.resolve()))


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    if sys.version_info < (3, 11):
        print("Python 3.11+ is required.", file=sys.stderr)
        return 1
    if not (ROOT / "site/index.html").is_file():
        print("Missing site/index.html. Run scripts/build_site.py first.", file=sys.stderr)
        return 1
    try:
        server = create_server()
    except OSError as exc:
        print(f"Cannot listen on {HOST}:{PORT}: {exc}. Check whether port {PORT} is in use.", file=sys.stderr)
        return 1
    with server:
        print(
            f"Listening on {HOST}:{PORT}\n"
            f"DFT portal (local): http://127.0.0.1:{PORT}/\n"
            f"Other machines: http://<server-ip>:{PORT}/\nPress Ctrl+C to stop.",
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
