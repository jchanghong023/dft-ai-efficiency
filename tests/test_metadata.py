"""Documentation inventory and public-boundary regression checks."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._lib.common import ROOT, read_json
from scripts.build_site import load_content, public_inputs
from scripts.maintenance.package import public_files


class MetadataTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".tmp/test-metadata"; base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_missing_explanation_fails(self):
        from scripts import build_site
        original = build_site.catalog
        def missing(root, category):
            result = original(root, category)
            if category == "commands": result.pop("fullsend")
            return result
        with patch("scripts.build_site.catalog", side_effect=missing):
            with self.assertRaisesRegex(ValueError, "mismatch"): load_content(ROOT)

    def test_cli_usage_missing_entry_and_stale_revision_fail(self):
        import copy
        from scripts import build_site
        original=build_site.read_json
        for failure in ('missing','revision'):
            def changed(path):
                data=original(path)
                if path.name=='cli-usage.json':
                    data=copy.deepcopy(data)
                    if failure=='missing':data['entries'].pop('docs')
                    else:data['revision']='0'*40
                return data
            with self.subTest(failure=failure), patch('scripts.build_site.read_json',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'CLI usage explanation'):
                    load_content(ROOT)

    def test_cli_usage_contains_real_parameters_and_examples(self):
        from scripts.build_site import command_page
        snapshot, data=load_content(ROOT)
        self.assertEqual(len(data['cli']),43)
        for item in data['cli']:
            title, source=command_page(item,'cli',snapshot)
            self.assertIn(item['parameters'],source)
            self.assertNotEqual(item['example'],f"omp {item['name']} --help")
            self.assertIn(item['usage_source'],source)
        docs=next(item for item in data['cli'] if item['name']=='docs')
        self.assertIn('--name',docs['parameters'])
        self.assertIn('--force',docs['parameters'])

    def test_public_walk_does_not_open_or_enumerate_yellow(self):
        opened, enumerated = [], []
        original_open, original_iterdir = Path.open, Path.iterdir
        def guarded_open(path, *args, **kwargs):
            if "yellow" in path.parts: raise AssertionError(f"Opened yellow: {path}")
            opened.append(str(path)); return original_open(path, *args, **kwargs)
        def guarded_iterdir(path):
            if "yellow" in path.parts: raise AssertionError(f"Enumerated yellow: {path}")
            enumerated.append(str(path)); return original_iterdir(path)
        with patch.object(Path, "open", guarded_open), patch.object(Path, "iterdir", guarded_iterdir):
            load_content(ROOT); public_inputs(ROOT)
            members = list(public_files(ROOT))
        self.assertTrue(opened)
        self.assertTrue(members)
        self.assertIn("scripts/serve_site.py", {relative for relative, _ in members})
        self.assertIn("tests/test_serve_site.py", {relative for relative, _ in members})
        self.assertFalse(any("yellow/" in relative or ".tmp/" in relative for relative, _ in members))


if __name__ == "__main__": unittest.main(verbosity=2)
