"""Verify public source, generated portal, team formats and release binaries offline."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse
import csv
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._lib.common import ROOT, BINS, binary_metadata, read_json, sha256


class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids = set(); self.links = []; self.resources = []; self.title = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            if attrs["id"] in self.ids:
                raise ValueError(f"Duplicate HTML id {attrs['id']}")
            self.ids.add(attrs["id"])
        if tag == "title": self.title = True
        if tag == "a" and "href" in attrs: self.links.append(attrs["href"])
        if tag in {"script", "img", "iframe", "audio", "video", "source"} and "src" in attrs:
            self.resources.append(attrs["src"])
        if tag == "link" and "href" in attrs: self.resources.append(attrs["href"])


def verify_site(root=ROOT):
    site = root / "site"
    manifest = read_json(site / "build-manifest.json")
    for section, base in (("sources", root), ("files", site)):
        for relative, expected in manifest[section].items():
            path = base / relative
            if not path.resolve().is_relative_to(base.resolve()) or "yellow" in Path(relative).parts:
                raise ValueError(f"Invalid public manifest path: {relative}")
            if path.is_symlink() or sha256(path) != expected:
                raise ValueError(f"Changed or invalid {section} file: {relative}; rebuild site")
    actual = {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()}
    if actual != set(manifest["files"]) | {"build-manifest.json"}:
        raise ValueError("Unexpected or missing generated site files")
    pages = {}
    for relative in manifest["files"]:
        if relative.endswith(".html"):
            path = site / relative
            parser = Page(); parser.feed(path.read_text(encoding="utf-8"))
            if not parser.title or "main" not in parser.ids:
                raise ValueError(f"Missing page structure: {relative}")
            pages[path.resolve()] = parser
    for path, page in pages.items():
        for link in page.resources + page.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                if link in page.resources or parsed.scheme not in {"http", "https", "mailto"}:
                    raise ValueError(f"External/unsafe runtime resource: {path}: {link}")
                continue
            if parsed.path.startswith("/"):
                raise ValueError(f"Absolute local link: {link}")
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not target.is_relative_to(site.resolve()) or not target.is_file():
                raise ValueError(f"Broken/outside link: {path}: {link}")
            if parsed.fragment and target in pages and unquote(parsed.fragment) not in pages[target].ids:
                raise ValueError(f"Broken fragment: {path}: {link}")
    for asset in (site / "assets").rglob("*"):
        if asset.suffix not in {".css", ".js"} or asset.name == "search-data.js":
            continue
        source = asset.read_text(encoding="utf-8")
        if (asset.suffix == ".css" and re.search(r"@import|url\s*\(", source)
                or asset.suffix == ".js" and re.search(r"\b(fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(", source)):
            raise ValueError(f"Unexpected runtime resource loader: {asset.name}")
    raw = (site / "assets/search-data.js").read_text(encoding="utf-8")
    index = json.loads(raw.removeprefix("window.DFT_SEARCH = ").removesuffix(";\n").replace("<\\/", "</"))
    if {entry["url"] for entry in index} != {p.relative_to(site.resolve()).as_posix() for p in pages if p != (site / "index.html").resolve()}:
        raise ValueError("Search does not cover every article")
    for entry in index:
        target = (site / entry["url"]).resolve()
        identifiers = set()
        for section in entry.get("sections", []):
            if section["id"] in identifiers or section["id"] not in pages[target].ids or not section["title"]:
                raise ValueError(f"Invalid search section: {entry['url']} / {section['id']}")
            identifiers.add(section["id"])
    print(f"PASS portal: {len(pages)} pages, links/fragments/resources, full search index, unchanged public inputs")


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"Missing frontmatter: {path}")
    header, body = text[4:].split("\n---\n", 1)
    # Team files deliberately use simple scalar frontmatter compatible with OMP.
    fields = dict(line.split(":", 1) for line in header.splitlines() if line.strip())
    return {key: value.strip() for key, value in fields.items()}, body


def verify_content(root=ROOT):
    meta = read_json(root / "portal/metadata/omp.json")
    for kind in ("commands", "cli", "agents", "tools", "extras"):
        entries = meta["templates"] + meta["modules"] if kind == "extras" else meta[kind]
        with (root / f"portal/catalog/{kind}.tsv").open(encoding="utf-8", newline="") as stream:
            explanations = list(csv.DictReader(stream, delimiter="\t"))
        if {e["name"] for e in entries} != {e["name"] for e in explanations} or len(entries) != len(explanations):
            raise ValueError(f"Missing/duplicate explanation in {kind}")
        if any(not value for e in explanations for value in e.values()):
            raise ValueError(f"Empty explanation in {kind}")
    for skill in ("generate-unit-tests", "generate-dft-circuit"):
        path = root / f"omp/skills/{skill}/SKILL.md"
        fields, body = frontmatter(path)
        if fields.get("name") != skill or not fields.get("description") or fields.get("hide") == "true" or fields.get("disable-model-invocation") == "true":
            raise ValueError(f"Invalid/nonautomatic Skill: {skill}")
        for relative in re.findall(r"\]\(([^)]+)\)", body):
            if not (path.parent / relative).is_file():
                raise ValueError(f"Missing Skill reference: {relative}")
    for name in ("document-worker", "coding-worker", "verification-worker"):
        fields, _ = frontmatter(root / f"omp/agents/{name}.md")
        if fields.get("name") != name or not fields.get("description") or not fields.get("tools"):
            raise ValueError(f"Invalid OMP Worker: {name}")
        if name == "document-worker" and set(fields["tools"].split(", ")) - {"read", "grep", "glob", "wiki"}:
            raise ValueError("Document Worker has non-readonly tools")
    fields, body = frontmatter(root / "omp/commands/code-and-verify.md")
    if not fields.get("description") or "$ARGUMENTS" not in body:
        raise ValueError("Invalid OMP command template")
    print("PASS metadata explanations, 2 automatic Skills, 3 native Workers, command template")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-only", action="store_true")
    args = parser.parse_args()
    verify_content(); verify_site()
    if not args.site_only:
        for product in BINS:
            meta = binary_metadata(ROOT, product)
            print(f"PASS binary {product} {meta['platform']} ELF; SHA256 {meta['sha256']}")


if __name__ == "__main__":
    main()
