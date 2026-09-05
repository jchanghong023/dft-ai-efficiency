"""Exercise HTTP serving with synthetic files, never real internal documents."""
from __future__ import annotations

from http.client import HTTPConnection
from pathlib import Path
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import serve_site


class ServeSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = serve_site.ROOT / ".tmp/test-serve-site"
        base.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=base)
        cls.root = Path(cls.temp.name).resolve()
        for name, body in {
            "site/index.html": "<h1>测试门户</h1>",
            "site/pages/test.html": "<p>Document</p>",
            "site/assets/test.js": "window.test=true;",
            "site/assets/test.css": "body{color:#222}",
            "yellow/.site/index.html": "Internal fixture",
            "yellow/.site/entry.js": "window.DFT_INTERNAL_READY=true;",
            "yellow/docs/示例.md": "Attachment fixture",
            "yellow/docs.db": "Must not be served",
            "site/.hidden": "Must not be served",
            "README.md": "Must not be served",
        }.items():
            file = cls.root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(body, encoding="utf-8")
        cls.server = serve_site.create_server(cls.root, port=0)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, path, method="GET"):
        connection = HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, {key.lower(): value for key, value in response.getheaders()}, response.read()
        finally:
            connection.close()

    def test_loopback_and_entry(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertEqual(serve_site.PORT, 9333)
        status, headers, body = self.request("/")
        self.assertEqual(status, 302)
        self.assertEqual(headers["location"], "/site/index.html")
        status, headers, body = self.request(headers["location"])
        self.assertEqual(status, 200)
        self.assertIn("测试门户", body.decode("utf-8"))
        self.assertIn("charset=utf-8", headers["content-type"])
        self.assertEqual(headers["cache-control"], "no-cache")

    def test_pages_assets_and_internal_routes(self):
        for path in ("/site/", "/site/pages/test.html?q=1", "/site/assets/test.js",
                     "/site/assets/test.css", "/yellow/.site/index.html",
                     "/yellow/.site/entry.js", "/yellow/docs/%E7%A4%BA%E4%BE%8B.md"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 200)
        self.assertIn("javascript", self.request("/site/assets/test.js")[1]["content-type"])
        status, headers, body = self.request("/site/pages/test.html", "HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertGreater(int(headers["content-length"]), 0)

    def test_no_repository_exposure_or_directory_listing(self):
        for path in ("/README.md", "/yellow/docs.db", "/.git/config", "/site/assets/",
                     "/site/missing.html", "/yellow/docs/", "/site/.hidden",
                     "/site/../README.md", "/site/%2e%2e/README.md",
                     "/site/%2e%2e%5cREADME.md", "/site/%00", "/site/index.html:secret"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_missing_build_and_port_conflict_messages(self):
        with tempfile.TemporaryDirectory(dir=self.root) as empty:
            with patch.object(serve_site, "ROOT", Path(empty)), patch.object(sys, "argv", ["serve_site.py"]):
                with patch("sys.stderr") as error:
                    self.assertEqual(serve_site.main(), 1)
                    self.assertIn("build_site.py", str(error.write.call_args_list))
        with patch.object(serve_site, "ROOT", self.root), patch.object(sys, "argv", ["serve_site.py"]):
            with patch.object(serve_site, "create_server", side_effect=OSError("Address in use")), patch("sys.stderr") as error:
                self.assertEqual(serve_site.main(), 1)
                self.assertIn("9333", str(error.write.call_args_list))

    def test_ctrl_c_closes_server(self):
        with patch.object(serve_site, "ROOT", self.root), patch.object(sys, "argv", ["serve_site.py"]):
            with patch.object(serve_site, "create_server") as factory, patch("sys.stdout"):
                server = factory.return_value
                server.serve_forever.side_effect = KeyboardInterrupt
                self.assertEqual(serve_site.main(), 0)
                server.__exit__.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
