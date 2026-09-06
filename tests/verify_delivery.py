"""Verify an extracted internal delivery in place; private details stay in .tmp/."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit, quote
from urllib.request import build_opener, ProxyHandler
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._lib.common import ROOT, read_json, sha256, write_json
from scripts.serve_site import resolve_file
from tests.verify import Page


def verify_delivery(root, http_base=None):
    root = root.resolve()
    errors, checked = [], set()
    def check(condition, message):
        if not condition: errors.append(message)
    def safe_file(base, relative):
        path = base / relative
        if not path.resolve().is_relative_to(base.resolve()) or any(p.is_symlink() for p in (path, *path.parents) if p != root and root in p.parents):
            raise ValueError('Unsafe delivery path')
        return path
    public = read_json(root / 'site/build-manifest.json')
    internal = read_json(root / 'yellow/.site/manifest.json')
    for folder, hashes in [('site', public['files']), ('yellow/.site', internal['hashes']), ('yellow/docs', internal['sources']), ('yellow/docs', internal['resources'])]:
        for name, digest in hashes.items():
            path = safe_file(root / folder, name)
            check(path.is_file() and sha256(path) == digest, f'缺失或改变：{folder}/{name}')
            checked.add(path)
    for folder, names, manifest in [('site', set(public['files']), 'build-manifest.json'), ('yellow/.site', set(internal['files']), 'manifest.json')]:
        actual = {p.relative_to(root / folder).as_posix() for p in (root / folder).rglob('*') if p.is_file()}
        check(actual == names | {manifest}, f'生成目录清单不一致：{folder}')
    import hashlib
    build_id = hashlib.sha256(json.dumps(public['sources'], sort_keys=True).encode()).hexdigest()[:12]
    check(internal['public_build'] == build_id, '公共与内部页面不属于同一次公共构建')
    check(internal['discovered'] == internal['documents'] + len(internal['skipped']) + len(internal['failed']), '文档计数不一致')
    recorded_sources = set(internal['sources']) | {item['path'] for item in internal['skipped'] + internal['failed']}
    actual_sources = {p.relative_to(root / 'yellow/docs').as_posix() for p in (root / 'yellow/docs').rglob('*') if p.is_file() and p.suffix.lower() == '.md'}
    check(actual_sources == recorded_sources, '原始文档清单发生变化；请重新构建')
    check(not internal['failed'], '存在读取失败的文档；查看内部构建报告')
    check(not internal['issues'], '存在被移除的引用或 HTML；查看内部构建报告')
    pages = {}
    for folder in ('site', 'yellow/.site'):
        for path in (root / folder).rglob('*.html'):
            parser = Page()
            try: parser.feed(path.read_text(encoding='utf-8'))
            except ValueError as exc: errors.append(f'{path.relative_to(root)}: {exc}')
            check(parser.title and 'main' in parser.ids, f'页面结构不完整：{path.relative_to(root)}')
            pages[path.resolve()] = parser
    for path, page in pages.items():
        for link in page.links + page.resources:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                check(link not in page.resources and parsed.scheme in {'https', 'http', 'mailto'}, f'外部或不安全资源：{path.relative_to(root)}: {link}')
                continue
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            check(not parsed.path.startswith('/') and target.is_relative_to(root) and target.is_file(), f'本地链接缺失或越界：{path.relative_to(root)}: {link}')
            if not target.is_relative_to(root): continue
            url = '/' + quote(target.relative_to(root).as_posix(), safe='/')
            check(resolve_file(root, url) == target, f'HTTP 不可访问：{url}')
            if parsed.fragment and target in pages:
                check(unquote(parsed.fragment) in pages[target].ids, f'章节锚点不存在：{path.relative_to(root)}: {link}')
            checked.add(target)
    raw = (root / 'yellow/.site/search-data.js').read_text(encoding='utf-8')
    entries = json.loads(raw.removeprefix('window.DFT_SEARCH = ').removesuffix(';\n'))
    articles = {p for p in pages if p.parent == root / 'yellow/.site' and p.name.startswith('doc-')}
    check(len(articles) == internal['documents'] == len(entries), '生成文档与搜索条目数量不一致')
    check({(root / 'site' / item['url']).resolve() for item in entries} == articles, '内部搜索没有覆盖全部生成文档')
    for item in entries:
        target = (root / 'site' / item['url']).resolve()
        check(item['area'] == 'internal' and target in articles, '内部搜索路径或分区不正确')
        for section in item.get('sections', []):
            check(target in pages and section['id'] in pages[target].ids, '内部搜索章节失效')
    checked.add(root / 'yellow/.site/entry.js')
    http_count = 0
    if http_base:
        opener = build_opener(ProxyHandler({}))
        for path in sorted(checked):
            if not path.is_file(): continue
            url = http_base.rstrip('/') + '/' + quote(path.relative_to(root).as_posix(), safe='/')
            try:
                with opener.open(url, timeout=10) as response:
                    check(response.read() == path.read_bytes(), f'HTTP 内容不一致：{path.relative_to(root)}')
                http_count += 1
            except OSError:
                errors.append(f'HTTP 请求失败：{path.relative_to(root)}')
    return dict(passed=not errors, generated_at=datetime.now(timezone.utc).isoformat(), public_build=build_id,
                internal_generated_at=internal['generated_at'], documents=internal['documents'], discovered=internal['discovered'],
                skipped=internal['skipped'], failed=internal['failed'], issues=internal['issues'], errors=errors,
                checked_files=len(checked), http_checked=http_count,
                browser_acceptance='未执行；须在目标浏览器检查 file://、搜索、交互和外部请求')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='最终内部包换目录解压后的根目录')
    parser.add_argument('--http-base', help='该解压目录已启动的 HTTP 地址，如 http://127.0.0.1:9333')
    args = parser.parse_args()
    output = ROOT / '.tmp/delivery-verification.json'
    try: result = verify_delivery(args.root, args.http_base)
    except (OSError, ValueError, KeyError) as exc:
        result = dict(passed=False, errors=[str(exc)])
    write_json(output, result)
    print(f"{'PASS' if result['passed'] else 'FAIL'} internal delivery; private details: .tmp/delivery-verification.json")
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
