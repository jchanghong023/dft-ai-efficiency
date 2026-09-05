"""Build public file:// pages and a separate ignored local document browser."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import csv
import argparse
import html
import json
import re
import shutil
import tempfile
from pathlib import Path
from html.parser import HTMLParser
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
import markdown
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._lib.common import ROOT, TMP, read_json, write_json, sha256, wrap_tables
from scripts._lib.search import section_index

DEFAULT_MAX_LINES = 3000

TEAM_SOURCE_FILES = (
    "omp/commands/code-and-verify.md",
    "omp/agents/document-worker.md",
    "omp/agents/coding-worker.md",
    "omp/agents/verification-worker.md",
    "omp/skills/generate-unit-tests/SKILL.md",
    "omp/skills/generate-dft-circuit/SKILL.md",
    "omp/skills/generate-dft-circuit/references/tiny-base.md",
)

NAV = [("quickstart", "快速开始"), ("usage-guide", "场景使用指南"), ("cli", "CLI 与 TUI"), ("tools", "内置工具"),
       ("config", "常用配置"), ("skills", "团队 Skills 总览"), ("commands", "内置命令"),
       ("agents", "内置 Agent"), ("team", "团队公共能力"), ("faq", "FAQ / 最佳实践"),
       ("team-agents", "团队 Agent"), ("team-commands", "自定义命令"),
       ("maintenance", "维护与版本"), ("internal", "内部文档")]
AREAS = [
    dict(key="start", title="开始使用", description="从安装到日常会话，掌握 OMP 的命令、工具和配置。", label="GET STARTED",
         slugs=["quickstart", "usage-guide", "cli", "tools", "config", "commands", "agents", "faq"]),
    dict(key="team", title="团队能力", description="复用团队的开发流程、Skills 与 Worker，把需求落实到验证。", label="TEAM WORKFLOWS",
         slugs=["team", "skills", "team-agents", "team-commands", "skill-generate-unit-tests", "skill-generate-dft-circuit"]),
    dict(key="maintenance", title="维护手册", description="维护版本、文档与交付物，管理构建、校验和离线分发。", label="MAINTENANCE",
         slugs=["maintenance"]),
    dict(key="internal", title="内部文档", description="阅读本地接入的公司文档，按文件查找，按正文检索。", label="LOCAL KNOWLEDGE",
         slugs=["internal"]),
    dict(key="dft", title="DFT知识", description="从故障与扫描链到测试访问、自测试和工程调试，用交互实验理解 DFT。", label="DFT EXPLAINED",
         slugs=[]),
]


def load_curriculum(root):
    """A public, offline teaching inventory; fail on missing or unsafe lesson assets."""
    data = read_json(root / "portal/metadata/dft-curriculum.json")
    if data.get("schema") != 1 or not data.get("groups"):
        raise ValueError("Invalid DFT curriculum")
    lessons, seen = {}, set()
    for group in data["groups"]:
        if not group.get("title") or not group.get("description") or not group.get("lessons"):
            raise ValueError("Empty DFT curriculum group")
        for item in group["lessons"]:
            slug = item.get("slug", "")
            if not re.fullmatch(r"dft-[a-z0-9-]+", slug) or slug in lessons or not item.get("title") or not item.get("summary"):
                raise ValueError(f"Invalid/duplicate DFT lesson: {slug}")
            if not (root / f"portal/content/{slug}.md").is_file():
                raise ValueError(f"Missing DFT lesson: {slug}")
            if bool(item.get("lab")) != bool(item.get("script")):
                raise ValueError(f"Incomplete DFT lab: {slug}")
            if item.get("lab"):
                lab, script = item["lab"], item["script"]
                if not re.fullmatch(r"[a-z0-9-]+", lab) or lab in seen or not re.fullmatch(r"[a-z0-9-]+\.js", script):
                    raise ValueError(f"Invalid/duplicate DFT lab asset: {slug}")
                seen.add(lab)
                for path in (root / f"portal/templates/labs/{lab}.html", root / f"portal/assets/labs/{script}"):
                    if not path.is_file(): raise ValueError(f"Missing DFT lab asset: {path.name}")
            lessons[slug] = item
    return data["groups"], lessons


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    @classmethod
    def convert(cls, value):
        parser = cls(); parser.feed(value)
        return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def catalog(root, name):
    with (root / f"portal/catalog/{name}.tsv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    result = {row["name"]: row for row in rows}
    if len(rows) != len(result) or any(not value for row in rows for value in row.values()):
        raise ValueError(f"Duplicate or empty explanation field: {name}")
    return result


def public_inputs(root):
    """Never walk root or yellow; reject symlinked public inputs before reading."""
    portal = root / "portal"
    if portal.is_symlink():
        raise ValueError("Symlink portal is not a public source directory")
    paths = []
    for path in sorted(portal.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink public input: {path}")
        if path.is_file():
            paths.append(path)
    for relative in TEAM_SOURCE_FILES:
        path = root / relative
        if any(part.is_symlink() for part in (path, *path.parents) if part != root and root in part.parents):
            raise ValueError(f"Symlink team source: {path}")
        if not path.is_file():
            raise ValueError(f"Missing team source: {path}")
        paths.append(path)
    return paths


def load_content(root):
    public_inputs(root)
    snapshot = read_json(root / "portal/metadata/omp.json")
    if snapshot.get("schema") != 1 or not re.fullmatch(r"[0-9a-f]{40}", snapshot["revision"]):
        raise ValueError("Invalid metadata snapshot")
    data = {}
    for category in ("commands", "cli", "extras", "agents", "tools"):
        rows = catalog(root, category)
        entries = snapshot["templates"] + snapshot["modules"] if category == "extras" else snapshot[category]
        names = {entry["name"] for entry in entries}
        if set(rows) != names or len(names) != len(entries):
            raise ValueError(f"Inventory/explanation mismatch {category}: missing={names - set(rows)}, stale={set(rows) - names}")
        data[category] = [{**entry, **rows[entry["name"]]} for entry in entries]
    usage = read_json(root / "portal/catalog/cli-usage.json")
    if usage.get("schema") != 1 or usage.get("version") != snapshot["version"] or usage.get("revision") != snapshot["revision"]:
        raise ValueError("CLI usage explanation version differs from pinned metadata")
    if set(usage.get("entries", {})) != {item["name"] for item in data["cli"]}:
        raise ValueError("CLI usage explanation inventory mismatch")
    for item in data["cli"]:
        detail = usage["entries"][item["name"]]
        if not all(detail.get(key) for key in ("parameters", "examples", "source")):
            raise ValueError(f"Incomplete CLI usage: {item['name']}")
        source = detail["source"]
        if not source.startswith("packages/coding-agent/src/") or ".." in Path(source).parts or not re.fullmatch(r"[0-9a-f]{64}",usage.get("source_hashes", {}).get(source,"")):
            raise ValueError(f"Invalid CLI usage evidence: {item['name']}")
        item.update(parameters=detail["parameters"], example=detail["examples"], usage_source=source)
    return snapshot, data


def command_page(item, category, snapshot):
    cli = category == "cli"
    prefix = "omp " if cli else "/"
    title = prefix + item["name"]
    params = item.get("inlineHint")
    if cli:
        params = item["parameters"] + "\n\n以上为该固定版本的主要参数与使用条件；完整选项可用 `--help` 查看。"
    elif params:
        params = f"`{params}`。尖括号为必需输入，方括号为可选输入，实际效果取决于子命令。"
    else:
        params = "下列子命令选择具体操作。" if item.get("subcommands") else "无必需位置参数；需要交互选择的命令会打开对应面板。"
    url = f"{snapshot['repository']}/blob/{snapshot['revision']}/{item['source']}#L{item['line']}"
    text = f"# {title}\n\n{item['purpose']}。\n\n## 示例\n\n```{'bash' if cli else 'text'}\n{item['example']}\n```\n\n## 功能与场景\n\n{item['purpose']}。\n\n典型场景：{item['scenario']}。\n\n## 主要参数\n\n{params}\n\n"
    if item.get("aliases"):
        text += "别名：" + "、".join(f"`{prefix}{alias}`" for alias in item["aliases"]) + "。\n\n"
    if item.get("subcommands"):
        text += "源码注册的子命令：" + "、".join(f"`{sub['name']}`" for sub in item["subcommands"]) + "。\n\n"
    text += f"## 文件与状态影响\n\n{item['effects']}。\n\n示例中的路径、链接与名称须按实际任务替换；涉及写入或远端操作时，请先确认操作对象与影响。\n\n## 版本依据\n\n{snapshot['version']} · [对应注册源码]({url})。\n"
    if cli:
        usage_url = f"{snapshot['repository']}/blob/{snapshot['revision']}/{item['usage_source']}"
        text += f"\n参数与执行条件：[对应命令实现]({usage_url})。示例是使用说明，不表示已执行这些操作。\n"
    return title, text


def build(root=ROOT, include_internal=True, max_lines=DEFAULT_MAX_LINES):
    if max_lines < 1:
        raise ValueError("max_lines must be a positive integer")
    snapshot, catalogs = load_content(root)
    dft_groups, dft_lessons = load_curriculum(root)
    nav = NAV + [(item["slug"], item["title"]) for item in dft_lessons.values()]
    areas = [{**area, "slugs": list(dft_lessons) if area["key"] == "dft" else area["slugs"]} for area in AREAS]
    env = Environment(loader=FileSystemLoader(root / "portal/templates"), autoescape=select_autoescape(["html"]), undefined=StrictUndefined)
    template = env.get_template("page.html")
    navigation = [dict(slug=slug, title=title) for slug, title in nav]
    shared = dict(navigation=navigation, areas=areas, version=snapshot["version"], command_count=len(snapshot["commands"]))
    source_hashes = {path.relative_to(root).as_posix(): sha256(path) for path in public_inputs(root)}
    team_sources = {name: (root / name).read_text(encoding="utf-8") for name in TEAM_SOURCE_FILES}

    def render_team_source(match):
        name = match.group(1).strip()
        if name not in team_sources:
            raise ValueError(f"Unregistered team source: {name}")
        return (f'<p class="source-file"><code>{html.escape(name)}</code></p>'
                f'<pre data-source="{html.escape(name, quote=True)}"><code class="language-markdown">'
                f'{html.escape(team_sources[name])}</code></pre>')
    pages, indexes = {}, {}
    for category in ("commands", "cli", "extras"):
        links = ["| 名称 | 用途 |", "|---|---|"]
        for item in catalogs[category]:
            slug = ("cli-" if category == "cli" else "command-") + item["name"]
            title, source = command_page(item, category, snapshot)
            pages[slug] = (title, source, "cli" if category == "cli" else "commands")
            links.append(f"| [{title}]({slug}.html) | {item['purpose']} |")
        indexes[category] = "\n".join(links)
    indexes["tools"] = "| 工具 | 用途 | 注册类型 |\n|---|---|---|\n" + "\n".join(
        f"| `{item['name']}` | {item['purpose']} | {'隐藏 / 按模式启用' if item['hidden'] else '内置 / 可按条件启用'} |" for item in catalogs["tools"])
    for path in sorted((root / "portal/content").glob("*.md")):
        source = path.read_text(encoding="utf-8")
        title = source.splitlines()[0].removeprefix("# ")
        for category, inventory in indexes.items():
            source = source.replace(f"<!-- inventory:{category} -->", inventory)
        if "<!-- inventory:" in source:
            raise ValueError(f"Unresolved inventory marker in {path}")
        section = "skills" if path.stem.startswith("skill-") else path.stem
        if section not in dict(nav):
            raise ValueError(f"Unregistered content page: {path}")
        pages[path.stem] = (title, source, section)
    for slug, _ in nav:
        if slug not in pages:
            raise ValueError(f"Missing required section: {slug}")
    def area_context(area):
        return dict(area_key=area["key"], area_title=area["title"], area_description=area["description"], area_label=area["label"],
                    area_groups=dft_groups if area["key"] == "dft" else [],
                    area_navigation=[dict(slug=slug, title=pages[slug][0]) for slug in area["slugs"]])
    stage_root = root / ".tmp/site-build"
    stage_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=stage_root) as tmp:
        stage = Path(tmp)
        (stage / "pages").mkdir(); (stage / "assets").mkdir()
        (stage / "index.html").write_text(template.render(title="首页", home=True, base="", **shared), encoding="utf-8")
        search = []
        for area in areas:
            folder = stage / area["key"]; folder.mkdir()
            internal = area["key"] == "internal"
            intro = pages["internal"][1] if internal else area["description"]
            body = markdown.markdown(intro, extensions=["extra"])
            page = template.render(title=area["title"], body=body, toc="", home=False, base="../", section="",
                section_title=area["title"], landing=not internal, internal_page=internal, internal_entry=internal,
                **area_context(area), **shared)
            (folder / "index.html").write_text(page, encoding="utf-8")
            search.append(dict(title=area["title"], area=area["key"], location=area["title"], text=PlainText.convert(body), url=f"{area['key']}/index.html"))
        for slug, (title, source, section) in pages.items():
            area = next(area for area in areas if slug in area["slugs"] or section in area["slugs"])
            # Learning pages lead with the configured executable lab; prose stays readable below.
            markers = re.findall(r"<!--\s*(?:lab|demo):[^>]+-->", source)
            if area["key"] == "dft" and markers:
                for marker in markers:
                    source = source.replace(marker, "")
                heading, remainder = source.split("\n", 1)
                source = heading + "\n\n" + "\n".join(markers) + "\n" + remainder
            renderer = markdown.Markdown(extensions=["extra", "toc", "sane_lists"], extension_configs={"toc": {"toc_depth": "2-3"}})
            body = wrap_tables(renderer.convert(source))
            body = re.sub(r"<!--\s*team-source:(.*?)\s*-->", render_team_source, body)
            for demo in ("scan", "edt"):
                marker = f"<!-- demo:{demo} -->"
                if marker in body: body = body.replace(marker, env.get_template(f"dft-{demo}.html").render())
            lesson = dft_lessons.get(slug, {})
            lab_markers = re.findall(r"<!--\s*lab:([^>]+?)\s*-->", body)
            expected_markers = [lesson["lab"]] if lesson.get("lab") else []
            if lab_markers != expected_markers:
                raise ValueError(f"DFT lab marker/inventory mismatch: {slug}")
            if expected_markers:
                body = re.sub(r"<!--\s*lab:[^>]+?\s*-->", lambda _: env.get_template(f"labs/{lesson['lab']}.html").render(), body)
            previous, following = None, None
            if slug in dft_lessons:
                sequence = list(dft_lessons); position = sequence.index(slug)
                if position: previous = dft_lessons[sequence[position - 1]]
                if position + 1 < len(sequence): following = dft_lessons[sequence[position + 1]]
            page = template.render(title=title, body=body, toc=renderer.toc, home=False, base="../", section=section, page_slug=slug,
                active_navigation=slug if slug in area["slugs"] else section,
                section_title=dict(nav)[section], internal_page=section == "internal", internal_entry=section == "internal",
                lab_script=lesson.get("script"), previous_lesson=previous, next_lesson=following, **area_context(area), **shared)
            (stage / f"pages/{slug}.html").write_text(page, encoding="utf-8")
            search.append(dict(title=title, area=area["key"], location=area["title"], text=PlainText.convert(body), sections=section_index(body), url=f"pages/{slug}.html"))
        lab_scripts = sorted({f"labs/{item['script']}" for item in dft_lessons.values() if item.get("script")})
        for name in ("style.css", "app.js", "internal.js", "home.css", "home.js", "theme.css", "theme.js", "desktop.css", "reading.css", "reading.js", "dft.js", "dft.css", "lab.css", *lab_scripts):
            (stage / "assets" / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / "portal/assets" / name, stage / "assets" / name)
        (stage / "assets/search-data.js").write_text("window.DFT_SEARCH = " + json.dumps(search, ensure_ascii=False).replace("</", "<\\/") + ";\n", encoding="utf-8")
        hashes = {path.relative_to(stage).as_posix(): sha256(path) for path in sorted(stage.rglob("*")) if path.is_file()}
        write_json(stage / "build-manifest.json", dict(version=snapshot["version"], sources=source_hashes, files=hashes, pages=len(pages) + len(areas) + 1))
        destination = root / "site"
        if destination.is_symlink():
            raise ValueError("Symlink site destination")
        old = read_json(destination / "build-manifest.json")["files"] if (destination / "build-manifest.json").exists() else {}
        for relative in old:
            path = destination / relative
            if not path.resolve().is_relative_to(destination.resolve()):
                raise ValueError("Unsafe generated manifest path")
            if relative not in hashes:
                path.unlink(missing_ok=True)
        for path in stage.rglob("*"):
            if path.is_file():
                target = destination / path.relative_to(stage)
                if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):
                    raise ValueError(f"Symlink build output: {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    print(f"BUILT {len(pages) + len(areas) + 1} pages in {len(areas)} independent areas; public inputs only; no network")
    if include_internal:
        from scripts._lib.internal_docs import build_internal
        build_internal(root, template, shared, PlainText.convert, max_lines=max_lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-only", action="store_true", help="Build only public pages; do not access yellow/")
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, metavar="N",
                        help="Only render yellow/docs Markdown with at most N lines (default: 3000; inclusive)")
    args = parser.parse_args()
    if args.max_lines < 1:
        parser.error("--max-lines must be a positive integer")
    build(include_internal=not args.public_only, max_lines=args.max_lines)
