"""Desktop offline acceptance of independent areas and computed DFT demonstrations."""
from __future__ import annotations
import os
import json
from pathlib import Path
import sys
import unittest
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(ROOT / '.tmp/browsers'))
from playwright.sync_api import sync_playwright, expect


class DftPortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1050})
        self.page = self.context.new_page(); self.external = []; self.errors = []
        self.page.on('request', lambda request: self.external.append(request.url) if request.url.startswith(('http:', 'https:')) else None)
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.external, []); self.assertEqual(self.errors, [])

    def open(self, relative): self.page.goto((ROOT / 'site' / relative).as_uri())

    def test_five_distinct_area_pages_and_scoped_navigation(self):
        titles = ['开始使用', '团队能力', '维护手册', '内部文档', 'DFT知识']
        areas = ['start', 'team', 'maintenance', 'internal', 'dft']
        self.open('index.html')
        self.assertEqual(self.page.locator('.topnav a').all_text_contents(), ['首页', *titles])
        self.assertEqual(self.page.locator('.topnav a:not(:first-child)').evaluate_all('(links) => links.map(link => new URL(link.href).pathname.split("/").slice(-2).join("/"))'), [f'{area}/index.html' for area in areas])
        expected_links = {'start': ['quickstart', 'hotkeys', 'usage-guide', 'cli', 'tools', 'config', 'commands', 'agents', 'faq'],
                          'team': ['team', 'skills', 'team-agents', 'team-commands', 'skill-generate-unit-tests', 'skill-generate-dft-circuit'],
                          'maintenance': ['maintenance'],
                          'dft': [lesson['slug'] for group in json.loads((ROOT / 'portal/metadata/dft-curriculum.json').read_text(encoding='utf-8'))['groups'] for lesson in group['lessons']]}
        for area, title in zip(areas, titles):
            self.open(f'{area}/index.html')
            if area == 'internal' and (ROOT / 'yellow/.site/entry.js').exists(): self.page.wait_for_url('**/yellow/.site/index.html')
            expect(self.page.locator('body')).to_have_attribute('data-area', area)
            expect(self.page.locator('main h1')).to_have_text(title)
            expect(self.page.locator('.topnav a[aria-current="page"]')).to_have_text(title)
            if area in expected_links:
                paths = self.page.locator('.sidebar nav a').evaluate_all('(links) => links.map(link => link.href.split("/").pop())')
                self.assertEqual(paths, [slug + '.html' for slug in expected_links[area]])

    def test_scan_shift_capture_response_fault_pause_and_reset(self):
        self.open('pages/dft-scan.html'); demo = self.page.locator('#scan-demo')
        step = demo.get_by_role('button', name='单步', exact=True)
        for _ in range(4): step.click()
        expect(demo.locator('[data-field="registers"]')).to_have_text('1101')
        step.click(); expect(demo.locator('[data-field="se"]')).to_have_text('0')
        expect(demo.locator('[data-field="registers"]')).to_have_text('0010')
        for _ in range(4): step.click()
        expect(demo.locator('[data-field="output"]')).to_have_text('0100')
        expect(demo).to_have_attribute('data-result', 'same')
        demo.locator('[data-setting="fault"]').select_option('stuck')
        for _ in range(9): step.click()
        expect(demo.locator('[data-field="output"]')).to_have_text('0000')
        expect(demo).to_have_attribute('data-result', 'different')
        demo.get_by_role('button', name='重置').click()
        demo.get_by_role('button', name='播放', exact=True).click()
        self.page.wait_for_function('document.querySelector("#scan-demo").dataset.step !== "0"')
        demo.get_by_role('button', name='暂停', exact=True).click()
        paused = demo.get_attribute('data-step')
        self.page.wait_for_timeout(950)
        expect(demo).to_have_attribute('data-step', paused)
        self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'))
        output = ROOT / '.tmp/browser-check'; output.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(output / 'desktop-scan.png'), full_page=True)

    def test_edt_compression_detected_error_and_aliasing(self):
        self.open('pages/dft-edt.html'); demo = self.page.locator('#edt-demo')
        for scenario, expected, result in [('none', '11 · 10 · 11 · 00', 'same'), ('single', '01 · 10 · 11 · 00', 'different'), ('double', '11 · 10 · 11 · 00', 'alias')]:
            demo.locator('[data-setting="fault"]').select_option(scenario)
            for _ in range(4): demo.get_by_role('button', name='单步', exact=True).click()
            expect(demo.locator('[data-field="output"]')).to_have_text(expected)
            expect(demo).to_have_attribute('data-result', result)
        expect(demo.locator('[data-field="explanation"]')).to_contain_text('抵消')
        self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'))
        output = ROOT / '.tmp/browser-check'; output.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(output / 'desktop-edt.png'), full_page=True)

    def test_scan_inputs_history_and_component_explanation(self):
        self.open('pages/dft-scan.html'); demo=self.page.locator('#scan-demo')
        step=demo.locator('[data-action="step"]')
        for _ in range(6): step.click()
        demo.locator('[data-edge="5"]').click()
        expect(demo).to_have_attribute('data-step','6')
        expect(demo).to_have_attribute('data-view-step','5')
        expect(demo.locator('[data-field="registers"]')).to_have_text('0010')
        demo.locator('[data-inspect="q2"]').click()
        expect(demo.locator('[data-field="component-detail"]')).to_contain_text('D3=1')
        step.click()
        expect(demo).to_have_attribute('data-view-step','7')
        demo.locator('[data-setting="fault"]').select_option('stuck')
        for index in range(4): demo.locator(f'[data-stimulus="{index}"]').select_option('0')
        expect(demo.locator('[data-edge]')).to_have_count(1)
        expect(demo.locator('[data-field="expected"]')).to_have_text('1000')
        for _ in range(9): step.click()
        expect(demo.locator('[data-field="output"]')).to_have_text('1000')
        expect(demo.locator('[data-field="explanation"]')).to_contain_text('没有激活')

    def test_flow_recalculates_conditions_and_keeps_unresolved_evidence(self):
        self.open('pages/dft-flow.html'); demo=self.page.locator('#flow-lab')
        for _ in range(3):
            demo.locator('[data-action="inspect"]').click()
            demo.locator('[data-action="next"]').click()
        expect(demo).to_have_attribute('data-state','attention')
        expect(demo.locator('[data-evidence-records] li')).to_have_count(3)
        demo.locator('[data-parameter="link"]').select_option('normal')
        expect(demo.locator('[data-evidence-records] li')).to_have_count(0)
        expect(demo.locator('[data-trace-body] tr:last-child td:last-child')).to_have_text('1011')
        demo.locator('[data-setting="symptom"]').select_option('x-source')
        demo.locator('[data-parameter="source"]').select_option('0')
        demo.locator('[data-parameter="fault"]').select_option('yes')
        demo.locator('[data-parameter="mask"]').select_option('yes')
        expect(demo.locator('[data-trace-body] tr:last-child td:last-child')).to_have_text('masked')
        demo.locator('[data-parameter="mask"]').select_option('no')
        expect(demo.locator('[data-trace-body] tr:last-child td:last-child')).to_have_text('different')

    def test_no_javascript_still_shows_concepts_and_circuits(self):
        context = self.browser.new_context(java_script_enabled=False, viewport={'width': 1440, 'height': 1050})
        try:
            page = context.new_page()
            for demo in ('scan', 'edt'):
                page.goto((ROOT / f'site/pages/dft-{demo}.html').as_uri())
                self.assertEqual(page.locator('main svg').count(), 1)
                self.assertIn('静态图', page.locator('main').inner_text())
                self.assertEqual(page.locator('.demo-controls button:disabled').count(), 3)
                self.assertGreater(len(page.locator('main').inner_text()), 300)
        finally: context.close()

    def test_jtag_update_entry_and_history_preserve_live_state(self):
        self.open('pages/dft-jtag.html'); demo=self.page.locator('#jtag-lab')
        demo.locator('[data-access-setting="instruction"]').select_option('EXTEST')
        demo.locator('[data-access-action="load-instruction"]').click()
        expect(demo.locator('[data-tck]')).to_have_count(9)
        demo.locator('[data-tck="8"]').click()
        expect(demo).to_have_attribute('data-live-cycle','9')
        expect(demo).to_have_attribute('data-view-cycle','8')
        expect(demo.locator('[data-access-field="state"]')).to_have_text('Update-IR')
        expect(demo.locator('[data-access-field="instruction"]')).to_have_text('EXTEST')
        demo.locator('[data-tap-state="Pause-IR"]').click()
        expect(demo.locator('[data-access-field="node-detail"]')).to_contain_text('保存当前移位寄存器')
        demo.locator('[data-access-action="tms0"]').click()
        expect(demo).to_have_attribute('data-live-cycle','10')
        expect(demo).to_have_attribute('data-view-cycle','10')

    def test_occ_source_edges_gate_after_capture_and_history_pauses(self):
        self.open('pages/dft-clock-reset.html'); demo=self.page.locator('#clocks-occ-lab')
        demo.locator('[data-field="mode"]').select_option('capture')
        demo.locator('[data-field="se"]').uncheck()
        demo.locator('[data-field="functional"]').check()
        step=demo.locator('[data-action="step"]')
        step.click();step.click()
        expect(demo.locator('[data-readout="edges"]')).to_have_text('2 / 2')
        demo.locator('[data-action="play"]').click()
        demo.locator('[data-occ-edge="1"]').click()
        expect(demo.locator('[data-action="play"]')).to_have_text('播放')
        expect(demo).to_have_attribute('data-view-step','1')
        before=demo.get_attribute('data-step')
        self.page.wait_for_timeout(1000)
        expect(demo).to_have_attribute('data-step',before)
        demo.locator('[data-action="latest"]').click()
        while not step.is_disabled(): step.click()
        expect(demo.locator('[data-readout="edges"]')).to_have_text('2 / 2')
        expect(demo.locator('[data-visual="pulse"][data-active="true"]')).to_have_count(2)


if __name__ == '__main__': unittest.main(verbosity=2)
