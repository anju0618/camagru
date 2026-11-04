<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

$username = '';
if (is_post()) {
    check_csrf();
    $username = trim(post('username'));
    $password = post('password');
    $user = db_query('SELECT * FROM users WHERE username = ?', [$username])->fetch();
    $error = null;
    if (!$user) {
        password_verify($password, DUMMY_HASH); // same timing whether or not the user exists
        $error = 'Wrong username or password.';
    } elseif ($user['locked_until'] > time()) {
        $error = 'Too many failed attempts. Please try again in a few minutes.';
    } elseif (!password_verify($password, $user['password_hash'])) {
        $fails = $user['fail_count'] + 1;
        $locked = $fails >= 5 ? time() + 300 : 0;
        db_query('UPDATE users SET fail_count = ?, locked_until = ? WHERE id = ?', [$locked ? 0 : $fails, $locked, $user['id']]);
        $error = 'Wrong username or password.';
    } elseif (!$user['verified']) {
        $error = 'Please activate your account with the link we emailed you.';
    }
    if (!$error) {
        db_query('UPDATE users SET fail_count = 0, locked_until = 0 WHERE id = ?', [$user['id']]);
        login_user($user);
        flash('Welcome back, ' . $user['username'] . '!');
        redirect('/');
    }
    http_response_code(400);
    flash($error, 'err');
}
render_header('Log in');
?>
<section class="card narrow"><h1>Log in</h1>
<form method="post" action="/login.php"><?= csrf_field() ?>
<label>Username<input name="username" required maxlength="20" value="<?= e($username) ?>" autocomplete="username"></label>
<label>Password<input type="password" name="password" required maxlength="128" autocomplete="current-password"></label>
<button type="submit">Log in</button></form>
<p><a href="/forgot.php">Forgot your password?</a></p></section>
<?php render_footer();
