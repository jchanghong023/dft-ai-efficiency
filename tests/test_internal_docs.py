"""Isolated local Markdown rendering, navigation and public-output boundary checks."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import base64
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_site import build
from scripts._lib.common import ROOT, read_json


class InternalDocsTests(unittest.TestCase):
    def setUp(self):
        temporary = ROOT / ".tmp/test-internal-docs"; temporary.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "portal", self.root / "portal")
        # Builds read the public team sources; binary VERSION files are no longer inputs.
        shutil.copytree(ROOT / "omp", self.root / "omp")
        self.docs = self.root / "yellow/docs"; (self.docs / "nested").mkdir(parents=True)
        self.first = self.docs / "第一份 文档.md"
        self.first.write_text('# 测试说明\n\nPRIVATE_SENTINEL_5028\n\n[另一份](nested/第二份.MD#输入)\n\n![本地图片](image.png)\n\n![外部图片](https://example.invalid/image.png)\n\n<script>window.INTERNAL_SCRIPT_RAN=true</script>\n\n[危险链接](javascript:alert(1))\n\n```python\nprint("fixture")\n```\n', encoding="utf-8")
        (self.docs / "nested/第二份.MD").write_text('# 第二份\n\n## 输入\n\n另一份内容。\n', encoding="utf-8")
        (self.docs / "image.png").write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aS9sAAAAASUVORK5CYII='))
        self.run_build()

    def run_build(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()): build(self.root, **kwargs)

    def clean_delivery(self):
        self.first.write_text('# 测试说明\n\n[另一份](nested/第二份.MD#输入)\n\n![本地图片](image.png)\n', encoding='utf-8')
        self.run_build()

    def test_extracted_delivery_files_http_search_and_hashes(self):
        import zipfile
        import threading
        from scripts.serve_site import create_server, SiteHandler
        from tests.verify_delivery import verify_delivery
        self.clean_delivery()
        archive = self.root / 'fixture.zip'
        with zipfile.ZipFile(archive, 'w') as bundle:
            for folder in ('site', 'yellow/.site', 'yellow/docs'):
                for path in (self.root / folder).rglob('*'):
                    if path.is_file(): bundle.write(path, path.relative_to(self.root))
        relocated = self.root / 'different directory'
        with zipfile.ZipFile(archive) as bundle: bundle.extractall(relocated)
        with patch.object(SiteHandler, 'log_message'), create_server(relocated, port=0) as server:
            thread = threading.Thread(target=server.serve_forever); thread.start()
            try: result = verify_delivery(relocated, f'http://127.0.0.1:{server.server_port}')
            finally: server.shutdown(); thread.join()
        self.assertTrue(result['passed'], result['errors'])
        self.assertGreater(result['http_checked'], 180)
        (relocated / 'yellow/docs/image.png').unlink()
        self.assertFalse(verify_delivery(relocated)['passed'])

    def test_delivery_rejects_broken_fragment_and_changed_original(self):
        from tests.verify_delivery import verify_delivery
        self.clean_delivery()
        self.first.write_text('# 测试说明\n\n[章节](nested/第二份.MD#不存在)\n', encoding='utf-8')
        self.run_build()
        result = verify_delivery(self.root)
        self.assertTrue(any('章节锚点不存在' in error for error in result['errors']))
        self.clean_delivery()
        self.first.write_text('# Changed after build', encoding='utf-8')
        self.assertFalse(verify_delivery(self.root)['passed'])
        self.clean_delivery()
        (self.docs / 'added-after-build.md').write_text('# New document', encoding='utf-8')
        self.assertFalse(verify_delivery(self.root)['passed'])

    def test_hidden_resources_and_invalid_encoding_are_reported_privately(self):
        from tests.verify_delivery import verify_delivery
        self.clean_delivery()
        (self.docs / '.assets').mkdir()
        (self.docs / '.assets/figure.png').write_bytes(b'fixture')
        (self.docs / 'invalid.md').write_bytes(b'\xff\xfe\x00')
        self.first.write_text('# 测试说明\n\n![隐藏附件](.assets/figure.png)\n', encoding='utf-8')
        self.run_build()
        manifest = read_json(self.root / 'yellow/.site/manifest.json')
        self.assertEqual(len(manifest['failed']), 1)
        self.assertEqual(len(manifest['issues']), 1)
        article = (self.root / 'yellow/.site' / next(name for name in manifest['files'] if name.startswith('doc-') and '测试说明' in (self.root / 'yellow/.site' / name).read_text(encoding='utf-8'))).read_text(encoding='utf-8')
        self.assertNotIn('src="../docs/.assets', article)
        self.assertIn('.assets/figure.png', (self.root / 'yellow/.site/build-report.html').read_text(encoding='utf-8'))
        self.assertNotIn('.assets/figure.png', (self.root / 'site/assets/search-data.js').read_text(encoding='utf-8'))
        self.assertFalse(verify_delivery(self.root)['passed'])

    def test_private_output_does_not_enter_public_manifest_or_search(self):
        manifest = read_json(self.root / "site/build-manifest.json")
        for path in (self.root / "site").rglob("*"):
            if path.is_file():
                self.assertNotIn(b"PRIVATE_SENTINEL_5028", path.read_bytes())
                self.assertNotIn("第一份 文档".encode(), path.read_bytes())
        self.assertFalse(any("yellow" in name for name in [*manifest["files"], *manifest["sources"]]))
        private = read_json(self.root / "yellow/.site/manifest.json")
        self.assertEqual(private["documents"], 2)
        self.assertIn("PRIVATE_SENTINEL_5028", (self.root / "yellow/.site/search-data.js").read_text(encoding="utf-8"))

    def test_links_images_and_inert_html(self):
        from tests.verify import Page
        folder = self.root / "yellow/.site"
        articles = list(folder.glob("doc-*.html"))
        page = next(path for path in articles if "PRIVATE_SENTINEL_5028" in path.read_text(encoding="utf-8"))
        content = page.read_text(encoding="utf-8")
        parsed = Page(); parsed.feed(content)
        self.assertIn("../docs/image.png", parsed.resources)
        self.assertFalse(any(value.startswith("https:") for value in parsed.resources))
        self.assertFalse(any(value.startswith("javascript:") for value in parsed.links))
        self.assertNotIn("window.INTERNAL_SCRIPT_RAN", content)
        target = next(link for link in parsed.links if link.endswith("#输入"))
        self.assertTrue((folder / target.split("#")[0]).is_file())
        self.assertIn('id="输入"', (folder / target.split("#")[0]).read_text(encoding="utf-8"))

    def test_large_escaped_paragraph_and_duplicate_heading_anchors(self):
        from scripts._lib.internal_docs import render_markdown
        from scripts.build_site import PlainText
        from tests.verify import Page
        raw = '# 标题\n\n## 输入\n\n' + ('signal\\_name ' * 12000) + 'END_OF_MANUAL\n\n## 输入\n\n最后一段。\n'
        body, toc = render_markdown(raw, PlainText.convert)
        self.assertEqual(PlainText.convert(body).count('signal_name'), 12000)
        self.assertIn('END_OF_MANUAL', body)
        self.assertIn('最后一段。', body)
        parsed = Page(); parsed.feed(body)
        navigation = Page(); navigation.feed(toc)
        self.assertTrue({'输入', '输入_1'}.issubset(parsed.ids))
        self.assertTrue(all(link.removeprefix('#') in parsed.ids for link in navigation.links))

    def test_default_inclusive_line_limit_and_newline_styles(self):
        from scripts._lib.internal_docs import render_markdown
        content = {
            'below.md': b'# Below\n\n' + b'line\n' * 2996 + b'INCLUDED_LAST_LINE',
            'equal.md': b'# Equal\r\n\r\n' + b'line\r\n' * 2997 + b'INCLUDED_EQUAL\r\n',
            'above.md': b'# Above\r\r' + b'line\r' * 2998 + b'EXCLUDED_ABOVE',
        }
        for name, data in content.items(): (self.docs / name).write_bytes(data)
        with self.first.open('a', encoding='utf-8') as stream:
            stream.write('\n[超限原文](above.md)\n')
        def guarded_render(raw, converter):
            self.assertNotIn('EXCLUDED_ABOVE', raw)
            return render_markdown(raw, converter)
        with patch('scripts._lib.internal_docs.render_markdown', side_effect=guarded_render): self.run_build()
        folder = self.root / 'yellow/.site'
        manifest = read_json(folder / 'manifest.json')
        self.assertEqual(manifest['max_lines'], 3000)
        self.assertEqual(manifest['documents'], 4)
        self.assertEqual({item['path']: item['lines'] for item in manifest['skipped']}, {'above.md': 3001})
        search = (folder / 'search-data.js').read_text(encoding='utf-8')
        self.assertIn('INCLUDED_LAST_LINE', search)
        self.assertIn('INCLUDED_EQUAL', search)
        self.assertNotIn('EXCLUDED_ABOVE', search)
        for path in folder.glob('*.html'):
            html = path.read_text(encoding='utf-8')
            self.assertNotIn('EXCLUDED_ABOVE', html)
        article = next(p for p in folder.glob('doc-*.html') if 'PRIVATE_SENTINEL_5028' in p.read_text(encoding='utf-8'))
        self.assertIn('href="../docs/above.md"', article.read_text(encoding='utf-8'))
        for name, data in content.items(): self.assertEqual((self.docs / name).read_bytes(), data)

    def test_custom_limit_removes_previously_generated_page(self):
        source = self.docs / 'custom.md'
        source.write_text('# CUSTOM_LIMIT_DOCUMENT\n' + 'line\n' * 11, encoding='utf-8')
        self.run_build(max_lines=13)
        folder = self.root / 'yellow/.site'
        previous = next(p for p in folder.glob('doc-*.html') if '<h1 id="custom_limit_document">' in p.read_text(encoding='utf-8'))
        self.run_build(max_lines=11)
        self.assertFalse(previous.exists())
        self.assertTrue(source.is_file())
        self.assertNotIn('CUSTOM_LIMIT_DOCUMENT', (folder / 'search-data.js').read_text(encoding='utf-8'))
        self.assertNotIn('custom.md', (folder / 'index.html').read_text(encoding='utf-8'))
        self.assertEqual(read_json(folder / 'manifest.json')['max_lines'], 11)
        self.run_build(max_lines=1)
        self.assertEqual(list(folder.glob('doc-*.html')), [])
        self.assertIn('当前没有满足行数条件的文档', (folder / 'index.html').read_text(encoding='utf-8'))

    def test_invalid_cli_limits_fail_before_build(self):
        for value in ('0', '-1', 'invalid'):
            with self.subTest(value=value):
                result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/build_site.py'), '--max-lines', value],
                                        cwd=self.root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn('--max-lines', result.stderr)

    def test_public_only_does_not_access_yellow_and_rebuild_removes_stale_pages(self):
        original_open, original_rglob = Path.open, Path.rglob
        def guarded_open(path, *args, **kwargs):
            if "yellow" in path.parts: raise AssertionError("Public build accessed internal data")
            return original_open(path, *args, **kwargs)
        def guarded_rglob(path, *args, **kwargs):
            if "yellow" in path.parts: raise AssertionError("Public build enumerated internal data")
            return original_rglob(path, *args, **kwargs)
        with patch.object(Path, "open", guarded_open), patch.object(Path, "rglob", guarded_rglob):
            self.run_build(include_internal=False)
        self.first.unlink(); self.run_build()
        self.assertEqual(len(list((self.root / "yellow/.site").glob("doc-*.html"))), 1)
        self.assertNotIn("PRIVATE_SENTINEL_5028", (self.root / "yellow/.site/search-data.js").read_text(encoding="utf-8"))

    def test_desktop_file_navigation_search_and_no_javascript(self):
        from playwright.sync_api import sync_playwright, expect
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".tmp/browsers"))
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page(); external = []
            page.on("request", lambda request: external.append(request.url) if request.url.startswith(("http:", "https:")) else None)
            page.goto((self.root / "site/index.html").as_uri())
            self.assertEqual(page.locator(".topnav a").all_text_contents(), ["首页", "开始使用", "团队能力", "维护手册", "内部文档", "DFT知识"])
            page.locator(".topnav").get_by_role("link", name="内部文档", exact=True).click()
            page.wait_for_url("**/yellow/.site/index.html")
            self.assertEqual(page.locator(".document-list a").count(), 2)
            page.locator("#document-filter").fill("第一份")
            self.assertEqual(page.locator(".document-list a:visible").count(), 1)
            page.locator(".document-list a:visible").click()
            expect(page.locator("main")).to_contain_text("PRIVATE_SENTINEL_5028")
            self.assertIsNone(page.evaluate("window.INTERNAL_SCRIPT_RAN"))
            page.locator("main").get_by_role("link", name="另一份", exact=True).click()
            expect(page.locator("main h1")).to_have_text("第二份")
            page.locator('.search-trigger').click()
            page.locator("#search-input").fill("PRIVATE_SENTINEL_5028")
            page.locator("#search-results a").click()
            expect(page.locator("main")).to_contain_text("PRIVATE_SENTINEL_5028")
            self.assertFalse(page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"))
            selected = page.url
            context.close()
            context = browser.new_context(java_script_enabled=False)
            page = context.new_page(); page.goto(selected)
            expect(page.locator("main")).to_contain_text("PRIVATE_SENTINEL_5028")
            self.assertEqual(page.locator(".document-list a").count(), 2)
            context.close(); browser.close()
            self.assertEqual(external, [])


if __name__ == "__main__": unittest.main(verbosity=2)
