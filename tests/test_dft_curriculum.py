"""Public curriculum integration and inert HTML checks, without a browser."""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_site import load_curriculum


class LabPage(HTMLParser):
    VOID = {"input", "br", "hr", "img", "meta", "link", "source", "wbr", "area", "base", "embed", "param", "col", "track"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.controls = []
        self.labs = 0
        self.fallbacks = 0
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        is_lab = "dft-lab" in attrs.get("class", "").split()
        in_lab = is_lab or any(entry[1] for entry in self.stack)
        if is_lab: self.labs += 1
        if in_lab and tag in {"button", "select", "input", "textarea"}:
            self.controls.append(attrs)
        if in_lab and tag == "noscript": self.fallbacks += 1
        if tag == "script": self.scripts.append(attrs.get("src"))
        if tag not in self.VOID: self.stack.append((tag, in_lab))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


class CurriculumTests(unittest.TestCase):
    def test_each_new_lesson_has_inert_controls_and_its_own_local_script(self):
        groups, lessons = load_curriculum(ROOT)
        self.assertEqual(len(groups), 6)
        self.assertEqual(len(lessons), 17)
        for lesson in lessons.values():
            if not lesson.get("lab"): continue
            with self.subTest(lesson=lesson["slug"]):
                page = (ROOT / f"site/pages/{lesson['slug']}.html").read_text(encoding="utf-8")
                parsed = LabPage(); parsed.feed(page)
                self.assertEqual(parsed.labs, 1)
                self.assertEqual(parsed.fallbacks, 1)
                self.assertGreater(len(parsed.controls), 1)
                self.assertTrue(all("disabled" in attrs for attrs in parsed.controls), "JS-only controls must be inert without JS")
                self.assertIn(f"../assets/labs/{lesson['script']}", parsed.scripts)
                self.assertEqual(len([src for src in parsed.scripts if src and "/labs/" in src]), 1)
                self.assertNotIn("<!-- lab:", page)

    def test_invalid_curriculum_asset_is_rejected(self):
        temporary = ROOT / ".tmp/test-dft-curriculum"; temporary.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary) as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "portal", root / "portal")
            path = root / "portal/metadata/dft-curriculum.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["groups"][0]["lessons"][1]["script"] = "../../untrusted.js"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid/duplicate DFT lab asset"):
                load_curriculum(root)

    def test_all_model_scripts_parse_in_node(self):
        node = shutil.which("node")
        if not node: self.skipTest("Node.js required for JavaScript syntax verification only")
        for path in sorted((ROOT / "portal/assets/labs").glob("*.js")):
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, f"{path.name}: {result.stderr}")


if __name__ == "__main__": unittest.main(verbosity=2)
