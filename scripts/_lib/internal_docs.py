"""Render local company Markdown into ignored yellow/.site, never public site/."""
from __future__ import annotations
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from markdown.extensions.toc import slugify_unicode
from markdown_it import MarkdownIt
from scripts._lib.common import read_json, write_json, wrap_tables
from scripts._lib.search import section_index


class LocalMarkdown(HTMLParser):
    """Keep readable Markdown HTML, local resources and ordinary links, not active HTML."""
    tags = set("p br hr h1 h2 h3 h4 h5 h6 a img pre code blockquote ul ol li strong em del s table thead tbody tfoot tr th td dl dt dd div span details summary sup sub kbd input".split())
    void = {"br", "hr", "img", "input"}
    blocked = {"script", "style", "iframe", "object", "embed", "svg", "math"}

    def __init__(self, source, docs, destinations):
        super().__init__(convert_charrefs=False)
        self.source, self.docs, self.destinations = source, docs, destinations
        self.parts, self.skip = [], []

    def url(self, value, image=False):
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc:
            return value if not image and parsed.scheme in {"http", "https", "mailto"} else None
        if not parsed.path:
            return value if not image else None
        # Relative links are resolved against the original Markdown, not its HTML output.
        target = (self.source.parent / unquote(parsed.path).replace("\\", "/")).resolve()
        if not target.is_relative_to(self.docs) or not target.is_file():
            return None
        if not image and target in self.destinations:
            path = self.destinations[target]
        else:
            path = "../docs/" + quote(target.relative_to(self.docs).as_posix(), safe="/")
        return urlunsplit(("", "", path, parsed.query, unquote(parsed.fragment)))

    def handle_starttag(self, tag, attrs):
        if self.skip:
            if tag in self.blocked: self.skip.append(tag)
            return
        if tag in self.blocked:
            self.skip.append(tag); return
        if tag not in self.tags: return
        attrs = dict(attrs)
        kept = []
        for name in ("id", "class", "title", "colspan", "rowspan", "start", "open"):
            if name in attrs: kept.append((name, attrs[name] or ""))
        if tag == "a" and "href" in attrs:
            href = self.url(attrs["href"] or "")
            if href is not None: kept.append(("href", href))
        if tag == "img":
            src = self.url(attrs.get("src") or "", image=True)
            if src is None:
                self.parts.append('<span class="missing-image">' + html.escape(attrs.get("alt") or "图片未在本地提供") + '</span>')
                return
            kept += [("src", src), ("alt", attrs.get("alt") or ""), ("loading", "lazy")]
        if tag == "input":
            if attrs.get("type") != "checkbox": return
            kept += [("type", "checkbox"), ("disabled", "")]
            if "checked" in attrs: kept.append(("checked", ""))
        self.parts.append("<" + tag + "".join(f' {key}="{html.escape(value, quote=True)}"' for key, value in kept) + ">")

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[-1]: self.skip.pop()
        elif tag in self.tags and tag not in self.void:
            self.parts.append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void: self.handle_endtag(tag)

    def handle_data(self, data):
        if not self.skip: self.parts.append(html.escape(data))

    def handle_entityref(self, name):
        if not self.skip: self.parts.append(f"&{name};")

    def handle_charref(self, name):
        if not self.skip: self.parts.append(f"&#{name};")


def render_markdown(raw, text_converter):
    # Large imported manuals contain long escape-heavy paragraphs. Token parsing
    # avoids Python-Markdown's repeated inline string replacement on those blocks.
    renderer = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])
    environment = {}
    tokens = renderer.parse(raw, environment)
    used, headings = set(), []
    for index, token in enumerate(tokens):
        if token.type != "heading_open": continue
        title = text_converter(renderer.renderer.render(tokens[index + 1:index + 2], renderer.options, environment))
        slug = slugify_unicode(title, "-") or "section"
        identifier, suffix = slug, 1
        while identifier in used:
            identifier = f"{slug}_{suffix}"; suffix += 1
        used.add(identifier); token.attrSet("id", identifier)
        if int(token.tag[1:]) <= 3:
            headings.append(f'<li class="toc-{token.tag}"><a href="#{html.escape(identifier, quote=True)}">{html.escape(title)}</a></li>')
    body = renderer.renderer.render(tokens, renderer.options, environment)
    toc = '<div class="toc"><ul>' + "".join(headings) + '</ul></div>' if headings else ""
    return body, toc


def build_internal(root, template, shared, text_converter, *, max_lines):
    yellow = root / "yellow"
    docs = yellow / "docs"
    output = yellow / ".site"
    if any(path.is_symlink() for path in (yellow, docs, output)):
        raise ValueError("Internal document paths must not be symlinks")
    sources = []
    if docs.exists():
        if not docs.is_dir(): raise ValueError("yellow/docs is not a directory")
        for path in docs.rglob("*"):
            if path.is_symlink(): raise ValueError("Symlinks in internal documents are not supported")
            if path.is_file() and path.suffix.lower() == ".md": sources.append(path)
    sources.sort(key=lambda path: path.relative_to(docs).as_posix().casefold())
    selected, skipped = [], []
    for source in sources:
        # Count physical lines, including blank lines. Universal-newline reading
        # handles LF/CRLF/CR and counts a final unterminated line exactly once.
        with source.open(encoding="utf-8-sig") as stream:
            lines = sum(1 for _ in stream)
        if lines <= max_lines:
            selected.append(source)
        else:
            skipped.append(dict(path=source.relative_to(docs).as_posix(), lines=lines))
    sources = selected
    docs = docs.resolve()
    destinations = {path.resolve(): "doc-" + hashlib.sha256(path.relative_to(docs).as_posix().encode()).hexdigest()[:20] + ".html" for path in sources}
    navigation = [dict(name=path.relative_to(docs).as_posix(), href=destinations[path.resolve()]) for path in sources]
    stage_root = root / ".tmp/internal-build"
    stage_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=stage_root) as temporary:
        stage = Path(temporary)
        common = dict(shared, home=False, base="../../site/", section="internal", section_title="内部文档",
                      area_key="internal", area_title="内部文档", area_navigation=[],
                      internal_page=True, internal_files=navigation, internal_home="index.html", search_data="search-data.js")
        intro = f'<h1>内部文档</h1><p>收录 {len(sources)} 个行数不超过 {max_lines} 的 Markdown 文件。选择左侧文件开始阅读，也可按文件名筛选或搜索正文。</p>'
        if skipped:
            intro += f'<p>已跳过 {len(skipped)} 个超过行数限制的文档，原始文件仍保留。</p>'
        if not sources and skipped:
            intro += '<p>当前没有满足行数条件的文档。</p>'
        elif not sources:
            intro += '<p>将文档放入 <code>yellow/docs/</code> 后重新运行网站构建，即可在这里浏览。</p>'
        (stage / "index.html").write_text(template.render(title="内部文档", body=intro, toc="", active_document="", **common), encoding="utf-8")
        search = []
        for number, source in enumerate(sources, 1):
            raw = source.read_text(encoding="utf-8-sig")
            rendered, toc = render_markdown(raw, text_converter)
            cleaner = LocalMarkdown(source.resolve(), docs, destinations)
            cleaner.feed(rendered); cleaner.close()
            body = "".join(cleaner.parts)
            if not re.search(r"<h1(?:\s|>)", body): body = f"<h1>{html.escape(source.stem)}</h1>" + body
            body = wrap_tables(body)
            filename = source.relative_to(docs).as_posix()
            destination = destinations[source.resolve()]
            page = template.render(title=source.stem, body=body, toc=toc, active_document=destination,
                original_document="../docs/" + quote(filename, safe="/"), document_name=filename, **common)
            (stage / destination).write_text(page, encoding="utf-8")
            search.append(dict(title=filename, area="internal", location="内部文档", text=text_converter(body), sections=section_index(body), url="../yellow/.site/" + destination))
            if number % 50 == 0:
                print(f"RENDERED internal docs: {number}/{len(sources)}", flush=True)
        (stage / "search-data.js").write_text("window.DFT_SEARCH = " + json.dumps(search, ensure_ascii=False).replace("</", "<\\/") + ";\n", encoding="utf-8")
        (stage / "entry.js").write_text("window.DFT_INTERNAL_READY = true;\n", encoding="utf-8")
        files = sorted(path.name for path in stage.iterdir())
        write_json(stage / "manifest.json", dict(files=files, documents=len(sources), max_lines=max_lines, skipped=skipped))
        output.mkdir(parents=True, exist_ok=True)
        old = read_json(output / "manifest.json")["files"] if (output / "manifest.json").exists() else []
        for filename in old:
            target = output / filename
            if target.parent != output or not target.resolve().is_relative_to(output.resolve()):
                raise ValueError("Invalid internal output manifest path")
            if filename not in files: target.unlink(missing_ok=True)
        for path in stage.iterdir():
            target = output / path.name
            if target.is_symlink(): raise ValueError("Symlink internal output")
            shutil.copyfile(path, target)
    print(f"BUILT internal docs: {len(sources)} Markdown files (<= {max_lines} lines); skipped {len(skipped)}; output yellow/.site/ (excluded from public Git/package)")
    if skipped:
        print("SKIPPED details: yellow/.site/manifest.json; original documents and Wiki database unchanged")
    return len(sources)
