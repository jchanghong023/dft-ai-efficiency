"""Desktop browser file:// acceptance (requires Playwright and local Chromium)."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import os
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._lib.common import ROOT
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".tmp/browsers"))
from playwright.sync_api import sync_playwright, expect


def main():
    output = ROOT / ".tmp/browser-check"; output.mkdir(parents=True, exist_ok=True)
    failures, network, errors = [], [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1050})
        page = context.new_page()
        page.on("request", lambda req: network.append(req.url) if req.url.startswith(("http:", "https:")) else None)
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto((ROOT / "site/index.html").as_uri())
        page.screenshot(path=str(output / "desktop-home.png"), full_page=True)
        page.locator('main a[href="pages/quickstart.html"]').click()
        assert page.url.endswith("quickstart.html")
        page.screenshot(path=str(output / "desktop-article.png"), full_page=True)
        page.get_by_role("button", name="复制代码").first.click()
        expect(page.locator("#toast")).to_have_text("已复制代码")
        # Verify actual copied bytes with a local clipboard shim as well, independent of OS paste permissions.
        page.evaluate("window.__copied = null; Object.defineProperty(navigator, 'clipboard', {configurable:true,value:{writeText:async t=>{window.__copied=t;}}})")
        expected = page.locator("pre code").first.inner_text()
        page.get_by_role("button", name="复制代码").first.click()
        assert page.evaluate("window.__copied") == expected
        for area, query, destination in [("start", "fullsend", "command-fullsend.html"), ("team", "PAD", "skill-generate-dft-circuit.html"),
                                    ("team", "generate-unit-tests", "skill-generate-unit-tests.html"), ("start", "进程无法退出", "faq.html")]:
            page.goto((ROOT / f"site/{area}/index.html").as_uri())
            page.locator('.search-trigger').click()
            page.locator("#search-input").fill(query)
            assert page.locator(f'#search-results a[href*="{destination}"]').count(), query
        page.goto((ROOT / "site/start/index.html").as_uri())
        page.locator('.search-trigger').click()
        page.locator("#search-input").fill("fullsend")
        page.locator('#search-results a[href*="command-fullsend.html"]').click()
        assert "command-fullsend.html" in page.url
        # Every generated page must load successfully with no script errors or horizontal desktop overflow.
        article_paths = sorted(path for path in (ROOT / "site").rglob("*.html") if path != ROOT / "site/index.html")
        for path in article_paths:
            page.goto(path.as_uri())
            if path in {ROOT / "site/pages/internal.html", ROOT / "site/internal/index.html"} and (ROOT / "yellow/.site/entry.js").exists():
                page.wait_for_url("**/yellow/.site/index.html")
            if not page.locator("main h1").count(): failures.append(f"missing body: {path.name}")
            if page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"): failures.append(f"overflow: {path.name}")
        context.close()
        no_js = browser.new_context(java_script_enabled=False, viewport={"width": 1440, "height": 1050})
        plain = no_js.new_page()
        plain.goto((ROOT / "site/pages/commands.html").as_uri())
        assert plain.locator('main a[href="command-fullsend.html"]').count() == 1
        plain.locator('main a[href="command-fullsend.html"]').click()
        assert plain.locator("main h1").inner_text() == "/fullsend"
        assert plain.locator("main").inner_text().find("文件与状态影响") >= 0
        no_js.close(); browser.close()
    result = dict(desktop="1440x1050", pages=len(article_paths) + 1, external_requests=network, javascript_errors=errors, failures=failures,
                  checks=["file navigation", "Chinese full text search", "command and Skill search", "code copy bytes", "all article loads", "no-JS article navigation"])
    (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if network or errors or failures: raise AssertionError(result)
    print("PASS desktop file:// navigation, all pages, Chinese search, copy, no-JS; zero external requests")


if __name__ == "__main__": main()
