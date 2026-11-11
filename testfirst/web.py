"""Browser HTTP handler shared by localhost and the Vercel entry point."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
from urllib.parse import urlsplit

from .challenges import CHALLENGES
from .engine import Game, Outcome, parse_numbers
from .cookies import cookie_header, decode_session, environment_secret, read_cookie


class BrowserSession:
    """Per-request game state, restored from an authenticated browser cookie."""

    def __init__(self):
        self.games = [Game(challenge) for challenge in CHALLENGES]
        self.selected = 0
        self.view = "menu"
        self.result = None
        self.successful_numbers = None

    def snapshot(self):
        result = {"numbers": self.successful_numbers} if self.successful_numbers is not None else self.result
        return {
            "selected": self.selected, "view": self.view,
            "hints": [game.hints_used for game in self.games],
            "completed": [game.completed for game in self.games], "result": result,
        }

    @classmethod
    def restore(cls, data):
        session = cls()
        if data is None:
            return session
        try:
            if set(data) != {"v", "exp", "selected", "view", "hints", "completed", "result"}:
                raise ValueError("Invalid session fields.")
            index = data["selected"]
            if type(index) is not int or not 0 <= index < len(session.games):
                raise ValueError("Invalid selection.")
            if data["view"] not in ("menu", "challenge", "summary"):
                raise ValueError("Invalid view.")
            if type(data["hints"]) is not list or type(data["completed"]) is not list:
                raise ValueError("Invalid progress.")
            if len(data["hints"]) != len(session.games) or len(data["completed"]) != len(session.games):
                raise ValueError("Invalid progress length.")
            for game, hints, completed in zip(session.games, data["hints"], data["completed"]):
                if type(hints) is not int or not 0 <= hints <= len(game.challenge.hints) or type(completed) is not bool:
                    raise ValueError("Invalid progress values.")
                game.hints_used, game.completed = hints, completed
            session.selected, session.view = index, data["view"]
            result = data["result"]
            if result is not None:
                if session.view != "challenge" or type(result) is not dict:
                    raise ValueError("Invalid result.")
                if set(result) == {"numbers"}:
                    game = session.games[index]
                    if not game.completed:
                        raise ValueError("Missing completion mark.")
                    numbers = parse_numbers(json.dumps(result["numbers"]), game.challenge)
                    session.act({"action": "submit", "numbers": json.dumps(numbers),
                                 "prediction": str(game.challenge.reference(numbers))})
                    if session.result["outcome"] != Outcome.SUCCESS.value:
                        raise ValueError("Counterexample is no longer valid.")
                elif (set(result) == {"outcome", "message"}
                      and result["outcome"] in ("invalid_input", "incorrect_prediction", "no_bug")
                      and type(result["message"]) is str and len(result["message"]) <= 200):
                    session.result = result
                else:
                    raise ValueError("Invalid result fields.")
            if session.view == "summary" and (index != len(session.games) - 1 or not session.games[index].completed):
                raise ValueError("Invalid summary.")
            return session
        except (ValueError, TypeError, KeyError, RecursionError):
            return cls()

    def state(self):
        return {
            "view": self.view,
            "selected": self.selected,
            "challenges": [
                {
                    "id": index,
                    "title": game.challenge.title,
                    "specification": game.challenge.specification,
                    "source": game.challenge.source,
                    "input_rules": game.challenge.input_rules,
                    "hints": list(game.challenge.hints[:game.hints_used]),
                    "hints_used": game.hints_used,
                    "hint_total": len(game.challenge.hints),
                    "completed": game.completed,
                }
                for index, game in enumerate(self.games)
            ],
            "result": self.result,
        }

    def act(self, data):
        if type(data) is not dict or type(data.get("action")) is not str:
            raise ValueError("Provide an action in a JSON object.")
        action = data["action"]
        game = self.games[self.selected]
        if action == "menu":
            self.view = "menu"
            self.result = None
        elif action == "select":
            index = data.get("challenge")
            if type(index) is not int or not 0 <= index < len(self.games):
                raise ValueError("Choose an existing challenge.")
            self.selected = index
            self.view = "challenge"
            self.result = None
        elif action in {"next", "replay"}:
            if not self.result or self.result["outcome"] != Outcome.SUCCESS.value:
                raise ValueError("Complete the current challenge before continuing or replaying.")
            if action == "replay":
                game.restart()
            elif self.selected == len(self.games) - 1:
                self.view = "summary"
            else:
                self.selected += 1
            self.result = None
        elif action in {"submit", "hint", "restart"}:
            if self.view != "challenge":
                raise ValueError("Select a challenge first.")
            if self.result and self.result["outcome"] == Outcome.SUCCESS.value:
                raise ValueError("Choose Next challenge, Replay, or Challenge menu.")
            if action == "hint":
                game.next_hint()
            elif action == "restart":
                game.restart()
                self.result = None
            else:
                if type(data.get("numbers")) is not str or type(data.get("prediction")) is not str:
                    raise ValueError("Input and prediction must be text fields.")
                attempt = game.evaluate(data["numbers"], data["prediction"])
                self.result = {"outcome": attempt.outcome.value, "message": attempt.message}
                # Answers and traces stay private until the player predicts correctly and exposes the bug.
                if attempt.outcome is Outcome.SUCCESS:
                    self.successful_numbers = json.loads(data["numbers"])
                    self.result.update(
                        expected=attempt.expected, actual=attempt.actual,
                        trace=attempt.trace, explanation=game.challenge.explanation,
                    )
        else:
            raise ValueError("Unknown action.")
        if self.result is None:
            self.successful_numbers = None
        return self.state()


STATIC = Path(__file__).with_name("static")
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/tokens.css": ("tokens.css", "text/css; charset=utf-8"),
    "/base.css": ("base.css", "text/css; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    deployed = False

    def setup(self):
        super().setup()
        if not self.deployed:
            self.connection.settimeout(5)

    def reply(self, status, body, content_type="application/json; charset=utf-8", session=None):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if session is not None:
            self.send_header("Set-Cookie", cookie_header(session.snapshot(), self.session_secret(), self.deployed))
        self.end_headers()
        self.wfile.write(body)

    def session_secret(self):
        return environment_secret() if self.deployed else self.server.session_secret

    def allowed_request(self):
        if self.deployed:
            origins = set(os.environ.get("TESTFIRST_ALLOWED_ORIGINS", "").split(","))
            if os.environ.get("VERCEL_URL"):
                origins.add("https://" + os.environ["VERCEL_URL"])
            origins = {origin.strip() for origin in origins if origin.strip()}
            try:
                origins = {origin for origin in origins if urlsplit(origin).scheme == "https"
                           and urlsplit(origin).netloc and origin == "https://" + urlsplit(origin).netloc}
            except ValueError:
                return False
        else:
            origins = {f"http://127.0.0.1:{self.server.server_port}"}
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1:
            return False
        expected = ("https://" if self.deployed else "http://") + hosts[0]
        if expected not in origins:
            return False
        origin = self.headers.get("Origin")
        if len(self.headers.get_all("Origin", [])) > 1 or origin not in (None, expected):
            return False
        if self.path.startswith("/api/"):
            if self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none"):
                return False
            if self.command == "POST" and origin != expected:
                return False
        return True

    def load_session(self):
        return BrowserSession.restore(decode_session(
            read_cookie(self.headers.get("Cookie", "")), self.session_secret(),
        ))

    def session_available(self):
        try:
            self.session_secret()
            return True
        except RuntimeError:
            self.reply(503, {"error": "Session configuration is unavailable."})
            return False

    def do_GET(self):
        if not self.allowed_request():
            self.reply(403, {"error": "Open the app at its configured address."})
        elif self.path == "/api/state":
            if self.session_available():
                session = self.load_session()
                self.reply(200, session.state(), session=session)
        elif self.path in ASSETS:
            filename, content_type = ASSETS[self.path]
            self.reply(200, (STATIC / filename).read_bytes(), content_type)
        else:
            self.reply(404, {"error": "Not found."})

    def do_POST(self):
        if not self.allowed_request():
            self.reply(403, {"error": "Requests must come from this app."})
            return
        if self.path != "/api/action":
            self.reply(404, {"error": "Not found."})
            return
        if not self.session_available():
            return
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            self.reply(415, {"error": "Send JSON."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                self.reply(413, {"error": "Request must contain 1–16384 bytes."})
                return
            data = json.loads(self.rfile.read(length))
            session = self.load_session()
            state = session.act(data)
        except (ValueError, RecursionError) as error:
            self.reply(400, {"error": str(error)})
            return
        self.reply(200, state, session=session)


def make_server(port=8000):
    # Local-only convenience; Vercel never calls this factory or generates a fallback secret.
    os.environ.setdefault("TESTFIRST_SESSION_SECRET", secrets.token_urlsafe(32))
    secret = environment_secret()
    server = HTTPServer(("127.0.0.1", port), Handler)
    server.session_secret = secret
    return server


def main():
    with make_server() as server:
        print("TestFirst: http://127.0.0.1:8000 (Ctrl+C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nSession ended.")


if __name__ == "__main__":
    main()
