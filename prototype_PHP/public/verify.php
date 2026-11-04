<?php
declare(strict_types=1); # 型変換禁止
require __DIR__ . '/../src/bootstrap.php';

$token = is_string($_GET['token'] ?? null) ? $_GET['token'] : '';
$userId = use_token($token, 'verify');
if ($userId === null) {
    flash('This activation link is invalid or has expired.', 'err');
} else {
    q('UPDATE users SET verified = 1 WHERE id = ?', [$userId]);
    flash('Your account is active. You can log in now.');
}
redirect('/login.php');
