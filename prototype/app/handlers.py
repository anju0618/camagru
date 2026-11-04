import base64
import binascii
import functools
import os
import sqlite3
import time

from . import db, mailer, png, security, views
from .web import HttpError, Response, json_response, redirect, route

VERIFY_TTL = 24 * 3600
RESET_TTL = 3600
MAX_FAILS = 5
LOCK_SECONDS = 300
MAX_IMAGE_BYTES = 4 * 1024 * 1024
OVERLAY_DIR = os.path.join(db.BASE, "public", "overlays")
DATA_URL_PREFIX = "data:image/png;base64,"


def list_overlays():
    try:
        names = [f[:-4] for f in os.listdir(OVERLAY_DIR) if f.endswith(".png")]
    except OSError:
        names = []
    return sorted(n for n in names if n.replace("_", "").replace("-", "").isalnum())


_overlay_cache = {}


def load_overlay(name):
    if name not in _overlay_cache:
        with open(os.path.join(OVERLAY_DIR, name + ".png"), "rb") as f:
            _overlay_cache[name] = png.decode(f.read())
    return _overlay_cache[name]


def login_required(fn):
    @functools.wraps(fn)
    def wrapper(req, *args):
        if req.user is None:
            if req.path.startswith("/editor/create"):
                return json_response({"error": "Please log in first."}, "401 Unauthorized")
            body = views.message("Please log in", "You need an account to do this.",
                                 "/login", "Go to the login page")
            return req.page("Login required", body, "403 Forbidden")
        return fn(req, *args)
    return wrapper


def make_token(req, user_id, kind, ttl):
    token = security.new_token()
    req.conn.execute(
        "INSERT INTO tokens (user_id, kind, token_hash, expires_at) VALUES (?, ?, ?, ?)",
        (user_id, kind, security.sha(token), int(time.time()) + ttl))
    return token


def use_token(req, token, kind):
    """Return the user id for a valid token and mark it as used, else None."""
    row = req.conn.execute(
        "SELECT id, user_id FROM tokens WHERE token_hash = ? AND kind = ? "
        "AND used = 0 AND expires_at > ?",
        (security.sha(token), kind, int(time.time()))).fetchone()
    if not row:
        return None
    req.conn.execute("UPDATE tokens SET used = 1 WHERE id = ?", (row["id"],))
    return row["user_id"]


def peek_token(req, token, kind):
    return req.conn.execute(
        "SELECT 1 FROM tokens WHERE token_hash = ? AND kind = ? AND used = 0 AND expires_at > ?",
        (security.sha(token), kind, int(time.time()))).fetchone() is not None


# --- gallery ----------------------------------------------------------------
@route("GET", r"/")
def gallery(req):
    total = req.conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
    pages = max(1, -(-total // views.PER_PAGE))
    try:
        page = int(req.query.get("page", "1"))
    except ValueError:
        page = 1
    page = min(max(page, 1), pages)
    rows = req.conn.execute(
        "SELECT i.id, i.created_at, u.username, "
        "(SELECT COUNT(*) FROM likes l WHERE l.image_id = i.id) AS likes, "
        "(SELECT COUNT(*) FROM comments c WHERE c.image_id = i.id) AS comments "
        "FROM images i JOIN users u ON u.id = i.user_id "
        "ORDER BY i.created_at DESC, i.id DESC LIMIT ? OFFSET ?",
        (views.PER_PAGE, (page - 1) * views.PER_PAGE)).fetchall()
    return req.page("Gallery", views.gallery(rows, page, pages))


@route("GET", r"/img/(\d+)")
def image_file(req, image_id):
    row = req.conn.execute("SELECT file FROM images WHERE id = ?", (int(image_id),)).fetchone()
    if not row:
        raise HttpError("404 Not Found", "Photo not found.")
    try:
        with open(os.path.join(db.IMG_DIR, row["file"]), "rb") as f:
            data = f.read()
    except OSError:
        raise HttpError("404 Not Found", "Photo not found.")
    return Response(data, ctype="image/png", headers=[("Cache-Control", "no-cache")])


# --- accounts -----------------------------------------------------------------
@route("GET", r"/register")
def register_form(req):
    return req.page("Sign up", views.register_form(req.csrf, {}))


@route("POST", r"/register")
def register(req):
    f = req.form
    username = f.get("username", "").strip()
    email = f.get("email", "").strip()
    password = f.get("password", "")
    error = (security.check_username(username) or security.check_email(email)
             or security.check_password(password, username, email))
    if not error and password != f.get("confirm", ""):
        error = "The two passwords do not match."
    if not error and req.conn.execute(
            "SELECT 1 FROM users WHERE username = ? OR email = ?", (username, email)).fetchone():
        error = "That username or email is already taken."
    if error:
        req.flash(error, "err")
        return req.page("Sign up", views.register_form(
            req.csrf, {"username": username, "email": email}), "400 Bad Request")
    try:
        cur = req.conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (username, email, security.hash_password(password), int(time.time())))
    except sqlite3.IntegrityError:
        req.flash("That username or email is already taken.", "err")
        return req.page("Sign up", views.register_form(
            req.csrf, {"username": username, "email": email}), "400 Bad Request")
    token = make_token(req, cur.lastrowid, "verify", VERIFY_TTL)
    req.conn.commit()
    mailer.send(email, "Activate your Camagru account",
                "Hello %s,\n\nActivate your account:\n%s/verify?token=%s\n\n"
                "The link is valid for 24 hours.\n" % (username, mailer.base_url(), token))
    req.flash("Account created. Check your email for the activation link.")
    return redirect("/login")


@route("GET", r"/verify")
def verify(req):
    user_id = use_token(req, req.query.get("token", ""), "verify")
    if user_id is None:
        req.flash("This activation link is invalid or has expired.", "err")
    else:
        req.conn.execute("UPDATE users SET verified = 1 WHERE id = ?", (user_id,))
        req.flash("Your account is active. You can log in now.")
    return redirect("/login")


@route("GET", r"/login")
def login_form(req):
    return req.page("Log in", views.login_form(req.csrf))


@route("POST", r"/login")
def login(req):
    username = req.form.get("username", "").strip()
    password = req.form.get("password", "")
    now = int(time.time())
    user = req.conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    error = None
    if user is None:
        security.verify_password(password, security.DUMMY_HASH)
        error = "Wrong username or password."
    elif user["locked_until"] > now:
        error = "Too many failed attempts. Please try again in a few minutes."
    elif not security.verify_password(password, user["password_hash"]):
        fails = user["fail_count"] + 1
        locked = now + LOCK_SECONDS if fails >= MAX_FAILS else 0
        req.conn.execute("UPDATE users SET fail_count = ?, locked_until = ? WHERE id = ?",
                         (0 if locked else fails, locked, user["id"]))
        error = "Wrong username or password."
    elif not user["verified"]:
        error = "Please activate your account with the link we emailed you."
    if error:
        req.flash(error, "err")
        return req.page("Log in", views.login_form(req.csrf, username), "400 Bad Request")
    req.conn.execute("UPDATE users SET fail_count = 0, locked_until = 0 WHERE id = ?",
                     (user["id"],))
    req.login(user["id"])
    req.flash("Welcome back, %s!" % user["username"])
    return redirect("/")


@route("POST", r"/logout")
def logout(req):
    req.logout()
    req.flash("You have been logged out.")
    return redirect("/")


@route("GET", r"/forgot")
def forgot_form(req):
    return req.page("Reset password", views.forgot_form(req.csrf))


@route("POST", r"/forgot")
def forgot(req):
    email = req.form.get("email", "").strip()
    user = req.conn.execute(
        "SELECT * FROM users WHERE email = ? AND verified = 1", (email,)).fetchone()
    if user:
        token = make_token(req, user["id"], "reset", RESET_TTL)
        req.conn.commit()
        mailer.send(user["email"], "Reset your Camagru password",
                    "Choose a new password:\n%s/reset?token=%s\n\n"
                    "The link is valid for 1 hour. If this wasn't you, ignore this email.\n"
                    % (mailer.base_url(), token))
    req.flash("If that email is registered, a reset link is on its way.")
    return redirect("/login")


@route("GET", r"/reset")
def reset_form(req):
    token = req.query.get("token", "")
    if not peek_token(req, token, "reset"):
        req.flash("This reset link is invalid or has expired.", "err")
        return redirect("/forgot")
    return req.page("Choose a new password", views.reset_form(req.csrf, token))


@route("POST", r"/reset")
def reset(req):
    token = req.form.get("token", "")
    password = req.form.get("password", "")
    if not peek_token(req, token, "reset"):
        req.flash("This reset link is invalid or has expired.", "err")
        return redirect("/forgot")
    error = security.check_password(password)
    if not error and password != req.form.get("confirm", ""):
        error = "The two passwords do not match."
    if error:
        req.flash(error, "err")
        return req.page("Choose a new password", views.reset_form(req.csrf, token),
                        "400 Bad Request")
    user_id = use_token(req, token, "reset")
    req.conn.execute("UPDATE users SET password_hash = ?, fail_count = 0, locked_until = 0 "
                     "WHERE id = ?", (security.hash_password(password), user_id))
    req.conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    req.flash("Password changed. Please log in.")
    return redirect("/login")


@route("GET", r"/settings")
@login_required
def settings_form(req):
    return req.page("Settings", views.settings(req.csrf, req.user))


@route("POST", r"/settings")
@login_required
def settings_save(req):
    f = req.form
    username = f.get("username", "").strip()
    email = f.get("email", "").strip()
    notify = 1 if f.get("notify") == "1" else 0
    error = security.check_username(username) or security.check_email(email)
    if not error and req.conn.execute(
            "SELECT 1 FROM users WHERE (username = ? OR email = ?) AND id <> ?",
            (username, email, req.user["id"])).fetchone():
        error = "That username or email is already taken."
    if not error and email.lower() != req.user["email"].lower() and not security.verify_password(
            f.get("current", ""), req.user["password_hash"]):
        error = "Enter your current password to change your email."
    if error:
        req.flash(error, "err")
        return redirect("/settings")
    req.conn.execute("UPDATE users SET username = ?, email = ?, notify = ? WHERE id = ?",
                     (username, email, notify, req.user["id"]))
    req.flash("Settings saved.")
    return redirect("/settings")


@route("POST", r"/settings/password")
@login_required
def settings_password(req):
    f = req.form
    password = f.get("password", "")
    error = None
    if not security.verify_password(f.get("current", ""), req.user["password_hash"]):
        error = "Your current password is wrong."
    elif security.check_password(password, req.user["username"], req.user["email"]):
        error = security.check_password(password, req.user["username"], req.user["email"])
    elif password != f.get("confirm", ""):
        error = "The two passwords do not match."
    if error:
        req.flash(error, "err")
        return redirect("/settings")
    req.conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                     (security.hash_password(password), req.user["id"]))
    req.conn.execute("DELETE FROM sessions WHERE user_id = ? AND id <> ?",
                     (req.user["id"], req.session["id"]))
    req.flash("Password changed.")
    return redirect("/settings")


# --- editor ---------------------------------------------------------------------
@route("GET", r"/editor")
@login_required
def editor(req):
    mine = req.conn.execute(
        "SELECT id FROM images WHERE user_id = ? ORDER BY created_at DESC, id DESC",
        (req.user["id"],)).fetchall()
    return req.page("Editor", views.editor(req.csrf, list_overlays(), mine),
                    scripts=("/static/editor.js",))


@route("POST", r"/editor/create")
@login_required
def editor_create(req):
    name = req.form.get("overlay", "")
    data_url = req.form.get("image", "")
    if name not in list_overlays():
        return json_response({"error": "Please choose a decoration."}, "400 Bad Request")
    if not data_url.startswith(DATA_URL_PREFIX):
        return json_response({"error": "Invalid image."}, "400 Bad Request")
    try:
        raw = base64.b64decode(data_url[len(DATA_URL_PREFIX):], validate=True)
        if len(raw) > MAX_IMAGE_BYTES:
            raise ValueError("too big")
        base = png.decode(raw)
        result = png.composite(base, load_overlay(name))
    except (binascii.Error, ValueError):
        return json_response({"error": "That image could not be read."}, "400 Bad Request")
    filename = os.urandom(16).hex() + ".png"
    with open(os.path.join(db.IMG_DIR, filename), "wb") as f:
        f.write(png.encode(*result))
    cur = req.conn.execute(
        "INSERT INTO images (user_id, file, created_at) VALUES (?, ?, ?)",
        (req.user["id"], filename, int(time.time())))
    return json_response({"id": cur.lastrowid, "url": "/image/%d" % cur.lastrowid,
                          "img": "/img/%d" % cur.lastrowid})


# --- image page -----------------------------------------------------------------
def get_image(req, image_id):
    row = req.conn.execute(
        "SELECT i.*, u.username, (SELECT COUNT(*) FROM likes l WHERE l.image_id = i.id) AS likes "
        "FROM images i JOIN users u ON u.id = i.user_id WHERE i.id = ?",
        (int(image_id),)).fetchone()
    if not row:
        raise HttpError("404 Not Found", "Photo not found.")
    return row


@route("GET", r"/image/(\d+)")
def image_page(req, image_id):
    img = get_image(req, image_id)
    comments = req.conn.execute(
        "SELECT c.body, c.created_at, u.username FROM comments c "
        "JOIN users u ON u.id = c.user_id WHERE c.image_id = ? ORDER BY c.created_at, c.id",
        (img["id"],)).fetchall()
    liked = bool(req.user and req.conn.execute(
        "SELECT 1 FROM likes WHERE user_id = ? AND image_id = ?",
        (req.user["id"], img["id"])).fetchone())
    return req.page("Photo", views.image_page(req.csrf, req.user, img, comments, liked))


@route("POST", r"/image/(\d+)/like")
@login_required
def like(req, image_id):
    img = get_image(req, image_id)
    deleted = req.conn.execute("DELETE FROM likes WHERE user_id = ? AND image_id = ?",
                               (req.user["id"], img["id"])).rowcount
    if not deleted:
        req.conn.execute("INSERT OR IGNORE INTO likes (user_id, image_id) VALUES (?, ?)",
                         (req.user["id"], img["id"]))
    return redirect("/image/%d" % img["id"])


@route("POST", r"/image/(\d+)/comment")
@login_required
def comment(req, image_id):
    img = get_image(req, image_id)
    body = req.form.get("body", "").strip()
    if not body or len(body) > 500:
        req.flash("A comment must be 1-500 characters.", "err")
        return redirect("/image/%d" % img["id"])
    req.conn.execute(
        "INSERT INTO comments (image_id, user_id, body, created_at) VALUES (?, ?, ?, ?)",
        (img["id"], req.user["id"], body, int(time.time())))
    owner = req.conn.execute("SELECT * FROM users WHERE id = ?", (img["user_id"],)).fetchone()
    if owner["notify"] and owner["id"] != req.user["id"]:
        req.conn.commit()
        mailer.send(owner["email"], "New comment on your photo",
                    "%s commented on your photo:\n\n%s\n\n%s/image/%d\n"
                    % (req.user["username"], body, mailer.base_url(), img["id"]))
    req.flash("Comment posted.")
    return redirect("/image/%d" % img["id"])


@route("POST", r"/image/(\d+)/delete")
@login_required
def delete_image(req, image_id):
    img = get_image(req, image_id)
    if img["user_id"] != req.user["id"]:
        raise HttpError("403 Forbidden", "You can only delete your own photos.")
    req.conn.execute("DELETE FROM images WHERE id = ?", (img["id"],))
    try:
        os.remove(os.path.join(db.IMG_DIR, img["file"]))
    except OSError:
        pass
    req.flash("Photo deleted.")
    return redirect("/editor")
