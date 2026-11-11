"""Vercel's standard-library Python function entry point."""

from urllib.parse import parse_qs, urlsplit

from testfirst.web import Handler


class handler(Handler):
    deployed = True

    def route(self):
        path = urlsplit(self.path)
        if path.path in ("/api/state", "/api/action"):
            self.path = path.path
        elif path.path in ("/api", "/api/index"):
            query = parse_qs(path.query)
            if query.get("route") in (["state"], ["action"]):
                self.path = "/api/" + query["route"][0]

    def do_GET(self):
        self.route()
        super().do_GET()

    def do_POST(self):
        self.route()
        super().do_POST()
