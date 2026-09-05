"""Exercise stateless binary updates without real downloads or user installation."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts._lib.common import ROOT, BINS, binary_metadata
from scripts.maintenance import maintain_binaries as updater


class BinaryTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".tmp/test-binaries"
        base.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for relative in BINS.values():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"original binary")

    def responses(self, arch="x64"):
        header = bytearray(64)
        header[:7] = b"\x7fELF\x02\x01\x01"
        header[18:20] = (62 if arch == "x64" else 183).to_bytes(2, "little")
        omp, claude = bytes(header) + b"omp", bytes(header) + b"claude"
        digest = lambda data: hashlib.sha256(data).hexdigest()
        omp_url, sums_url = "https://example.test/omp", "https://example.test/sums"
        claude_url = f"{updater.CLAUDE}/1.2.3/linux-{arch}/claude"
        release = dict(draft=False, prerelease=False, tag_name="v1.2.3", assets=[
            dict(name=f"omp-linux-{arch}", browser_download_url=omp_url,
                 size=len(omp), digest="sha256:" + digest(omp)),
            dict(name="SHA256SUMS.txt", browser_download_url=sums_url),
        ])
        manifest = dict(version="1.2.3", platforms={f"linux-{arch}": dict(checksum=digest(claude), size=len(claude))})
        return {
            updater.API: json.dumps(release).encode(),
            sums_url: f"{digest(omp)}  omp-linux-{arch}\n".encode(),
            updater.CLAUDE + "/stable": b"1.2.3\n",
            updater.CLAUDE + "/1.2.3/manifest.json": json.dumps(manifest).encode(),
            omp_url: omp, claude_url: claude,
        }, claude_url

    def run_update(self, responses, arch="x64"):
        def fetch(url):
            result = responses[url]
            if isinstance(result, Exception):
                raise result
            return io.BytesIO(result)
        with patch.object(updater, "fetch", side_effect=fetch), contextlib.redirect_stdout(io.StringIO()):
            updater.update(arch, self.root)

    def assert_originals(self):
        for relative in BINS.values():
            self.assertEqual((self.root / relative).read_bytes(), b"original binary")
        self.assertEqual(list((self.root / ".tmp").iterdir()), [])

    def test_update_and_repeat_leave_only_two_binaries(self):
        for arch in ("x64", "arm64"):
            with self.subTest(arch=arch):
                responses, _ = self.responses(arch)
                self.run_update(responses, arch)
                self.run_update(responses, arch)
                self.assertEqual({p.relative_to(self.root).as_posix()
                                  for p in self.root.rglob("*") if p.is_file()}, set(BINS.values()))
                self.assertEqual(list((self.root / ".tmp").iterdir()), [])
                for product in BINS:
                    self.assertEqual(binary_metadata(self.root, product)["platform"], f"linux-{arch}")

    def test_bad_second_checksum_preserves_both_binaries_and_cleans_downloads(self):
        responses, url = self.responses()
        responses[url] += b"corrupt"
        with self.assertRaisesRegex(ValueError, "checksum/size"):
            self.run_update(responses)
        self.assert_originals()

    def test_second_download_error_preserves_both_binaries(self):
        responses, url = self.responses()
        responses[url] = OSError("connection interrupted")
        with self.assertRaisesRegex(OSError, "interrupted"):
            self.run_update(responses)
        self.assert_originals()

    def test_publisher_verified_wrong_architecture_is_rejected(self):
        responses, url = self.responses()
        data = bytearray(responses[url])
        data[18:20] = (183).to_bytes(2, "little")
        responses[url] = bytes(data)
        manifest_url = updater.CLAUDE + "/1.2.3/manifest.json"
        manifest = json.loads(responses[manifest_url])
        manifest["platforms"]["linux-x64"]["checksum"] = hashlib.sha256(data).hexdigest()
        responses[manifest_url] = json.dumps(manifest).encode()
        with self.assertRaisesRegex(ValueError, "expected Linux x64"):
            self.run_update(responses)
        self.assert_originals()

    def test_conflicting_publisher_checksums_fail_before_downloads(self):
        responses, _ = self.responses()
        release = json.loads(responses[updater.API])
        release["assets"][0]["digest"] = "sha256:" + "0" * 64
        responses[updater.API] = json.dumps(release).encode()
        with self.assertRaisesRegex(ValueError, "disagrees"):
            self.run_update(responses)
        self.assertFalse((self.root / ".tmp").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
