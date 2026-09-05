"""Update the two Linux binaries in dist using only Python 3.11+ stdlib."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
API = "https://api.github.com/repos/jchanghong023/oh-my-pi/releases/latest"
CLAUDE = "https://downloads.claude.ai/claude-code-releases"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "dft-ai-efficiency-maintainer"})
    return urllib.request.urlopen(request, timeout=60)


def read_text(url):
    with fetch(url) as response:
        return response.read().decode("utf-8")


def releases(arch):
    platform = f"linux-{arch}"
    release = json.loads(read_text(API))
    if release["draft"] or release["prerelease"]:
        raise ValueError("Not a formal OMP release")
    assets = {item["name"]: item for item in release["assets"]}
    asset = assets[f"omp-{platform}"]
    sums = read_text(assets["SHA256SUMS.txt"]["browser_download_url"])
    entries = {line.split()[-1].lstrip("*"): line.split()[0]
               for line in sums.splitlines() if line.strip()}
    expected = entries[asset["name"]]
    if asset.get("digest") and asset["digest"] != "sha256:" + expected:
        raise ValueError("GitHub digest disagrees with SHA256SUMS")
    omp = ("omp/omp", release["tag_name"], asset["browser_download_url"], expected, asset["size"])

    version = read_text(CLAUDE + "/stable").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid Claude stable version")
    manifest = json.loads(read_text(f"{CLAUDE}/{version}/manifest.json"))
    if manifest["version"] != version:
        raise ValueError("Claude manifest version mismatch")
    item = manifest["platforms"][platform]
    return [omp, ("claude-code/claude", version, f"{CLAUDE}/{version}/{platform}/claude",
                  item["checksum"], item["size"])]


def download(url, target, expected, size, arch):
    if not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("Missing publisher SHA256")
    print(f"DOWNLOAD {url}", flush=True)
    with fetch(url) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)
    with target.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        stream.seek(0)
        header = stream.read(64)
    if digest != expected or target.stat().st_size != size:
        raise ValueError(f"Publisher checksum/size mismatch: {target.name}")
    machine = 62 if arch == "x64" else 183
    if (len(header) < 64 or header[:7] != b"\x7fELF\x02\x01\x01"
            or int.from_bytes(header[18:20], "little") != machine):
        raise ValueError(f"Not the expected Linux {arch} ELF binary: {target.name}")
    target.chmod(0o755)


def update(arch, root=ROOT):
    artifacts = releases(arch)
    temporary = root / ".tmp"
    temporary.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="binaries-", dir=temporary) as folder:
        stage = Path(folder)
        # Verify both downloads before replacing either existing binary.
        for relative, version, url, expected, size in artifacts:
            download(url, stage / Path(relative).name, expected, size, arch)
        for relative, version, *_ in artifacts:
            target = root / "dist" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage / target.name, target)
            print(f"UPDATED {relative} {version} linux-{arch}", flush=True)


def main():
    if sys.version_info < (3, 11):
        raise SystemExit("Python 3.11+ is required")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", choices=["x64", "arm64"], default="x64")
    update(parser.parse_args().arch)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"FAIL {exc}; any preceding UPDATED lines have already been applied")
