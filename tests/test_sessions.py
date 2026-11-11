import base64
from http.client import HTTPConnection
from http.server import HTTPServer
import json
from pathlib import Path
import secrets
import threading
import unittest
from unittest.mock import patch

from api.index import handler
from testfirst.cookies import COOKIE_LIMIT, SESSION_SECONDS, decode_session, encode_session, environment_secret, read_cookie
from testfirst.web import BrowserSession, Handler, make_server


class CookieTests(unittest.TestCase):
    def setUp(self):
        self.secret = secrets.token_bytes(32)

    def test_signing_expiry_rotation_and_limits(self):
        snapshot = BrowserSession().snapshot()
        with patch("testfirst.cookies.time.time", return_value=1000):
            value = encode_session(snapshot, self.secret)
            data = decode_session(value, self.secret)
            self.assertEqual(data["exp"], 1000 + SESSION_SECONDS)
            self.assertEqual(BrowserSession.restore(data).state(), BrowserSession().state())
            self.assertIsNone(decode_session(value, secrets.token_bytes(32)))
            with self.assertRaises(ValueError):
                encode_session({"extra": "x" * COOKIE_LIMIT}, self.secret)
        with patch("testfirst.cookies.time.time", return_value=1000 + SESSION_SECONDS + 1):
            self.assertIsNone(decode_session(value, self.secret))
        with patch("testfirst.cookies.time.time", return_value=0):
            self.assertIsNone(decode_session(value, self.secret))

    def test_modified_progress_invalidates_signature(self):
        value = encode_session(BrowserSession().snapshot(), self.secret)
        body, signature = value.split(".")
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        data["completed"] = [True, True, True]
        forged = base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode() + "." + signature
        self.assertIsNone(decode_session(forged, self.secret))

    def test_largest_allowed_state_stays_well_under_cookie_limit(self):
        session = BrowserSession()
        for game in session.games:
            game.hints_used = 3
            game.completed = True
        session.act({"action": "select", "challenge": 2})
        session.act({"action": "submit", "numbers": "[20,-20,20,-20,20,-20,20,-20]", "prediction": "-20"})
        value = encode_session(session.snapshot(), self.secret)
        self.assertLess(len(value), 700)
        restored = BrowserSession.restore(decode_session(value, self.secret))
        self.assertEqual(restored.state(), session.state())

    def test_authenticated_but_invalid_schema_resets_without_execution(self):
        original = BrowserSession().snapshot()
        for changes in ({"selected": True}, {"selected": 3}, {"hints": [4, 0, 0]},
                        {"hints": [True, 0, 0]}, {"completed": [1, False, False]},
                        {"completed": []}, {"view": "unknown"}, {"view": "summary"},
                        {"result": {"numbers": []}}, {"extra": "unexpected"}):
            data = decode_session(encode_session({**original, **changes}, self.secret), self.secret)
            self.assertEqual(BrowserSession.restore(data).state(), BrowserSession().state())

    def test_cookie_parser_rejects_garbage_and_oversized_header(self):
        self.assertIsNone(read_cookie(""))
        self.assertIsNone(read_cookie("x" * 8193))
        self.assertIsNone(read_cookie("invalid cookie"))
        for token in ("", "bad", ".", "%%%" + "." + "a" * 64, "x" * 2049):
            self.assertIsNone(decode_session(token, self.secret))

    def test_missing_or_short_secret_fails_closed_and_is_not_generated_for_deployment(self):
        for value in ("", "too-short"):
            with patch.dict("os.environ", {"TESTFIRST_SESSION_SECRET": value}):
                with self.assertRaises(RuntimeError):
                    environment_secret()
        secret = secrets.token_urlsafe(32)
        with patch.dict("os.environ", {"TESTFIRST_SESSION_SECRET": secret}):
            self.assertEqual(environment_secret(), secret.encode())
            with make_server(0) as first, make_server(0) as second:
                self.assertEqual(first.session_secret, second.session_secret)


class VercelHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict("os.environ", {
            "TESTFIRST_SESSION_SECRET": secrets.token_urlsafe(32),
            "TESTFIRST_ALLOWED_ORIGINS": "https://practice.example, https://custom.example",
            "VERCEL_URL": "preview.example.vercel.app",
        })
        cls.env.start()
        cls.logging = patch.object(Handler, "log_message")
        cls.logging.start()
        cls.server = HTTPServer(("127.0.0.1", 0), handler)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()
        cls.logging.stop()
        cls.env.stop()

    def request(self, method="GET", path="/api/index?route=state", body=None, headers=None):
        request_headers = {"Host": "practice.example", "Origin": "https://practice.example", "Content-Type": "application/json"}
        request_headers.update(headers or {})
        request_headers = {key: value for key, value in request_headers.items() if value is not None}
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path, json.dumps(body) if body is not None else None, request_headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read()), dict(response.getheaders())
        finally:
            connection.close()

    def test_https_proxy_requests_use_secure_cookie_and_rewrite_routes(self):
        status, state, headers = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(state["view"], "menu")
        self.assertIn("; Secure", headers["Set-Cookie"])
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        status, state, headers = self.request("POST", "/api/index?route=action", {"action": "select", "challenge": 1}, {"Cookie": cookie})
        self.assertEqual(status, 200)
        self.assertEqual(state["selected"], 1)
        # Some proxies preserve the original URL rather than the rewritten URL.
        self.assertEqual(self.request(path="/api/state")[0], 200)
        self.assertEqual(self.request(path="/api/state?route=state")[0], 200)
        for path in ("/api/index?route=other", "/api/index?route=state&route=action"):
            self.assertEqual(self.request(path=path)[0], 404)

    def test_unknown_hosts_cross_origin_and_missing_origin_are_rejected(self):
        for headers in ({"Host": "evil.example", "Origin": "https://evil.example"},
                        {"Origin": "https://evil.example"}, {"Origin": "http://practice.example"},
                        {"Origin": "https://practice.example.evil.example"}, {"Origin": None}, {"Origin": ""},
                        {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"},
                        {"Sec-Fetch-Site": "same-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request("POST", "/api/index?route=action", {"action": "menu"}, headers)[0], 403)

    def test_preview_and_custom_domain_and_missing_configuration(self):
        for host in ("preview.example.vercel.app", "custom.example"):
            self.assertEqual(self.request(headers={"Host": host, "Origin": "https://" + host})[0], 200)
        with patch.dict("os.environ", {"TESTFIRST_SESSION_SECRET": ""}):
            status, data, headers = self.request()
            self.assertEqual(status, 503)
            self.assertNotIn("Set-Cookie", headers)
            self.assertNotIn("SECRET", json.dumps(data))
        with patch.dict("os.environ", {"TESTFIRST_ALLOWED_ORIGINS": "", "VERCEL_URL": ""}):
            self.assertEqual(self.request()[0], 403)
        with patch.dict("os.environ", {"TESTFIRST_ALLOWED_ORIGINS": "https://[invalid"}):
            self.assertEqual(self.request()[0], 403)

    def test_configuration_serves_existing_assets_and_routes_existing_api(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "vercel.json").read_text())
        self.assertIsNone(config["framework"])
        self.assertEqual(config["outputDirectory"], "testfirst/static")
        for source, destination in (("/api/state", "/api/index?route=state"), ("/api/action", "/api/index?route=action")):
            self.assertIn({"source": source, "destination": destination}, config["rewrites"])
        self.assertTrue((root / config["outputDirectory"] / "index.html").is_file())
        self.assertEqual((root / ".python-version").read_text().strip(), "3.13")


if __name__ == "__main__":
    unittest.main()
