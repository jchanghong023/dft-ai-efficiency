"""Isolated staged-content and real Git-hook checks; never commits to the user's repo."""
from __future__ import annotations
import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.check_docs import check, ROOT
from scripts.maintenance.install_hooks import install


class DocChecksTests(unittest.TestCase):
    def setUp(self):
        folder = ROOT / '.tmp/test-doc-checks'; folder.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='repo with spaces ', dir=folder)
        self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        self.git('init', '--quiet')
        (self.root / 'portal/content').mkdir(parents=True)
        (self.root / 'tests').mkdir()
        shutil.copyfile(ROOT / 'tests/check_docs.py', self.root / 'tests/check_docs.py')
        self.doc = self.root / 'portal/content/team.md'

    def git(self, *args, checked=True):
        return subprocess.run(['git', '-C', str(self.root), *args], capture_output=True, text=True, check=checked)

    def test_inclusive_limit_and_newline_count(self):
        self.doc.write_bytes(b'line\r\n' * 2999 + b'last line')
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(check(self.root), 1)
        self.doc.write_bytes(self.doc.read_bytes() + b'\r\nextra')
        with self.assertRaisesRegex(ValueError, '3001 lines > 3000'): check(self.root)

    def test_staged_content_not_unstaged_edits_and_yellow_excluded(self):
        self.doc.write_text('line\n' * 6); self.git('add', 'portal/content/team.md')
        self.doc.write_text('short\n')
        with self.assertRaisesRegex(ValueError, '6 lines > 5'): check(self.root, staged=True, max_lines=5)
        self.git('add', 'portal/content/team.md'); self.doc.write_text('line\n' * 6)
        (self.root / 'yellow').mkdir(); (self.root / 'yellow/internal.md').write_bytes(b'\xff' * 100)
        self.git('add', 'yellow/internal.md')
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(check(self.root, staged=True, max_lines=5), 1)

    def test_real_pre_commit_hook_and_existing_hook_preservation(self):
        self.git('config', 'dft.docsMaxLines', '5')
        with contextlib.redirect_stdout(io.StringIO()): hook = install(self.root)
        self.doc.write_text('line\n' * 6); self.git('add', 'portal/content/team.md')
        result = self.git('hook', 'run', 'pre-commit', checked=False)
        self.assertNotEqual(result.returncode, 0); self.assertIn('Split oversized documents', result.stderr)
        self.doc.write_text('line\n' * 5); self.git('add', 'portal/content/team.md')
        result = self.git('hook', 'run', 'pre-commit', checked=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        hook.write_text('# unrelated existing hook\n')
        with self.assertRaisesRegex(ValueError, 'unrelated hook'): install(self.root)
        self.assertEqual(hook.read_text(), '# unrelated existing hook\n')


if __name__ == '__main__': unittest.main(verbosity=2)
