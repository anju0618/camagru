<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

$token = is_post() ? post('token') : (is_string($_GET['token'] ?? null) ? $_GET['token'] : '');
if (!peek_token($token, 'reset')) {
    flash('This reset link is invalid or has expired.', 'err');
    redirect('/forgot.php');
}
if (is_post()) {
    check_csrf();
    $password = post('password');
    $error = check_password($password);
    if (!$error && $password !== post('confirm')) {
        $error = 'The two passwords do not match.';
    }
    if (!$error) {
        $userId = use_token($token, 'reset');
        q('UPDATE users SET password_hash = ?, fail_count = 0, locked_until = 0 WHERE id = ?',
            [password_hash($password, PASSWORD_DEFAULT), $userId]);
        flash('Password changed. Please log in.');
        redirect('/login.php');
    }
    http_response_code(400);
    flash($error, 'err');
}
render_header('Choose a new password');
?>
<section class="card narrow"><h1>Choose a new password</h1>
<form method="post" action="/reset.php"><?= csrf_field() ?>
<input type="hidden" name="token" value="<?= e($token) ?>">
<label>New password<input type="password" name="password" required minlength="8" maxlength="128" autocomplete="new-password"></label>
<label>Confirm password<input type="password" name="confirm" required autocomplete="new-password"></label>
<button type="submit">Change password</button></form></section>
<?php render_footer();
