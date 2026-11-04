<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

if (!is_post()) {
    fail(405, 'Method not allowed.');
}
check_csrf();
$_SESSION = [];
session_regenerate_id(true);
$_SESSION['csrf'] = bin2hex(random_bytes(32));
flash('You have been logged out.');
redirect('/');
