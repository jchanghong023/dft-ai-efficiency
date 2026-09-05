"""Check public Markdown line limits, including the exact Git index at commit time."""
from __future__ import annotations
import argparse
import io
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAX_LINES = 3000


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def check(root=ROOT, *, staged=False, max_lines=None):
    if sys.version_info < (3, 11): raise ValueError("Python 3.11+ is required")
    if max_lines is None:
        config = subprocess.run(["git", "-C", str(root), "config", "--get", "dft.docsMaxLines"], capture_output=True)
        if config.returncode not in (0, 1): raise ValueError("Cannot read repository documentation policy")
        max_lines = int(config.stdout.strip()) if config.stdout.strip() else DEFAULT_MAX_LINES
    if max_lines < 1: raise ValueError("Documentation line limit must be a positive integer")
    sources = []
    if staged:
        # Limit the query itself to public content: never enumerate/read yellow/.
        for record in git(root, "ls-files", "--stage", "-z", "--", "portal/content").split(b"\0"):
            if not record: continue
            header, name = record.split(b"\t", 1)
            path = name.decode("utf-8")
            if Path(path).suffix.lower() != ".md": continue
            mode, oid, stage = header.split()
            if stage != b"0" or mode not in (b"100644", b"100755"):
                raise ValueError(f"Unmerged or non-regular public Markdown: {path}")
            sources.append((path, git(root, "cat-file", "blob", oid.decode("ascii"))))
    else:
        for path in sorted((root / "portal/content").rglob("*")):
            if path.suffix.lower() == ".md":
                if path.is_symlink() or not path.is_file(): raise ValueError(f"Non-regular public Markdown: {path}")
                sources.append((path.relative_to(root).as_posix(), path.read_bytes()))
    failures = []
    for name, data in sources:
        lines = sum(1 for _ in io.StringIO(data.decode("utf-8-sig"), newline=None))
        if lines > max_lines: failures.append(f"{name}: {lines} lines > {max_lines}")
    if failures:
        raise ValueError("Public Markdown exceeds the line limit:\n" + "\n".join(failures) +
                         "\nSplit oversized documents into multiple linked pages, then stage them again before committing.")
    print(f"PASS public Markdown: {len(sources)} files <= {max_lines} lines ({'Git index' if staged else 'working tree'}); yellow excluded")
    return len(sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Check staged blobs, not working-tree text")
    parser.add_argument("--max-lines", type=int, help="Override git config dft.docsMaxLines (default: 3000)")
    args = parser.parse_args()
    try: check(staged=args.staged, max_lines=args.max_lines)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__": raise SystemExit(main())
