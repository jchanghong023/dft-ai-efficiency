"""Create and verify a public offline ZIP using explicit public inputs only."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import hashlib
from pathlib import Path
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts._lib.common import ROOT, BINS, binary_metadata, sha256, read_json, write_json
from tests.verify import verify_content, verify_site

SOURCE_FILES = [
    "README.md", "AGENTS.md", ".gitignore", ".gitattributes", "requirements-build.txt", "requirements-dev.txt",
    "omp/AGENTS.md", "omp/commands/code-and-verify.md",
    "omp/agents/document-worker.md", "omp/agents/coding-worker.md", "omp/agents/verification-worker.md",
    "omp/skills/generate-unit-tests/SKILL.md", "omp/skills/generate-dft-circuit/SKILL.md",
    "omp/skills/generate-dft-circuit/references/tiny-base.md",
    "scripts/sync.py", "scripts/build_site.py", "scripts/serve_site.py", "scripts/_lib/common.py", "scripts/_lib/internal_docs.py", "scripts/_lib/search.py",
    *[f"scripts/maintenance/{name}.py" for name in ("maintain_binaries", "package", "install_hooks")],
    "licenses/omp/LICENSE", "licenses/omp/THIRD-PARTY-NOTICES.txt",
    *[f"tests/{name}.py" for name in ("__init__", "verify", "check_docs", "test_sync", "test_binaries", "test_portal", "test_metadata", "test_internal_docs", "test_doc_checks", "test_dft_portal",
        "test_dft_curriculum", "test_dft_scan", "test_dft_faults", "test_dft_clocks", "test_dft_access", "test_dft_bist", "test_dft_compression_power", "test_dft_flow", "test_presentation", "test_serve_site")],
    "VALIDATION.md",
    "本仓库项目自身相关文档/DFT_OMP_AI开发提效方案与实施计划_最终版.md",
]
YELLOW_IGNORE = b"*\n!.gitignore\n"


def public_files(root=ROOT):
    manifest = read_json(root / "site/build-manifest.json")
    files = set(SOURCE_FILES)
    files.update(manifest["sources"])
    files.update("site/" + name for name in manifest["files"])
    files.add("site/build-manifest.json")
    files.update(BINS.values())
    for relative in sorted(files):
        path = root / relative
        if Path(relative).is_absolute() or any(part in {"yellow", ".tmp", ".git", ".."} for part in Path(relative).parts):
            raise ValueError(f"Disallowed release member: {relative}")
        if any(part.is_symlink() for part in [path, *path.parents]) or not path.is_file():
            raise ValueError(f"Invalid public source: {relative}")
        yield relative, path


def build_package(root=ROOT):
    verify_content(root); verify_site(root)
    metadata = {product: binary_metadata(root, product) for product in BINS}
    if metadata["omp"]["platform"] != metadata["claude-code"]["platform"]:
        raise ValueError("Mixed binary architectures")
    folder = root / ".tmp/releases"
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f"dft-ai-efficiency-{metadata['omp']['platform']}.zip"
    pending = output.with_suffix(".zip.partial")
    paths = list(public_files(root))  # Full preflight, without looking into yellow.
    prefix = "dft-ai-efficiency/"
    with zipfile.ZipFile(pending, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative, path in paths:
            info = zipfile.ZipInfo(prefix + relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = ((0o100755 if relative in BINS.values() else 0o100644) << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            with path.open("rb") as source, archive.open(info, "w", force_zip64=True) as target:
                import shutil
                shutil.copyfileobj(source, target)
        archive.writestr(prefix + "yellow/.gitignore", YELLOW_IGNORE)
    with zipfile.ZipFile(pending) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP CRC verification failed")
        expected = {prefix + relative for relative, _ in paths} | {prefix + "yellow/.gitignore"}
        if set(archive.namelist()) != expected:
            raise ValueError("ZIP member mismatch")
        for product, relative in BINS.items():
            with archive.open(prefix + relative) as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != metadata[product]["sha256"]:
                raise ValueError(f"ZIP binary checksum mismatch: {product}")
    pending.replace(output)
    checksum = sha256(output)
    output.with_suffix(".zip.sha256").write_text(f"{checksum}  {output.name}\n", encoding="utf-8")
    write_json(output.with_suffix(".zip.manifest.json"), {"file": output.name, "sha256": checksum, "bytes": output.stat().st_size,
                "members": len(paths) + 1, "binaries": metadata,
                "excludes": ["yellow internal data", ".tmp", ".git", "personal configuration", "credentials"]})
    print(f"PACKAGED {output}\nSHA256 {checksum}\n{len(paths) + 1} members; ZIP CRC and embedded binary hashes verified")
    return output


if __name__ == "__main__":
    build_package()
