<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

if (is_post()) {
    check_csrf();
    $user = q('SELECT * FROM users WHERE email = ? AND verified = 1', [trim(post('email'))])->fetch();
    if ($user) {
        $token = make_token((int) $user['id'], 'reset', 3600);
        send_mail($user['email'], 'Reset your Camagru password',
            "Choose a new password:\n" . base_url() . "/reset.php?token=$token\n\n"
            . "The link is valid for 1 hour. If this wasn't you, ignore this email.\n");
    }
    // Same answer whether or not the address is registered.
    flash('If that email is registered, a reset link is on its way.');
    redirect('/login.php');
}
render_header('Reset password');
?>
<section class="card narrow"><h1>Reset password</h1>
<form method="post" action="/forgot.php"><?= csrf_field() ?>
<label>Email<input type="email" name="email" required maxlength="254" autocomplete="email"></label>
<button type="submit">Send reset link</button></form></section>
<?php render_footer();
