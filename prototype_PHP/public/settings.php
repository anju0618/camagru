<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

$user = require_login();
if (is_post()) {
    check_csrf();
    $error = null;
    if (post('action') === 'password') {
        $new = post('password');
        if (!password_verify(post('current'), $user['password_hash'])) {
            $error = 'Your current password is wrong.';
        } elseif ($e1 = check_password($new, $user['username'], $user['email'])) {
            $error = $e1;
        } elseif ($new !== post('confirm')) {
            $error = 'The two passwords do not match.';
        } else {
            $hash = password_hash($new, PASSWORD_DEFAULT);
            q('UPDATE users SET password_hash = ? WHERE id = ?', [$hash, $user['id']]);
            $_SESSION['pwf'] = pw_fingerprint($hash); // keep this session, drop the others
            flash('Password changed.');
        }
    } else {
        $username = trim(post('username'));
        $email = trim(post('email'));
        $error = check_username($username) ?? check_email($email);
        if (!$error && q('SELECT 1 FROM users WHERE (username = ? OR email = ?) AND id <> ?',
                [$username, $email, $user['id']])->fetch()) {
            $error = 'That username or email is already taken.';
        }
        if (!$error && strcasecmp($email, $user['email']) !== 0
                && !password_verify(post('current'), $user['password_hash'])) {
            $error = 'Enter your current password to change your email.';
        }
        if (!$error) {
            q('UPDATE users SET username = ?, email = ?, notify = ? WHERE id = ?',
                [$username, $email, post('notify') === '1' ? 1 : 0, $user['id']]);
            flash('Settings saved.');
        }
    }
    if ($error) {
        flash($error, 'err');
    }
    redirect('/settings.php');
}
render_header('Settings');
?>
<section class="card narrow"><h1>Settings</h1>
<form method="post" action="/settings.php"><?= csrf_field() ?>
<label>Username<input name="username" required minlength="3" maxlength="20" pattern="[A-Za-z0-9_]+" value="<?= e($user['username']) ?>"></label>
<label>Email<input type="email" name="email" required maxlength="254" value="<?= e($user['email']) ?>"></label>
<label>Current password (only needed to change email)<input type="password" name="current" maxlength="128" autocomplete="current-password"></label>
<label class="check"><input type="checkbox" name="notify" value="1" <?= $user['notify'] ? 'checked' : '' ?>> Email me when someone comments on my photos</label>
<button type="submit">Save</button></form></section>
<section class="card narrow"><h2>Change password</h2>
<form method="post" action="/settings.php"><?= csrf_field() ?>
<input type="hidden" name="action" value="password">
<label>Current password<input type="password" name="current" required maxlength="128" autocomplete="current-password"></label>
<label>New password<input type="password" name="password" required minlength="8" maxlength="128" autocomplete="new-password"></label>
<label>Confirm new password<input type="password" name="confirm" required autocomplete="new-password"></label>
<button type="submit">Change password</button></form></section>
<?php render_footer();
