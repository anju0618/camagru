import hashlib
import hmac
import re
import secrets

USERNAME_RE = re.compile(r"[A-Za-z0-9_]{3,20}")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return "scrypt$%s$%s" % (salt.hex(), digest.hex())


def verify_password(password, stored):
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex),
                                n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(digest, bytes.fromhex(digest_hex))
    except ValueError:
        return False


DUMMY_HASH = hash_password("dummy-password")


def new_token():
    return secrets.token_urlsafe(32)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def check_username(name):
    if not USERNAME_RE.fullmatch(name):
        return "Username must be 3-20 characters: letters, digits or underscore."
    return None


def check_email(email):
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        return "Please enter a valid email address."
    return None


def check_password(password, username="", email=""):
    if len(password) < 8 or len(password) > 128:
        return "Password must be 8-128 characters."
    if not (re.search(r"[a-z]", password) and re.search(r"[A-Z]", password)
            and re.search(r"[0-9]", password)):
        return "Password needs a lowercase letter, an uppercase letter and a digit."
    if password.lower() in (username.lower(), email.lower()):
        return "Password must not be the same as your username or email."
    return None
