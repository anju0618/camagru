import html
import time

PER_PAGE = 6


def esc(value):
    return html.escape(str(value), quote=True)


def fmt_time(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ts)) + " UTC"


def csrf_field(csrf):
    return '<input type="hidden" name="csrf" value="%s">' % esc(csrf)


def layout(title, body, user, csrf, flash=None, scripts=()):
    if user:
        nav = (
            '<a href="/editor">Editor</a>'
            '<a href="/settings">%s</a>'
            '<form method="post" action="/logout" class="inline">%s'
            '<button type="submit" class="link">Log out</button></form>'
        ) % (esc(user["username"]), csrf_field(csrf))
    else:
        nav = '<a href="/login">Log in</a><a href="/register">Sign up</a>'
    flash_html = ""
    if flash:
        kind, text = flash
        flash_html = '<p class="flash %s" role="status">%s</p>' % (
            "error" if kind == "err" else "ok", esc(text))
    script_tags = "".join('<script src="%s"></script>' % esc(s) for s in scripts)
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>%s - Camagru</title><link rel="icon" href="data:,">'
        '<link rel="stylesheet" href="/static/style.css"></head><body>'
        '<header><a class="brand" href="/">Camagru</a>'
        '<nav><a href="/">Gallery</a>%s</nav></header>'
        '<main>%s%s</main>'
        '<footer>Camagru &middot; 42 Tokyo project</footer>%s</body></html>'
    ) % (esc(title), nav, flash_html, body, script_tags)


def message(title, text, link=None, link_text=""):
    extra = '<p><a href="%s">%s</a></p>' % (esc(link), esc(link_text)) if link else ""
    return '<section class="card narrow"><h1>%s</h1><p>%s</p>%s</section>' % (
        esc(title), esc(text), extra)


def gallery(rows, page, pages):
    if rows:
        cards = "".join(
            '<article class="tile"><a href="/image/%d"><img src="/img/%d" alt="Photo by %s" '
            'loading="lazy"></a><p><strong>%s</strong> &middot; %d likes &middot; %d comments</p>'
            '<p class="muted">%s</p></article>'
            % (r["id"], r["id"], esc(r["username"]), esc(r["username"]),
               r["likes"], r["comments"], fmt_time(r["created_at"]))
            for r in rows)
        grid = '<div class="grid">%s</div>' % cards
    else:
        grid = '<p class="muted">No photos yet. Be the first!</p>'
    pager = ""
    if pages > 1:
        prev_link = '<a href="/?page=%d">&laquo; Newer</a>' % (page - 1) if page > 1 else ""
        next_link = '<a href="/?page=%d">Older &raquo;</a>' % (page + 1) if page < pages else ""
        pager = '<nav class="pager">%s<span>Page %d / %d</span>%s</nav>' % (
            prev_link, page, pages, next_link)
    return "<h1>Gallery</h1>%s%s" % (grid, pager)


def register_form(csrf, values):
    return (
        '<section class="card narrow"><h1>Sign up</h1>'
        '<form method="post" action="/register">%s'
        '<label>Username<input name="username" required minlength="3" maxlength="20" '
        'pattern="[A-Za-z0-9_]+" value="%s" autocomplete="username"></label>'
        '<label>Email<input type="email" name="email" required maxlength="254" value="%s" '
        'autocomplete="email"></label>'
        '<label>Password<input type="password" name="password" required minlength="8" '
        'maxlength="128" autocomplete="new-password"></label>'
        '<label>Confirm password<input type="password" name="confirm" required '
        'autocomplete="new-password"></label>'
        '<p class="muted">8+ characters with upper case, lower case and a digit.</p>'
        '<button type="submit">Create account</button></form></section>'
    ) % (csrf_field(csrf), esc(values.get("username", "")), esc(values.get("email", "")))


def login_form(csrf, username=""):
    return (
        '<section class="card narrow"><h1>Log in</h1>'
        '<form method="post" action="/login">%s'
        '<label>Username<input name="username" required maxlength="20" value="%s" '
        'autocomplete="username"></label>'
        '<label>Password<input type="password" name="password" required maxlength="128" '
        'autocomplete="current-password"></label>'
        '<button type="submit">Log in</button></form>'
        '<p><a href="/forgot">Forgot your password?</a></p></section>'
    ) % (csrf_field(csrf), esc(username))


def forgot_form(csrf):
    return (
        '<section class="card narrow"><h1>Reset password</h1>'
        '<form method="post" action="/forgot">%s'
        '<label>Email<input type="email" name="email" required maxlength="254" '
        'autocomplete="email"></label>'
        '<button type="submit">Send reset link</button></form></section>'
    ) % csrf_field(csrf)


def reset_form(csrf, token):
    return (
        '<section class="card narrow"><h1>Choose a new password</h1>'
        '<form method="post" action="/reset">%s'
        '<input type="hidden" name="token" value="%s">'
        '<label>New password<input type="password" name="password" required minlength="8" '
        'maxlength="128" autocomplete="new-password"></label>'
        '<label>Confirm password<input type="password" name="confirm" required '
        'autocomplete="new-password"></label>'
        '<button type="submit">Change password</button></form></section>'
    ) % (csrf_field(csrf), esc(token))


def settings(csrf, user):
    return (
        '<section class="card narrow"><h1>Settings</h1>'
        '<form method="post" action="/settings">%s'
        '<label>Username<input name="username" required minlength="3" maxlength="20" '
        'pattern="[A-Za-z0-9_]+" value="%s"></label>'
        '<label>Email<input type="email" name="email" required maxlength="254" value="%s"></label>'
        '<label>Current password (only needed to change email)'
        '<input type="password" name="current" maxlength="128" autocomplete="current-password"></label>'
        '<label class="check"><input type="checkbox" name="notify" value="1" %s> '
        'Email me when someone comments on my photos</label>'
        '<button type="submit">Save</button></form></section>'
        '<section class="card narrow"><h2>Change password</h2>'
        '<form method="post" action="/settings/password">%s'
        '<label>Current password<input type="password" name="current" required maxlength="128" '
        'autocomplete="current-password"></label>'
        '<label>New password<input type="password" name="password" required minlength="8" '
        'maxlength="128" autocomplete="new-password"></label>'
        '<label>Confirm new password<input type="password" name="confirm" required '
        'autocomplete="new-password"></label>'
        '<button type="submit">Change password</button></form></section>'
    ) % (csrf_field(csrf), esc(user["username"]), esc(user["email"]),
         "checked" if user["notify"] else "", csrf_field(csrf))


def editor(csrf, overlays, mine):
    buttons = "".join(
        '<button type="button" class="overlay" data-name="%s"><img src="/static/overlays/%s.png" '
        'alt="%s"></button>' % (esc(n), esc(n), esc(n)) for n in overlays)
    thumbs = "".join(thumb(csrf, r["id"]) for r in mine)
    return (
        '<h1>Editor</h1><div class="editor"><section class="card main-col">'
        '<div class="stage"><video id="video" autoplay playsinline muted></video>'
        '<img id="still" class="hidden" alt="Selected photo">'
        '<img id="overlay-preview" class="hidden" alt=""></div>'
        '<p id="status" class="muted" role="status">Choose a decoration, then take a photo.</p>'
        '<div class="overlays">%s</div>'
        '<div class="actions"><button type="button" id="capture" disabled>Take photo</button>'
        '<label class="button secondary">Upload image'
        '<input type="file" id="upload" accept="image/*" class="visually-hidden"></label>'
        '<button type="button" id="use-camera" class="secondary hidden">Use camera</button></div>'
        '<input type="hidden" id="csrf" value="%s"></section>'
        '<aside class="card side-col"><h2>Your photos</h2><ul id="thumbs" class="thumbs">%s</ul>'
        '</aside></div>'
    ) % (buttons, esc(csrf), thumbs)


def thumb(csrf, image_id):
    return (
        '<li><a href="/image/%d"><img src="/img/%d" alt="Your photo"></a>'
        '<form method="post" action="/image/%d/delete">%s'
        '<button type="submit" class="danger small">Delete</button></form></li>'
    ) % (image_id, image_id, image_id, csrf_field(csrf))


def image_page(csrf, user, img, comments, liked):
    actions = ""
    if user:
        actions = (
            '<form method="post" action="/image/%d/like" class="inline">%s'
            '<button type="submit" class="secondary">%s</button></form>'
        ) % (img["id"], csrf_field(csrf), "Unlike" if liked else "Like")
        if user["id"] == img["user_id"]:
            actions += (
                '<form method="post" action="/image/%d/delete" class="inline">%s'
                '<button type="submit" class="danger">Delete</button></form>'
            ) % (img["id"], csrf_field(csrf))
    else:
        actions = '<p class="muted"><a href="/login">Log in</a> to like or comment.</p>'
    comment_form = ""
    if user:
        comment_form = (
            '<form method="post" action="/image/%d/comment">%s'
            '<label>Add a comment<textarea name="body" required maxlength="500" rows="3">'
            '</textarea></label><button type="submit">Post comment</button></form>'
        ) % (img["id"], csrf_field(csrf))
    items = "".join(
        '<li><strong>%s</strong> <span class="muted">%s</span><p>%s</p></li>'
        % (esc(c["username"]), fmt_time(c["created_at"]), esc(c["body"]))
        for c in comments) or '<li class="muted">No comments yet.</li>'
    return (
        '<section class="card"><h1>Photo by %s</h1>'
        '<img class="full" src="/img/%d" alt="Photo by %s">'
        '<p class="muted">%s &middot; %d likes</p><div class="actions">%s</div></section>'
        '<section class="card"><h2>Comments</h2><ul class="comments">%s</ul>%s</section>'
    ) % (esc(img["username"]), img["id"], esc(img["username"]),
         fmt_time(img["created_at"]), img["likes"], actions, items, comment_form)
