<?php
declare(strict_types=1);

define('DATA_DIR', getenv('DATA_DIR') ?: '/var/www/data');
define('IMG_DIR', DATA_DIR . '/images');
define('OVERLAY_DIR', __DIR__ . '/../public/overlays');
const PER_PAGE = 6;
const DUMMY_HASH = '$2y$10$wlemZnjO8U4qXo0g41RQJOIFygoP.RlAhu6Nnj9ZuT9AY/WISV5AC';

set_exception_handler(function (Throwable $e): void {
    error_log((string) $e);
    http_response_code(500);
    echo 'Something went wrong on our side.';
});

header("Content-Security-Policy: default-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
    . "style-src 'self'; script-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'");
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('Referrer-Policy: same-origin');

session_name('sid');
session_set_cookie_params([
    'httponly' => true,
    'samesite' => 'Lax',
    'secure' => str_starts_with((string) getenv('BASE_URL'), 'https://'),
]);
session_start();
if (empty($_SESSION['csrf'])) {
    $_SESSION['csrf'] = bin2hex(random_bytes(32));
}

require __DIR__ . '/mail.php';
require __DIR__ . '/image.php';
require __DIR__ . '/layout.php';

const SCHEMA = '
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0,
    notify INTEGER NOT NULL DEFAULT 1,
    fail_count INTEGER NOT NULL DEFAULT 0,
    locked_until INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at INTEGER NOT NULL,
    used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS likes (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_id INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, image_id)
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY,
    image_id INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
';

function db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        if (!is_dir(IMG_DIR)) {
            mkdir(IMG_DIR, 0775, true);
        }
        $pdo = new PDO('sqlite:' . DATA_DIR . '/camagru.db', null, null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        $pdo->exec('PRAGMA foreign_keys = ON');
        $pdo->exec('PRAGMA busy_timeout = 5000');
        $pdo->exec(SCHEMA);
    }
    return $pdo;
}

/** Run a prepared statement. Every query in this app goes through here. */
function q(string $sql, array $params = []): PDOStatement
{
    $st = db()->prepare($sql);
    $st->execute($params);
    return $st;
}

function e(mixed $value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function redirect(string $to): never
{
    header('Location: ' . $to, true, 303);
    exit;
}

function fail(int $code, string $message): never
{
    http_response_code($code);
    render_header((string) $code);
    echo '<section class="card narrow"><h1>' . e($code) . '</h1><p>' . e($message)
        . '</p><p><a href="/">Back to the gallery</a></p></section>';
    render_footer();
    exit;
}

function flash(string $text, string $kind = 'ok'): void
{
    $_SESSION['flash'] = [$kind, $text];
}

function csrf_field(): string
{
    return '<input type="hidden" name="csrf" value="' . e($_SESSION['csrf']) . '">';
}

/** Call at the top of every POST handler. */
function check_csrf(): void
{
    $sent = $_POST['csrf'] ?? '';
    if (!is_string($sent) || !hash_equals($_SESSION['csrf'], $sent)) {
        fail(403, 'Invalid or missing form token. Please go back, reload the page and try again.');
    }
}

function is_post(): bool
{
    return $_SERVER['REQUEST_METHOD'] === 'POST';
}

function post(string $key): string
{
    $v = $_POST[$key] ?? '';
    return is_string($v) ? $v : '';
}

function current_user(): ?array
{
    static $user = false;
    if ($user === false) {
        $user = null;
        if (!empty($_SESSION['uid'])) {
            $row = q('SELECT * FROM users WHERE id = ?', [$_SESSION['uid']])->fetch();
            // A password change anywhere else logs this session out.
            if ($row && hash_equals(pw_fingerprint($row['password_hash']), $_SESSION['pwf'] ?? '')) {
                $user = $row;
            } else {
                unset($_SESSION['uid'], $_SESSION['pwf']);
            }
        }
    }
    return $user;
}

function pw_fingerprint(string $hash): string
{
    return substr(hash('sha256', $hash), 0, 16);
}

function login_user(array $user): void
{
    session_regenerate_id(true); // prevents session fixation
    $_SESSION['uid'] = $user['id'];
    $_SESSION['pwf'] = pw_fingerprint($user['password_hash']);
    $_SESSION['csrf'] = bin2hex(random_bytes(32));
}

function require_login(): array
{
    $user = current_user();
    if (!$user) {
        http_response_code(403);
        render_header('Login required');
        echo '<section class="card narrow"><h1>Please log in</h1><p>You need an account to do this.</p>'
            . '<p><a href="/login.php">Go to the login page</a></p></section>';
        render_footer();
        exit;
    }
    return $user;
}

function check_username(string $name): ?string
{
    return preg_match('/^[A-Za-z0-9_]{3,20}$/D', $name) ? null
        : 'Username must be 3-20 characters: letters, digits or underscore.';
}

function check_email(string $email): ?string
{
    return (strlen($email) <= 254 && filter_var($email, FILTER_VALIDATE_EMAIL)) ? null
        : 'Please enter a valid email address.';
}

function check_password(string $pw, string $username = '', string $email = ''): ?string
{
    if (strlen($pw) < 8 || strlen($pw) > 128) {
        return 'Password must be 8-128 characters.';
    }
    if (!preg_match('/[a-z]/', $pw) || !preg_match('/[A-Z]/', $pw) || !preg_match('/[0-9]/', $pw)) {
        return 'Password needs a lowercase letter, an uppercase letter and a digit.';
    }
    if (strcasecmp($pw, $username) === 0 || strcasecmp($pw, $email) === 0) {
        return 'Password must not be the same as your username or email.';
    }
    return null;
}

/** Create a single-use token; only its hash is stored. Returns the raw token. */
function make_token(int $userId, string $kind, int $ttl): string
{
    $token = bin2hex(random_bytes(32));
    q('INSERT INTO tokens (user_id, kind, token_hash, expires_at) VALUES (?, ?, ?, ?)',
        [$userId, $kind, hash('sha256', $token), time() + $ttl]);
    return $token;
}

function peek_token(string $token, string $kind): ?array
{
    $row = q('SELECT * FROM tokens WHERE token_hash = ? AND kind = ? AND used = 0 AND expires_at > ?',
        [hash('sha256', $token), $kind, time()])->fetch();
    return $row ?: null;
}

/** Returns the user id and marks the token used, or null if invalid. */
function use_token(string $token, string $kind): ?int
{
    $row = peek_token($token, $kind);
    if (!$row) {
        return null;
    }
    q('UPDATE tokens SET used = 1 WHERE id = ?', [$row['id']]);
    return (int) $row['user_id'];
}
