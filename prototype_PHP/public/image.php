<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

$id = (int) ($_GET['id'] ?? 0);
$img = q('SELECT i.*, u.username,
            (SELECT COUNT(*) FROM likes l WHERE l.image_id = i.id) AS likes
          FROM images i JOIN users u ON u.id = i.user_id WHERE i.id = ?', [$id])->fetch();
if (!$img) {
    fail(404, 'Photo not found.');
}
$self = '/image.php?id=' . $id;

if (is_post()) {
    check_csrf();
    $user = require_login();
    switch (post('action')) {
        case 'like':
            if (q('DELETE FROM likes WHERE user_id = ? AND image_id = ?', [$user['id'], $id])->rowCount() === 0) {
                q('INSERT OR IGNORE INTO likes (user_id, image_id) VALUES (?, ?)', [$user['id'], $id]);
            }
            redirect($self);
        case 'comment':
            $body = trim(post('body'));
            if ($body === '' || mb_strlen($body) > 500) {
                flash('A comment must be 1-500 characters.', 'err');
                redirect($self);
            }
            q('INSERT INTO comments (image_id, user_id, body, created_at) VALUES (?, ?, ?, ?)',
                [$id, $user['id'], $body, time()]);
            $owner = q('SELECT * FROM users WHERE id = ?', [$img['user_id']])->fetch();
            if ($owner['notify'] && (int) $owner['id'] !== (int) $user['id']) {
                send_mail($owner['email'], 'New comment on your photo',
                    $user['username'] . " commented on your photo:\n\n$body\n\n" . base_url() . "$self\n");
            }
            flash('Comment posted.');
            redirect($self);
        case 'delete':
            if ((int) $img['user_id'] !== (int) $user['id']) {
                fail(403, 'You can only delete your own photos.');
            }
            q('DELETE FROM images WHERE id = ?', [$id]);
            @unlink(IMG_DIR . '/' . basename($img['file']));
            flash('Photo deleted.');
            redirect('/editor.php');
        default:
            fail(400, 'Unknown action.');
    }
}

$user = current_user();
$comments = q('SELECT c.body, c.created_at, u.username FROM comments c
               JOIN users u ON u.id = c.user_id WHERE c.image_id = ? ORDER BY c.created_at, c.id', [$id])->fetchAll();
$liked = $user && q('SELECT 1 FROM likes WHERE user_id = ? AND image_id = ?', [$user['id'], $id])->fetch();
render_header('Photo');
?>
<section class="card"><h1>Photo by <?= e($img['username']) ?></h1>
<img class="full" src="/img.php?id=<?= $id ?>" alt="Photo by <?= e($img['username']) ?>">
<p class="muted"><?= e(gmdate('Y-m-d H:i', (int) $img['created_at'])) ?> UTC &middot; <?= (int) $img['likes'] ?> likes</p>
<div class="actions">
<?php if ($user): ?>
<form method="post" action="<?= e($self) ?>" class="inline"><?= csrf_field() ?><input type="hidden" name="action" value="like">
<button type="submit" class="secondary"><?= $liked ? 'Unlike' : 'Like' ?></button></form>
<?php if ((int) $user['id'] === (int) $img['user_id']): ?>
<form method="post" action="<?= e($self) ?>" class="inline"><?= csrf_field() ?><input type="hidden" name="action" value="delete">
<button type="submit" class="danger">Delete</button></form>
<?php endif; ?>
<?php else: ?>
<p class="muted"><a href="/login.php">Log in</a> to like or comment.</p>
<?php endif; ?>
</div></section>
<section class="card"><h2>Comments</h2>
<ul class="comments">
<?php foreach ($comments as $c): ?>
<li><strong><?= e($c['username']) ?></strong> <span class="muted"><?= e(gmdate('Y-m-d H:i', (int) $c['created_at'])) ?> UTC</span><p><?= e($c['body']) ?></p></li>
<?php endforeach; ?>
<?php if (!$comments): ?><li class="muted">No comments yet.</li><?php endif; ?>
</ul>
<?php if ($user): ?>
<form method="post" action="<?= e($self) ?>"><?= csrf_field() ?><input type="hidden" name="action" value="comment">
<label>Add a comment<textarea name="body" required maxlength="500" rows="3"></textarea></label>
<button type="submit">Post comment</button></form>
<?php endif; ?>
</section>
<?php render_footer();
