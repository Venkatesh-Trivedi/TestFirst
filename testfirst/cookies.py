"""Bounded, authenticated session values; cookies are signed, not encrypted."""

import base64
import hashlib
import hmac
from http.cookies import CookieError, SimpleCookie
import json
import os
import re
import time

COOKIE_NAME = "testfirst_session"
COOKIE_LIMIT = 2048
SESSION_SECONDS = 86400


def environment_secret():
    secret = os.environ.get("TESTFIRST_SESSION_SECRET", "").encode("utf-8")
    if len(secret) < 32:
        raise RuntimeError("TESTFIRST_SESSION_SECRET must contain at least 32 bytes.")
    return secret


def encode_session(state, secret):
    payload = {**state, "v": 1, "exp": int(time.time()) + SESSION_SECONDS}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    value = body.decode("ascii") + "." + signature
    if len(value) > COOKIE_LIMIT:
        raise ValueError("Session exceeds the cookie size limit.")
    return value


def decode_session(value, secret):
    if not value or len(value) > COOKIE_LIMIT or not re.fullmatch(r"[A-Za-z0-9_-]+\.[0-9a-f]{64}", value):
        return None
    body, signature = value.split(".")
    expected = hmac.new(secret, body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if type(payload) is not dict or type(payload.get("v")) is not int or payload["v"] != 1 or type(payload.get("exp")) is not int:
            return None
        now = int(time.time())
        if not now <= payload["exp"] <= now + SESSION_SECONDS:
            return None
        return payload
    except (ValueError, RecursionError):
        return None


def read_cookie(header):
    if len(header) > 8192:
        return None
    try:
        cookie = SimpleCookie()
        cookie.load(header)
        return cookie[COOKIE_NAME].value if COOKIE_NAME in cookie else None
    except CookieError:
        return None


def cookie_header(state, secret, secure):
    value = encode_session(state, secret)
    return (
        f"{COOKIE_NAME}={value}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_SECONDS}"
        + ("; Secure" if secure else "")
    )
