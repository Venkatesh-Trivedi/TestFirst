from http.client import HTTPConnection
import json
import threading
import unittest
from unittest.mock import patch

from testfirst.challenges import CHALLENGES
from testfirst.web import BrowserSession, Handler, make_server
from testfirst.cookies import COOKIE_LIMIT, decode_session, read_cookie


class BrowserAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.logging = patch.object(Handler, "log_message")
        cls.logging.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.logging.stop()

    def setUp(self):
        self.cookie = ""

    def request(self, method="GET", path="/api/state", data=None, headers=None, raw=None, server=None):
        server = server or self.server
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
        request_headers = {"Content-Type": "application/json"} if body is not None else {}
        if self.cookie:
            request_headers["Cookie"] = self.cookie
        if method == "POST":
            request_headers["Origin"] = f"http://127.0.0.1:{server.server_port}"
        request_headers.update(headers or {})
        request_headers = {key: value for key, value in request_headers.items() if value is not None}
        try:
            connection.request(method, path, body, request_headers)
            response = connection.getresponse()
            payload = response.read()
            if response.getheader("Set-Cookie"):
                self.cookie = response.getheader("Set-Cookie").split(";", 1)[0]
            if "application/json" in response.getheader("Content-Type", ""):
                payload = json.loads(payload)
            return response.status, payload, dict(response.getheaders())
        finally:
            connection.close()

    def act(self, action, **fields):
        status, state, _ = self.request("POST", "/api/action", {"action": action, **fields})
        self.assertEqual(status, 200, state)
        return state

    def solve(self, index):
        self.act("select", challenge=index)
        numbers, prediction = [("[-2,-1]", "-1"), ("[1,3,3]", "1"), ("[2,1]", "1")][index]
        return self.act("submit", numbers=numbers, prediction=prediction)

    def test_initial_state_has_exactly_three_challenges_and_no_spoilers(self):
        status, state, headers = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(state["view"], "menu")
        self.assertIsNone(state["result"])
        self.assertEqual(len(state["challenges"]), 3)
        for data, challenge in zip(state["challenges"], CHALLENGES):
            self.assertEqual(data["source"], challenge.source)
            self.assertEqual(data["specification"], challenge.specification)
            self.assertEqual(data["hints"], [])
            self.assertFalse(data["completed"])
            self.assertNotIn("explanation", data)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_all_four_outcomes_and_answer_redaction(self):
        self.act("select", challenge=0)
        for numbers, prediction, outcome in [
            ("[true]", "1", "invalid_input"),
            ("[-1]", "0", "incorrect_prediction"),
            ("[1,2]", "2", "no_bug"),
            ("[-1]", "-1", "success"),
        ]:
            with self.subTest(outcome=outcome):
                state = self.act("submit", numbers=numbers, prediction=prediction)
                self.assertEqual(state["result"]["outcome"], outcome)
                if outcome != "success":
                    self.assertEqual(set(state["result"]), {"outcome", "message"})
                    self.assertFalse(state["challenges"][0]["completed"])
                else:
                    self.assertEqual(state["result"]["expected"], -1)
                    self.assertEqual(state["result"]["actual"], 0)
                    self.assertEqual(state["result"]["trace"], list(CHALLENGES[0].trace([-1])))
                    self.assertEqual(state["result"]["explanation"], CHALLENGES[0].explanation)

    def test_new_challenges_use_engine_and_their_constraints(self):
        self.act("select", challenge=1)
        state = self.act("submit", numbers="[2,2]", prediction="2")
        self.assertEqual(state["result"]["outcome"], "invalid_input")
        self.assertEqual(state["result"]["message"], "Include at least 2 different numbers.")
        for index in (1, 2):
            state = self.solve(index)
            self.assertEqual(state["result"]["outcome"], "success")
            self.assertEqual(state["result"]["expected"], 1)
            self.assertEqual(state["result"]["actual"], 3 if index == 1 else 2)

    def test_displayed_example_is_neutral_for_every_challenge(self):
        for index, prediction in enumerate(("3", "2", "1")):
            self.act("select", challenge=index)
            state = self.act("submit", numbers="[1, 2, 3]", prediction=prediction)
            self.assertEqual(state["result"]["outcome"], "no_bug")
            self.assertFalse(state["challenges"][index]["completed"])

    def test_hints_only_disclosed_on_request_and_limited(self):
        self.act("select", challenge=0)
        for used in range(1, 5):
            state = self.act("hint")
            self.assertEqual(state["challenges"][0]["hints_used"], min(used, 3))
            self.assertEqual(state["challenges"][0]["hints"], list(CHALLENGES[0].hints[:used]))
        self.act("menu")
        state = self.act("select", challenge=0)
        self.assertEqual(state["challenges"][0]["hints_used"], 3)
        state = self.act("restart")
        self.assertEqual(state["challenges"][0]["hints"], [])

    def test_replay_clears_answers_and_hints_but_keeps_completion(self):
        self.act("select", challenge=1)
        self.act("hint")
        self.act("select", challenge=0)
        self.act("hint")
        self.act("submit", numbers="[-1]", prediction="-1")
        state = self.act("replay")
        self.assertEqual(state["view"], "challenge")
        self.assertIsNone(state["result"])
        self.assertTrue(state["challenges"][0]["completed"])
        self.assertEqual(state["challenges"][0]["hints"], [])
        self.assertEqual(state["challenges"][1]["hints_used"], 1)
        state = self.act("submit", numbers="[-1]", prediction="0")
        self.assertEqual(set(state["result"]), {"outcome", "message"})

    def test_next_progression_and_final_summary(self):
        for index in range(3):
            self.solve(index)
            state = self.act("next")
            self.assertIsNone(state["result"])
            self.assertEqual(state["view"], "summary" if index == 2 else "challenge")
            self.assertEqual(state["selected"], min(index + 1, 2))
        self.assertEqual(sum(c["completed"] for c in state["challenges"]), 3)
        state = self.act("menu")
        self.assertEqual(state["view"], "menu")

    def test_skips_repeated_success_and_server_restart(self):
        self.solve(2)
        self.act("replay")
        self.act("submit", numbers="[2,1]", prediction="1")
        state = self.act("next")
        self.assertEqual(state["view"], "summary")
        self.assertEqual([c["completed"] for c in state["challenges"]], [False, False, True])
        self.assertFalse(any(c["completed"] for c in BrowserSession().state()["challenges"]))

    def test_invalid_actions_do_not_mutate_session(self):
        for data in [None, [], {}, {"action": 1}, {"action": "unknown"},
                     {"action": "select", "challenge": True}, {"action": "select", "challenge": -1},
                     {"action": "select", "challenge": 3}, {"action": "next"},
                     {"action": "replay"}, {"action": "submit", "numbers": "[]", "prediction": "0"}]:
            with self.subTest(data=data):
                before = self.request()[1]
                status, _, _ = self.request("POST", "/api/action", data, raw=b"null" if data is None else None)
                self.assertEqual(status, 400)
                self.assertEqual(self.request()[1], before)
        self.act("select", challenge=0)
        self.assertEqual(self.request("POST", "/api/action", {"action": "submit", "numbers": [1], "prediction": 1})[0], 400)
        self.solve(0)
        for action in ("submit", "hint", "restart"):
            self.assertEqual(self.request("POST", "/api/action", {"action": action})[0], 400)

    def test_http_boundaries_and_static_allowlist(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        for path in ("/", "/app.js", "/style.css", "/tokens.css", "/base.css"):
            status, body, headers = self.request(path=path)
            self.assertEqual(status, 200)
            self.assertTrue(body)
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        for path in ("/../engine.py", "/.git/config", "/not-found"):
            self.assertEqual(self.request(path=path)[0], 404)
        for raw in (b"{", b"\xff", b"[" * 2000 + b"]" * 2000):
            self.assertEqual(self.request("POST", "/api/action", raw=raw)[0], 400)
        self.assertEqual(self.request("POST", "/api/action", raw=b" " * 16385)[0], 413)
        self.assertEqual(self.request("POST", "/api/action", raw=b"{}")[0], 400)
        self.assertEqual(self.request("POST", "/api/action", raw=b"{}", headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("POST", "/other", {})[0], 404)
        self.assertEqual(self.request(headers={"Host": "attacker.example"})[0], 403)
        self.assertEqual(self.request("POST", "/api/action", {"action": "menu"}, headers={"Origin": "http://attacker.example"})[0], 403)
        status, _, _ = self.request("POST", "/api/action", {"action": "menu"}, headers={"Origin": f"http://127.0.0.1:{self.server.server_port}"})
        self.assertEqual(status, 200)

    def test_two_browser_cookie_jars_are_independent(self):
        self.act("select", challenge=0)
        self.act("hint")
        self.act("submit", numbers="[-1]", prediction="-1")
        browser_a = self.cookie
        self.cookie = ""
        browser_b = self.request()[1]
        self.assertEqual(browser_b["view"], "menu")
        self.assertFalse(any(c["completed"] for c in browser_b["challenges"]))
        self.act("select", challenge=1)
        self.act("hint")
        browser_b_cookie = self.cookie
        self.cookie = browser_a
        browser_a_state = self.request()[1]
        self.assertEqual(browser_a_state["result"]["outcome"], "success")
        self.assertEqual([c["hints_used"] for c in browser_a_state["challenges"]], [1, 0, 0])
        self.cookie = browser_b_cookie
        self.assertEqual([c["hints_used"] for c in self.request()[1]["challenges"]], [0, 1, 0])

    def test_fresh_backend_restores_cookie_without_process_session(self):
        self.act("select", challenge=2)
        self.act("hint")
        expected = self.act("submit", numbers="[2,1]", prediction="1")
        fresh = make_server(0)
        fresh.session_secret = self.server.session_secret
        worker = threading.Thread(target=fresh.serve_forever, daemon=True)
        worker.start()
        try:
            self.assertFalse(hasattr(fresh, "session"))
            self.assertEqual(self.request(server=fresh)[1], expected)
            state = self.request("POST", "/api/action", {"action": "next"}, server=fresh)[1]
            self.assertEqual(state["view"], "summary")
            self.assertEqual([c["completed"] for c in state["challenges"]], [False, False, True])
        finally:
            fresh.shutdown()
            fresh.server_close()
            worker.join()

    def test_cookie_is_small_and_contains_no_hint_answer_or_trace_data(self):
        self.act("select", challenge=2)
        self.act("hint")
        self.act("submit", numbers="[20,-20]", prediction="-20")
        _, _, headers = self.request()
        header = headers["Set-Cookie"]
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=Strict", header)
        self.assertIn("Path=/", header)
        self.assertNotIn("Domain=", header)
        self.assertNotIn("; Secure", header)
        self.assertLess(len(header), 4096)
        token = read_cookie(self.cookie)
        self.assertLessEqual(len(token), COOKIE_LIMIT)
        data = decode_session(token, self.server.session_secret)
        self.assertEqual(data["result"], {"numbers": [20, -20]})
        self.assertEqual(data["hints"], [0, 0, 1])
        self.assertEqual(set(data), {"v", "exp", "selected", "view", "hints", "completed", "result"})
        serialized = json.dumps(data)
        for secret_field in ("reference", "expected", "actual", "trace", "explanation", "prediction"):
            self.assertNotIn(secret_field, serialized)
        for challenge in CHALLENGES:
            for hint in challenge.hints:
                self.assertNotIn(hint, serialized)

    def test_tampered_cookie_cannot_restore_or_forge_progress(self):
        self.solve(0)
        valid = read_cookie(self.cookie)
        body, signature = valid.split(".")
        for bad in ("x" + valid, body + "." + "0" * 64, valid + "x", "x" * (COOKIE_LIMIT + 1)):
            self.cookie = "testfirst_session=" + bad
            status, state, _ = self.request()
            self.assertEqual(status, 200)
            self.assertEqual(state["view"], "menu")
            self.assertIsNone(state["result"])
            self.assertFalse(any(c["completed"] for c in state["challenges"]))

    def test_failed_attempt_feedback_survives_fresh_request_without_answers(self):
        self.act("select", challenge=0)
        for numbers, prediction in (("bad", "0"), ("[-1]", "0"), ("[1]", "1")):
            expected = self.act("submit", numbers=numbers, prediction=prediction)
            self.assertEqual(self.request()[1], expected)
            self.assertEqual(set(expected["result"]), {"outcome", "message"})

    def test_local_guard_requires_origin_for_mutations_and_ignores_forwarded_headers(self):
        for headers in ({"Origin": None}, {"Origin": ""}, {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"},
                        {"Origin": "https://evil.example", "X-Forwarded-Host": "evil.example", "X-Forwarded-Proto": "https"}):
            self.assertEqual(self.request("POST", "/api/action", {"action": "menu"}, headers=headers)[0], 403)


if __name__ == "__main__":
    unittest.main()
