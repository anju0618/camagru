<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

$username = $email = '';
if (is_post()) {
    check_csrf();
    $username = trim(post('username'));
    $email = trim(post('email'));
    $password = post('password');
    $error = check_username($username) ?? check_email($email) ?? check_password($password, $username, $email);
    if (!$error && $password !== post('confirm')) {
        $error = 'The two passwords do not match.';
    }
    if (!$error && db_query('SELECT 1 FROM users WHERE username = ? OR email = ?', [$username, $email])->fetch()) {
        $error = 'That username or email is already taken.';
    }
    if (!$error) {
        try {
            db_query('INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
                [$username, $email, password_hash($password, PASSWORD_DEFAULT), time()]);
            $id = (int) db()->lastInsertId();
            $token = make_token($id, 'verify', 86400);
            send_mail($email, 'Activate your Camagru account',
                "Hello $username,\n\nActivate your account:\n" . base_url() . "/verify.php?token=$token\n\n"
                . "The link is valid for 24 hours.\n");
            flash('Account created. Check your email for the activation link.');
            redirect('/login.php');
        } catch (PDOException $ex) {
            $error = 'That username or email is already taken.';
        }
    }
    http_response_code(400);
    flash($error, 'err');
}
render_header('Sign up');
?>
<section class="card narrow"><h1>Sign up</h1>
<form method="post" action="/register.php"><?= csrf_field() ?>
<label>Username<input name="username" required minlength="3" maxlength="20" pattern="[A-Za-z0-9_]+" value="<?= e($username) ?>" autocomplete="username"></label>
<label>Email<input type="email" name="email" required maxlength="254" value="<?= e($email) ?>" autocomplete="email"></label>
<label>Password<input type="password" name="password" required minlength="8" maxlength="128" autocomplete="new-password"></label>
<label>Confirm password<input type="password" name="confirm" required autocomplete="new-password"></label>
<p class="muted">8+ characters with upper case, lower case and a digit.</p>
<button type="submit">Create account</button></form></section>
<?php render_footer();
