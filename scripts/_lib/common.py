"""Shared public-repository utilities (Python 3.11+, standard library)."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
import sys

sys.dont_write_bytecode = True
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required")
ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / ".tmp"
BINS = {"omp": "dist/omp/omp", "claude-code": "dist/claude-code/claude"}


def wrap_tables(body: str) -> str:
    """Wrap outer Markdown tables, including tables with HTML attributes."""
    depth = 0

    def replace(match):
        nonlocal depth
        tag = match.group()
        if tag.lower().startswith("</"):
            if depth == 0:
                return tag
            depth -= 1
            return tag + ("</div>" if depth == 0 else "")
        depth += 1
        return ('<div class="table-wrap">' if depth == 1 else "") + tag

    return re.sub(r"<table\b[^>]*>|</table\s*>", replace, body, flags=re.IGNORECASE)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def regular(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Not a regular source file: {path}")


def binary_metadata(root: Path, product: str):
    path = root / BINS[product]
    regular(path)
    with path.open("rb") as stream:
        header = stream.read(128)
    if header.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise ValueError(f"LFS pointer, not binary: {path}; run git lfs pull in the online checkout")
    if not header.startswith(b"\x7fELF"):
        raise ValueError(f"Not a Linux ELF binary: {path}")
    if len(header) < 64 or header[4:7] != b"\x02\x01\x01":
        raise ValueError(f"Invalid/unsupported ELF header: {path}")
    arch = {62: "x64", 183: "arm64"}.get(int.from_bytes(header[18:20], "little"))
    if arch is None:
        raise ValueError(f"Unsupported ELF architecture: {path}")
    return {"platform": f"linux-{arch}", "size": path.stat().st_size, "sha256": sha256(path)}


def atomic_copy(source: Path, target: Path, mode=0o644):
    """Same-filesystem staging is required for atomic replacement, no backup state."""
    import shutil
    import tempfile
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".dft-sync-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as out, source.open("rb") as src:
            shutil.copyfileobj(src, out)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(name, mode)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)
