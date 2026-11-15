"""tools/redmine.py を、手元に立てた模擬サーバーで確かめる。

    python -m unittest tools/test_redmine.py

本物の Redmine には接続しない。API の形 (パス、ヘッダ、本文) が合っているかを見る。
"""
import contextlib
import http.server
import io
import json
import os
import pathlib
import sys
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import redmine  # noqa: E402

KEY = "test-key-not-real"
ISSUE = {
    "id": 123, "subject": "ログイン失敗の回数制限", "description": "工程: spec\nモード: standard",
    "status": {"name": "新規"}, "tracker": {"name": "機能"},
    "journals": [{"notes": f"コメント{n}", "user": {"name": "山田"}, "created_on": "2026-11-01"} for n in range(1, 8)]
    + [{"notes": "", "user": {"name": "山田"}}],
}


class Handler(http.server.BaseHTTPRequestHandler):
    log = []

    def _send(self, code, obj=None):
        raw = json.dumps(obj).encode("utf-8") if obj is not None else b""
        self.send_response(code)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _handle(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n)) if n else None
        Handler.log.append((self.command, self.path, body))
        if self.headers.get("X-Redmine-API-Key") != KEY:
            return self._send(401)
        path = self.path.split("?")[0]
        if self.command == "GET" and path == "/issues/123.json":
            return self._send(200, {"issue": ISSUE})
        if self.command == "GET" and path == "/issues/999.json":
            return self._send(404)
        if self.command == "GET" and path == "/issues.json":
            return self._send(200, {"issues": [ISSUE]})
        if self.command == "GET" and path == "/issue_statuses.json":
            return self._send(200, {"issue_statuses": [{"id": 1, "name": "新規"}, {"id": 3, "name": "解決"}]})
        if self.command == "GET" and path == "/trackers.json":
            return self._send(200, {"trackers": [{"id": 2, "name": "機能"}]})
        if self.command == "PUT" and path == "/issues/123.json":
            return self._send(204)
        if self.command == "POST" and path == "/issues.json":
            return self._send(201, {"issue": {"id": 124}})
        self._send(500)

    do_GET = do_PUT = do_POST = _handle

    def log_message(self, *args):
        pass


class RedmineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        os.environ["REDMINE_URL"] = f"http://127.0.0.1:{cls.server.server_port}"
        os.environ["REDMINE_API_KEY"] = KEY

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        Handler.log.clear()
        conf = redmine.config()
        conf["redmine_project"] = "inv-b"
        conf["redmine_api_key_env"] = "REDMINE_API_KEY"
        self.r = redmine.Redmine(conf)

    def test_view_shows_ticket_and_limits_notes(self):
        out = self.r.view(123, 5)
        self.assertIn("#123 ログイン失敗の回数制限", out)
        self.assertIn("工程: spec", out)
        self.assertNotIn("コメント2\n", out + "\n")
        self.assertIn("コメント7", out)
        self.assertIn("全 7 件", out)
        self.assertIn("include=journals", Handler.log[0][1])

    def test_view_without_notes(self):
        self.assertNotIn("コメント7", self.r.view(123, 0))

    def test_list_filters_by_project(self):
        self.assertIn("#123 [新規]", self.r.list("open", 25))
        self.assertIn("project_id=inv-b", Handler.log[0][1])

    def test_comment_sends_notes(self):
        self.r.comment(123, "まとめ")
        self.assertEqual(Handler.log[0], ("PUT", "/issues/123.json", {"issue": {"notes": "まとめ"}}))

    def test_create_resolves_tracker_name(self):
        out = self.r.create("件名", "本文", "機能")
        self.assertIn("#124", out)
        self.assertEqual(
            Handler.log[-1][2],
            {"issue": {"project_id": "inv-b", "subject": "件名", "description": "本文", "tracker_id": 2}},
        )

    def test_status_resolves_name(self):
        self.r.status(123, "解決")
        self.assertEqual(Handler.log[-1][2], {"issue": {"status_id": 3}})

    def test_unknown_status_lists_choices(self):
        with self.assertRaises(SystemExit) as e:
            self.r.status(123, "完了")
        self.assertIn("新規、解決", str(e.exception))

    def test_missing_ticket_explains(self):
        with self.assertRaises(SystemExit) as e:
            self.r.view(999, 5)
        self.assertIn("404", str(e.exception))

    def test_wrong_key_explains_without_leaking_key(self):
        os.environ["REDMINE_API_KEY"] = "wrong"
        try:
            with self.assertRaises(SystemExit) as e:
                redmine.Redmine(redmine.config()).view(123, 5)
        finally:
            os.environ["REDMINE_API_KEY"] = KEY
        self.assertIn("401", str(e.exception))
        self.assertNotIn("wrong", str(e.exception))

    def test_missing_key_stops_before_any_request(self):
        del os.environ["REDMINE_API_KEY"]
        try:
            with self.assertRaises(SystemExit):
                redmine.Redmine(redmine.config())
        finally:
            os.environ["REDMINE_API_KEY"] = KEY
        self.assertEqual(Handler.log, [])

    def test_command_line(self):
        buf = io.StringIO()
        real = sys.stdout
        buf.reconfigure = lambda **kw: None
        sys.stdout = buf
        try:
            with contextlib.suppress(SystemExit):
                redmine.main(["view", "123", "--notes", "1"])
        finally:
            sys.stdout = real
        self.assertIn("コメント7", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
