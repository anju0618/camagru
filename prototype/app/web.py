import hmac
import json
import logging
import os
import re
import time
from urllib.parse import parse_qs

from . import db, security, views

log = logging.getLogger("camagru")

SESSION_TTL = 7 * 24 * 3600
MAX_BODY = 6 * 1024 * 1024
PUBLIC_DIR = os.path.realpath(os.path.join(db.BASE, "public"))
SECURE = os.environ.get("BASE_URL", "").startswith("https://")

SECURITY_HEADERS = [
    ("Content-Security-Policy",
     "default-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
     "style-src 'self'; script-src 'self'; frame-ancestors 'none'; "
     "form-action 'self'; base-uri 'none'"),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "same-origin"),
]

MIME = {".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8",
        ".png": "image/png"}


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class Response:
    def __init__(self, body=b"", status="200 OK", ctype="text/html; charset=utf-8", headers=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.body = body
        self.status = status
        self.headers = [("Content-Type", ctype)] + list(headers or [])


def redirect(location):
    return Response(b"", "303 See Other", headers=[("Location", location)])


def json_response(obj, status="200 OK"):
    return Response(json.dumps(obj), status, "application/json",
                    [("Cache-Control", "no-store")])


class Request:
    def __init__(self, environ, conn):
        self.environ = environ
        self.conn = conn
        self.method = environ.get("REQUEST_METHOD", "GET")
        self.path = environ.get("PATH_INFO", "/") or "/"
        self.query = {k: v[0] for k, v in parse_qs(
            environ.get("QUERY_STRING", ""), keep_blank_values=True).items()}
        self.cookies = {}
        for part in environ.get("HTTP_COOKIE", "").split(";"):
            if "=" in part:
                name, _, value = part.strip().partition("=")
                self.cookies[name] = value
        self._form = None
        self.session = None
        self.user = None
        self.out_cookies = []

    @property
    def form(self):
        if self._form is None:
            self._form = {}
            try:
                length = int(self.environ.get("CONTENT_LENGTH") or 0)
            except ValueError:
                length = 0
            if length > MAX_BODY:
                raise HttpError("413 Payload Too Large", "That upload is too large.")
            if length > 0:
                body = self.environ["wsgi.input"].read(length)
                if self.environ.get("CONTENT_TYPE", "").startswith("application/x-www-form-urlencoded"):
                    self._form = {k: v[0] for k, v in parse_qs(
                        body.decode("utf-8", "replace"), keep_blank_values=True).items()}
        return self._form

    # --- sessions ---------------------------------------------------------
    def _set_cookie(self, sid, max_age):
        value = "sid=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d" % (sid, max_age)
        if SECURE:
            value += "; Secure"
        self.out_cookies = [("Set-Cookie", value)]

    def _new_session(self, user_id):
        sid = security.new_token()
        csrf = security.new_token()
        self.conn.execute(
            "INSERT INTO sessions (id, user_id, csrf, created_at) VALUES (?, ?, ?, ?)",
            (security.sha(sid), user_id, csrf, int(time.time())))
        self.session = {"id": security.sha(sid), "user_id": user_id, "csrf": csrf, "flash": None}
        self._set_cookie(sid, SESSION_TTL)

    def _load_user(self):
        self.user = None
        if self.session["user_id"] is not None:
            self.user = self.conn.execute(
                "SELECT * FROM users WHERE id = ?", (self.session["user_id"],)).fetchone()

    def load_session(self):
        sid = self.cookies.get("sid", "")
        row = None
        if 0 < len(sid) <= 64:
            row = self.conn.execute(
                "SELECT * FROM sessions WHERE id = ? AND created_at > ?",
                (security.sha(sid), int(time.time()) - SESSION_TTL)).fetchone()
        if row:
            self.session = dict(row)
            self._load_user()
        else:
            self._new_session(None)

    def login(self, user_id):
        """Start a fresh session for the user (prevents session fixation)."""
        self.conn.execute("DELETE FROM sessions WHERE id = ?", (self.session["id"],))
        self._new_session(user_id)
        self._load_user()

    def logout(self):
        self.conn.execute("DELETE FROM sessions WHERE id = ?", (self.session["id"],))
        self._new_session(None)
        self.user = None

    @property
    def csrf(self):
        return self.session["csrf"]

    def check_csrf(self):
        sent = self.form.get("csrf", "").encode("utf-8", "replace")
        return hmac.compare_digest(sent, self.csrf.encode())

    def flash(self, text, kind="ok"):
        self.session["flash"] = "%s|%s" % (kind, text)
        self.conn.execute("UPDATE sessions SET flash = ? WHERE id = ?",
                          (self.session["flash"], self.session["id"]))

    def page(self, title, body, status="200 OK", scripts=()):
        flash = None
        if self.session.get("flash"):
            kind, _, text = self.session["flash"].partition("|")
            flash = (kind, text)
            self.session["flash"] = None
            self.conn.execute("UPDATE sessions SET flash = NULL WHERE id = ?",
                              (self.session["id"],))
        html = views.layout(title, body, self.user, self.csrf, flash, scripts)
        return Response(html, status, headers=[("Cache-Control", "no-store")])


# --- routing -------------------------------------------------------------
ROUTES = []


def route(method, pattern):
    def decorator(fn):
        ROUTES.append((method, re.compile(pattern), fn))
        return fn
    return decorator


def dispatch(req):
    allowed = []
    for method, regex, fn in ROUTES:
        match = regex.fullmatch(req.path)
        if not match:
            continue
        allowed.append(method)
        if method == req.method:
            if req.method == "POST" and not req.check_csrf():
                raise HttpError("403 Forbidden", "Invalid or missing form token. "
                                "Please go back, reload the page and try again.")
            return fn(req, *match.groups())
    if allowed:
        raise HttpError("405 Method Not Allowed", "Method not allowed.")
    raise HttpError("404 Not Found", "Page not found.")


@route("GET", r"/static/(.+)")
def static(req, name):
    path = os.path.realpath(os.path.join(PUBLIC_DIR, name))
    ext = os.path.splitext(path)[1].lower()
    if not path.startswith(PUBLIC_DIR + os.sep) or ext not in MIME or not os.path.isfile(path):
        raise HttpError("404 Not Found", "Page not found.")
    with open(path, "rb") as f:
        data = f.read()
    return Response(data, ctype=MIME[ext], headers=[("Cache-Control", "no-cache")])


def error_response(err):
    body = views.message("%s" % err.status, err.message, "/", "Back to the gallery")
    html = views.layout(err.status, body, None, "")
    extra = [("Allow", "GET, POST")] if err.status.startswith("405") else []
    return Response(html, err.status, headers=extra)


def application(environ, start_response):
    conn = db.connect()
    req = None
    try:
        try:
            req = Request(environ, conn)
            req.load_session()
            resp = dispatch(req)
            conn.commit()
        except HttpError as err:
            conn.commit()
            resp = error_response(err)
        except Exception:
            conn.rollback()
            log.exception("unhandled error")
            resp = error_response(HttpError("500 Internal Server Error",
                                            "Something went wrong on our side."))
    finally:
        conn.close()
    headers = resp.headers + SECURITY_HEADERS + (req.out_cookies if req else [])
    headers.append(("Content-Length", str(len(resp.body))))
    start_response(resp.status, headers)
    return [resp.body]
