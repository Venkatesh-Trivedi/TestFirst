"""Local browser interface. Run with python -m testfirst.web."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path

from .challenges import CHALLENGES
from .engine import Game, Outcome


class BrowserSession:
    """One shared, in-memory practice session per server process."""

    def __init__(self):
        self.games = [Game(challenge) for challenge in CHALLENGES]
        self.selected = 0
        self.view = "menu"
        self.result = None

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
                    self.result.update(
                        expected=attempt.expected, actual=attempt.actual,
                        trace=attempt.trace, explanation=game.challenge.explanation,
                    )
        else:
            raise ValueError("Unknown action.")
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
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def reply(self, status, body, content_type="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def local_request(self):
        address = f"127.0.0.1:{self.server.server_port}"
        origin = self.headers.get("Origin")
        return self.headers.get("Host") == address and origin in (None, f"http://{address}")

    def do_GET(self):
        if not self.local_request():
            self.reply(403, {"error": "Open the app at its 127.0.0.1 address."})
        elif self.path == "/api/state":
            self.reply(200, self.server.session.state())
        elif self.path in ASSETS:
            filename, content_type = ASSETS[self.path]
            self.reply(200, (STATIC / filename).read_bytes(), content_type)
        else:
            self.reply(404, {"error": "Not found."})

    def do_POST(self):
        if not self.local_request():
            self.reply(403, {"error": "Requests must come from this app."})
            return
        if self.path != "/api/action":
            self.reply(404, {"error": "Not found."})
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
            state = self.server.session.act(data)
        except (ValueError, RecursionError) as error:
            self.reply(400, {"error": str(error)})
            return
        self.reply(200, state)


def make_server(port=8000):
    server = HTTPServer(("127.0.0.1", port), Handler)
    server.session = BrowserSession()
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
