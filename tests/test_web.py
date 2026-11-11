from http.client import HTTPConnection
import json
import threading
import unittest
from unittest.mock import patch

from testfirst.challenges import CHALLENGES
from testfirst.web import BrowserSession, Handler, make_server


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
        self.server.session = BrowserSession()

    def request(self, method="GET", path="/api/state", data=None, headers=None, raw=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
        request_headers = {"Content-Type": "application/json"} if body is not None else {}
        request_headers.update(headers or {})
        try:
            connection.request(method, path, body, request_headers)
            response = connection.getresponse()
            payload = response.read()
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
                before = self.server.session.state()
                status, _, _ = self.request("POST", "/api/action", data, raw=b"null" if data is None else None)
                self.assertEqual(status, 400)
                self.assertEqual(self.server.session.state(), before)
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


if __name__ == "__main__":
    unittest.main()
