"""Synchronize team files to the current user's default OMP profile, offline."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse
from contextlib import closing
import os
from pathlib import Path
import platform
import signal
import sqlite3
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._lib.common import ROOT, BINS, binary_metadata, atomic_copy, sha256, regular


class LinuxProcesses:
    """Only inspect/signal same-UID OMP processes, with PID-reuse protection."""
    def __init__(self, proc=Path("/proc")):
        self.proc = proc

    def identity(self, entry):
        fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]  # starttime, field 22

    def scan(self):
        result = {}
        for entry in self.proc.iterdir():
            if not entry.name.isdigit() or int(entry.name) == os.getpid():
                continue
            try:
                if entry.stat().st_uid != os.getuid():
                    continue
                ident = self.identity(entry)
                if ident is None:
                    continue
                cmd = (entry / "cmdline").read_bytes().split(b"\0")
                executable = os.readlink(entry / "exe").removesuffix(" (deleted)")
                name = Path(executable).name
                argv0 = Path(os.fsdecode(cmd[0])).name
                compiled = name == "omp" or name.startswith("omp-linux-") or argv0 == "omp"
                script = name in {"bun", "node"} and any(
                    b"coding-agent/" in part and (part.endswith(b"/cli.ts") or part.endswith(b"/cli.js"))
                    for part in cmd[1:3]
                )
                if compiled or script:
                    result[int(entry.name)] = ident
            except (FileNotFoundError, ProcessLookupError):
                continue
            except PermissionError as exc:
                raise RuntimeError(f"Cannot inspect current-user process {entry.name}; no replacement") from exc
        return result

    def stop(self, processes, timeout):
        for pid, identity in processes.items():
            try:
                entry = self.proc / str(pid)
                if entry.stat().st_uid != os.getuid() or self.identity(entry) != identity:
                    continue
                os.kill(pid, signal.SIGTERM)
            except (FileNotFoundError, ProcessLookupError):
                continue
        end = time.monotonic() + timeout
        while self.scan():
            if time.monotonic() >= end:
                raise RuntimeError("OMP has not exited (or restarted); nothing will be overwritten")
            time.sleep(0.1)


def check_target(path: Path, home: Path):
    if not path.is_relative_to(home):
        raise ValueError(f"Target outside home: {path}")
    for current in (path, *path.parents):
        if current.is_symlink():
            raise ValueError(f"Refusing symlink target component: {current}")
        if current == home:
            break
    if path.exists() and not path.is_file():
        raise ValueError(f"Target is not a file: {path}")
    parent = path.parent
    while not parent.exists():
        parent = parent.parent
    if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
        raise PermissionError(f"Target directory is not writable: {parent}")
    if path.exists() and not os.access(path, os.W_OK):
        raise PermissionError(f"Target is not writable: {path}")


def check_sidecars(path: Path):
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(path) + suffix)
        if sidecar.is_symlink() or (sidecar.exists() and sidecar.stat().st_size):
            raise ValueError(f"SQLite sidecar is active/nonempty: {sidecar}; checkpoint and close its writer first")


def check_database(path: Path):
    regular(path)
    check_sidecars(path)
    with path.open("rb") as stream:
        if stream.read(16) != b"SQLite format 3\x00":
            raise ValueError(f"Not an initialized SQLite database: {path}")
    # Immutable read prevents SQLite from creating sidecars in the source yellow directory.
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        result = db.execute("PRAGMA integrity_check").fetchall()
        if result != [("ok",)]:
            raise ValueError(f"SQLite integrity check failed: {path}")


def team_files(root: Path):
    base = root / "omp"
    if base.is_symlink():
        raise ValueError(f"Symlink source directory: {base}")
    required = [base / "AGENTS.md", base / "commands/code-and-verify.md",
                *(base / f"agents/{name}-worker.md" for name in ("document", "coding", "verification")),
                *(base / f"skills/{name}/SKILL.md" for name in ("generate-unit-tests", "generate-dft-circuit"))]
    for path in required:
        regular(path)
    files = [base / "AGENTS.md"]
    for name in ("commands", "agents", "skills"):
        folder = base / name
        if folder.is_symlink():
            raise ValueError(f"Symlink source: {folder}")
        for path in sorted(folder.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Symlink source: {path}")
            if path.is_file():
                files.append(path)
    return files


def synchronize(root: Path, home: Path, processes, dry_run=False, timeout=10.0, machine=None):
    home = home.absolute()
    agent = home / ".omp/agent"
    operations = [(p, agent / p.relative_to(root / "omp"), 0o644) for p in team_files(root)]
    for product, relative in BINS.items():
        meta = binary_metadata(root, product)
        arch = {"x86_64": "x64", "AMD64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(machine or platform.machine())
        if meta["platform"] != f"linux-{arch}":
            raise ValueError(f"Binary architecture mismatch: {product} {meta['platform']} / {arch}")
        source = root / relative
        operations.append((source, home / ".local/bin" / source.name, 0o755))
    source_db, target_db = root / "yellow/docs.db", agent / "docs.db"
    db_digest = None
    if source_db.exists() or source_db.is_symlink():
        check_database(source_db)
        db_digest = sha256(source_db)
        operations.append((source_db, target_db, 0o600))
    else:
        print("SKIP yellow/docs.db missing; personal database is preserved")
    for source, target, _ in operations:
        regular(source)
        with source.open("rb") as stream:
            stream.read(1)
        check_target(target, home)
    # Preflight all sources and destinations BEFORE terminating any process.
    running = processes.scan()
    print(f"{'WOULD STOP' if dry_run else 'STOP'} current-user OMP PIDs: {list(running)}")
    if dry_run:
        for _, target, _ in operations:
            print(f"WOULD SYNC {target}")
        return
    processes.stop(running, timeout)
    if processes.scan():
        raise RuntimeError("Cannot confirm OMP exit; no replacement")
    if db_digest is not None:
        check_sidecars(source_db)
        check_sidecars(target_db)
        if sha256(source_db) != db_digest:
            raise ValueError("Source database changed after preflight")
    stage_dir = root / ".tmp/sync"
    stage_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=stage_dir) as stage:
        stage = Path(stage)
        context = stage / "AGENTS.md"
        context.write_text((root / "omp/AGENTS.md").read_text(encoding="utf-8") +
            "\n\n## 本机团队资料位置（同步生成）\n\n" +
            f"原始资料目录：{(root / 'yellow/docs').resolve()}\n\n" +
            "该目录可能尚未接入资料。需要精确原文时在此 read/grep，不假设它位于目标代码仓。\n",
            encoding="utf-8")
        for source, target, mode in operations:
            if target == agent / "AGENTS.md":
                source = context
            if target == target_db:
                # Freeze the validated bytes in .tmp; never copy an unverified later revision.
                import shutil
                frozen = stage / "docs.db"
                shutil.copyfile(source, frozen)
                check_sidecars(source)
                if sha256(frozen) != db_digest or sha256(source) != db_digest:
                    raise ValueError("Source database changed during staging")
                source = frozen
            check_target(target, home)
            if processes.scan():
                raise RuntimeError("OMP restarted during sync; stopping before next replacement")
            if target == target_db:
                check_sidecars(target)
            if target.exists() and sha256(source) == sha256(target):
                if mode == 0o755:
                    target.chmod(mode)
                print(f"SKIP unchanged {target}")
                continue
            atomic_copy(source, target, mode)
            print(f"UPDATE {target}")
    print("DONE; model configuration and unrelated user files preserved; shell startup files unchanged")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stop-timeout", type=float, default=10.0)
    args = parser.parse_args()
    if not sys.platform.startswith("linux"):
        parser.error("Sync target must be Linux (CentOS 7); isolated tests can run on other hosts")
    if args.stop_timeout <= 0:
        parser.error("--stop-timeout must be positive")
    synchronize(ROOT, Path.home(), LinuxProcesses(), args.dry_run, args.stop_timeout)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        raise SystemExit(f"FAIL {exc}; earlier UPDATE lines, if any, are already applied")
