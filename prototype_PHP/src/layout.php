<?php
declare(strict_types=1);

function render_header(string $title): void
{
    $user = current_user();
    echo '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        . '<meta name="viewport" content="width=device-width, initial-scale=1">'
        . '<title>' . e($title) . ' - Camagru</title><link rel="icon" href="data:,">'
        . '<link rel="stylesheet" href="/style.css"></head><body>'
        . '<header><a class="brand" href="/">Camagru</a><nav><a href="/">Gallery</a>';
    if ($user) {
        echo '<a href="/editor.php">Editor</a><a href="/settings.php">' . e($user['username']) . '</a>'
            . '<form method="post" action="/logout.php" class="inline">' . csrf_field()
            . '<button type="submit" class="link">Log out</button></form>';
    } else {
        echo '<a href="/login.php">Log in</a><a href="/register.php">Sign up</a>';
    }
    echo '</nav></header><main>';
    if (!empty($_SESSION['flash'])) {
        [$kind, $text] = $_SESSION['flash'];
        unset($_SESSION['flash']);
        echo '<p class="flash ' . ($kind === 'err' ? 'error' : 'ok') . '" role="status">' . e($text) . '</p>';
    }
}

function render_footer(array $scripts = []): void
{
    echo '</main><footer>Camagru &middot; 42 Tokyo project</footer>';
    foreach ($scripts as $s) {
        echo '<script src="' . e($s) . '"></script>';
    }
    echo '</body></html>';
}

function thumb_html(int $id): string
{
    return '<li><a href="/image.php?id=' . $id . '"><img src="/img.php?id=' . $id . '" alt="Your photo"></a>'
        . '<form method="post" action="/image.php?id=' . $id . '">' . csrf_field()
        . '<input type="hidden" name="action" value="delete">'
        . '<button type="submit" class="danger small">Delete</button></form></li>';
}
