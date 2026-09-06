"""Isolated synchronization tests; never use a real personal OMP directory."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import contextlib
import io
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._lib.common import ROOT, BINS
from scripts.sync import synchronize, LinuxProcesses


class Processes:
    def __init__(self, stuck=False): self.stopped = False; self.stuck = stuck; self.calls = 0
    def scan(self):
        self.calls += 1
        return {} if self.stopped else {12345: "fixture"}
    def stop(self, running, timeout):
        if self.stuck: raise RuntimeError("process did not exit")
        self.stopped = True


class SyncTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".tmp/test-sync"; base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="case with spaces ", dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo with spaces"
        self.home = Path(self.temp.name) / "isolated home"
        self.root.mkdir(); self.home.mkdir()
        shutil.copytree(ROOT / "omp", self.root / "omp")
        (self.root / "yellow").mkdir()
        for product, relative in BINS.items():
            path = self.root / relative
            path.parent.mkdir(parents=True)
            header = bytearray(64)
            header[:7] = b"\x7fELF\x02\x01\x01"
            header[18:20] = (62).to_bytes(2, "little")
            path.write_bytes(header + product.encode() + b"binary test fixture")
        self.processes = Processes()

    def run_sync(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            synchronize(self.root, self.home, self.processes, machine="x86_64", **kwargs)
        return output.getvalue()

    def make_db(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TABLE evidence(value TEXT)"); db.execute("INSERT INTO evidence VALUES(?)", (value,))
            db.commit()

    def test_first_repeat_and_preserve_user_files(self):
        agent = self.home / ".omp/agent"; agent.mkdir(parents=True)
        for name in ("models.yml", "config.yml", "personal.txt"):
            (agent / name).write_text("personal must survive")
        (agent / "AGENTS.md").write_text("old team rules")
        (agent / "skills/personal").mkdir(parents=True)
        (agent / "skills/personal/SKILL.md").write_text("my skill")
        self.assertIn("UPDATE", self.run_sync())
        self.assertTrue(self.processes.stopped)
        self.assertIn(str((self.root / "yellow/docs").resolve()), (agent / "AGENTS.md").read_text(encoding="utf-8"))
        for name in ("models.yml", "config.yml", "personal.txt"):
            self.assertEqual((agent / name).read_text(), "personal must survive")
        self.assertEqual((agent / "skills/personal/SKILL.md").read_text(), "my skill")
        self.assertNotIn("UPDATE", self.run_sync())
        self.assertTrue((self.home / ".local/bin/omp").is_file())
        if os.name != "nt": self.assertTrue(os.access(self.home / ".local/bin/omp", os.X_OK))

    def test_same_name_only_overwrite(self):
        self.run_sync()
        source = self.root / "omp/skills/generate-unit-tests/SKILL.md"
        source.write_text(source.read_text(encoding="utf-8") + "\nchange\n", encoding="utf-8")
        self.assertIn("UPDATE", self.run_sync())
        self.assertEqual(source.read_bytes(), (self.home / ".omp/agent/skills/generate-unit-tests/SKILL.md").read_bytes())

    def test_missing_database_keeps_existing_and_sidecars(self):
        target = self.home / ".omp/agent/docs.db"
        self.make_db(target, "personal")
        old = target.read_bytes()
        sidecar = Path(str(target) + "-wal"); sidecar.write_bytes(b"existing personal WAL")
        self.assertIn("personal database is preserved", self.run_sync())
        self.assertEqual(target.read_bytes(), old)
        self.assertEqual(sidecar.read_bytes(), b"existing personal WAL")

    def test_valid_database_replaces_consistently(self):
        source = self.root / "yellow/docs.db"; target = self.home / ".omp/agent/docs.db"
        self.make_db(source, "team"); self.make_db(target, "personal")
        self.run_sync()
        with contextlib.closing(sqlite3.connect(target)) as db:
            self.assertEqual(db.execute("SELECT value FROM evidence").fetchall(), [("team",)])

    def test_corrupt_database_preflight_does_not_stop(self):
        (self.root / "yellow/docs.db").write_bytes(b"not sqlite")
        with self.assertRaises(ValueError): self.run_sync()
        self.assertEqual(self.processes.calls, 0)
        self.assertFalse((self.home / ".omp").exists())

    def test_empty_database_cannot_replace_personal_data(self):
        (self.root / "yellow/docs.db").touch()
        target = self.home / ".omp/agent/docs.db"; self.make_db(target, "personal")
        before = target.read_bytes()
        with self.assertRaisesRegex(ValueError, "initialized SQLite"): self.run_sync()
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(self.processes.calls, 0)

    def test_source_wal_rejected_without_modification(self):
        source = self.root / "yellow/docs.db"; self.make_db(source, "team")
        sidecar = Path(str(source) + "-wal"); sidecar.write_bytes(b"uncheckpointed")
        with self.assertRaisesRegex(ValueError, "sidecar"): self.run_sync()
        self.assertEqual(self.processes.calls, 0)
        self.assertEqual(sidecar.read_bytes(), b"uncheckpointed")

    def test_target_wal_rejected_after_process_exit(self):
        source = self.root / "yellow/docs.db"; target = self.home / ".omp/agent/docs.db"
        self.make_db(source, "team"); self.make_db(target, "personal")
        before = target.read_bytes()
        Path(str(target) + "-wal").write_bytes(b"active")
        with self.assertRaisesRegex(ValueError, "sidecar"): self.run_sync()
        self.assertTrue(self.processes.stopped)
        self.assertEqual(target.read_bytes(), before)

    def test_stuck_process_no_overwrite(self):
        self.processes = Processes(stuck=True)
        target = self.home / ".omp/agent/docs.db"; self.make_db(target, "personal")
        self.make_db(self.root / "yellow/docs.db", "team")
        before = target.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "did not exit"): self.run_sync()
        self.assertEqual(target.read_bytes(), before)
        self.assertFalse((target.parent / "AGENTS.md").exists())

    def test_lfs_pointer_rejected_before_process_scan(self):
        (self.root / BINS["omp"]).write_text("version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 99\n")
        with self.assertRaisesRegex(ValueError, "LFS pointer"): self.run_sync()
        self.assertEqual(self.processes.calls, 0)

    def test_invalid_elf_rejected(self):
        (self.root / BINS["omp"]).write_bytes(b"\x7fELF")
        with self.assertRaisesRegex(ValueError, "ELF header"): self.run_sync()
        self.assertFalse(self.processes.stopped)

    def test_architecture_mismatch_rejected(self):
        path = self.root / BINS["omp"]
        data = bytearray(path.read_bytes())
        data[18:20] = (183).to_bytes(2, "little")
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "architecture mismatch"): self.run_sync()
        self.assertFalse(self.processes.stopped)

    def test_permissions_preflight_before_stop(self):
        with patch("scripts.sync.os.access", return_value=False):
            with self.assertRaises(PermissionError): self.run_sync()
        self.assertFalse(self.processes.stopped)

    def test_dry_run_writes_nothing_and_does_not_stop(self):
        self.assertIn("WOULD SYNC", self.run_sync(dry_run=True))
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertFalse(self.processes.stopped)
        self.assertFalse((self.root / ".tmp").exists())

    def test_readonly_staging_rejected_even_in_preview(self):
        access = os.access
        for dry_run in (True, False):
            with patch('scripts.sync.os.access', side_effect=lambda p, mode: False if p == self.root else access(p, mode)):
                with self.assertRaises(PermissionError): self.run_sync(dry_run=dry_run)
            self.assertFalse(self.processes.stopped)
            self.assertEqual(list(self.home.iterdir()), [])

    def test_staging_creation_failure_does_not_stop_process(self):
        with patch('scripts.sync.tempfile.TemporaryDirectory', side_effect=PermissionError('read-only staging')):
            with self.assertRaises(PermissionError): self.run_sync()
        self.assertFalse(self.processes.stopped)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_missing_team_file_preflight(self):
        (self.root / "omp/agents/coding-worker.md").unlink()
        with self.assertRaises(ValueError): self.run_sync()
        self.assertEqual(self.processes.calls, 0)

    def test_target_symlink_rejected(self):
        target = self.home / ".omp/agent"; target.mkdir(parents=True)
        victim = self.home / "personal"; victim.write_text("keep")
        try: (target / "AGENTS.md").symlink_to(victim)
        except OSError: self.skipTest("Symlinks not supported on this host")
        with self.assertRaisesRegex(ValueError, "symlink"): self.run_sync()
        self.assertEqual(victim.read_text(), "keep")

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc integration")
    def test_cli_dry_run_from_arbitrary_directory(self):
        scripts = self.root / "scripts"; scripts.mkdir()
        (scripts / "_lib").mkdir()
        for name in ("sync.py", "_lib/common.py"):
            shutil.copyfile(ROOT / "scripts" / name, scripts / name)
        env = dict(os.environ, HOME=str(self.home))
        result = subprocess.run([sys.executable, "-B", str(scripts / "sync.py"), "--dry-run"],
                                cwd=self.temp.name, env=env, text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.home / ".omp/agent"), result.stdout)
        self.assertFalse((self.home / ".omp").exists())

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux /proc integration")
    def test_real_same_uid_process_termination_isolated(self):
        executable = self.root / "omp-test-bin/omp"; executable.parent.mkdir()
        shutil.copyfile("/bin/sleep", executable); executable.chmod(0o755)
        proc = subprocess.Popen([str(executable), "20"])
        self.addCleanup(lambda: proc.kill() if proc.poll() is None else None)
        class OnlyFixture(LinuxProcesses):
            def scan(inner): return {pid: identity for pid, identity in super().scan().items() if pid == proc.pid}
        manager = OnlyFixture()
        self.assertIn(proc.pid, manager.scan())
        manager.stop(manager.scan(), 3)
        self.assertEqual(proc.wait(timeout=3), -15)


if __name__ == "__main__":
    unittest.main(verbosity=2)
