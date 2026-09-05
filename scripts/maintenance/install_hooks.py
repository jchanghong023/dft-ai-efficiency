"""Install this repository's public-document pre-commit check using Python 3.11+."""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
MARKER = "# dft-ai-efficiency: public Markdown line limit"


def install(root=ROOT):
    if sys.version_info < (3, 11): raise ValueError("Python 3.11+ is required")
    directory = subprocess.check_output(["git", "-C", str(root), "rev-parse", "--git-path", "hooks"], text=True).strip()
    folder = Path(directory)
    if not folder.is_absolute(): folder = root / folder
    target = folder / "pre-commit"
    if target.is_symlink(): raise ValueError("Existing pre-commit hook is a symlink; left unchanged")
    if target.exists() and MARKER not in target.read_text(encoding="utf-8"):
        raise ValueError(f"Existing unrelated hook left unchanged: {target}")
    executable = Path(sys.executable).as_posix()
    # Git for Windows handles quoted interpreter paths. Linux installations use
    # the explicitly required python3.11 command if the current path has spaces.
    if " " in executable:
        executable = f'"{executable}"' if sys.platform == "win32" else "/usr/bin/env python3.11"
    body = f'#!{executable}\n{MARKER}\n' + '''import pathlib
import subprocess
import sys
root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
raise SystemExit(subprocess.call([sys.executable, "-B", str(pathlib.Path(root) / "tests/check_docs.py"), "--staged"]))
'''
    folder.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8", newline="\n")
    target.chmod(0o755)
    print(f"INSTALLED public-document pre-commit check: {target}")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    try: install(parser.parse_args().repo.resolve())
    except (ValueError, OSError, subprocess.CalledProcessError) as error: raise SystemExit(str(error))
