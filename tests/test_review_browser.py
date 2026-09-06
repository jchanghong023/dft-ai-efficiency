"""Browser regression for public search and reduced desktop viewport widths."""
import os
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(ROOT / '.tmp/browsers'))


class ReviewBrowserTests(unittest.TestCase):
    def test_public_search_and_desktop_widths(self):
        output = ROOT / '.tmp/review-browser'; output.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            errors, external = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: external.append(request.url) if request.url.startswith(('https:', 'http:')) else None)
            page.goto((ROOT / 'site/index.html').as_uri())
            for area in ('start', 'internal', 'dft', 'team', 'maintenance'):
                self.assertTrue(page.locator(f'main a[href="{area}/index.html"]').first.is_visible())
            page.locator('.search-trigger').click()
            page.locator('#search-input').fill('lock-up')
            self.assertGreater(page.locator('#search-results a[href*="dft-scan-engineering.html"]').count(), 0)
            self.assertIn('全部公共内容', page.locator('#search-status').inner_text())
            page.locator('#search-close').click()
            page.screenshot(path=str(output / 'home.png'), full_page=True)
            # CSS viewport equivalents of 1440px at 100/125/150%, plus split screen.
            for width in (1440, 1152, 960, 720):
                page.set_viewport_size({'width': width, 'height': 1000})
                for relative in ('index.html', 'pages/quickstart.html', 'pages/dft-scan-engineering.html', 'pages/command-model.html'):
                    page.goto((ROOT / 'site' / relative).as_uri())
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), (width, relative))
                    if relative != 'index.html':
                        article = page.locator('main').bounding_box()
                        self.assertGreater(article['width'], 430, (width, relative))
                        if width <= 1200: self.assertFalse(page.locator('.docs-layout > .toc').is_visible())
                if width == 960: page.screenshot(path=str(output / 'article-960.png'), full_page=True)
            self.assertEqual(errors, [])
            self.assertEqual(external, [])
            browser.close()


if __name__ == '__main__': unittest.main(verbosity=2)
