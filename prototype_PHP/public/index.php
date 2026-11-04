<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

$total = (int) db_query('SELECT COUNT(*) FROM images')->fetchColumn();
$pages = max(1, (int) ceil($total / PER_PAGE));
$page = min(max((int) ($_GET['page'] ?? 1), 1), $pages);
$rows = db_query('SELECT i.id, i.created_at, u.username,
             (SELECT COUNT(*) FROM likes l WHERE l.image_id = i.id) AS likes,
             (SELECT COUNT(*) FROM comments c WHERE c.image_id = i.id) AS comments
           FROM images i JOIN users u ON u.id = i.user_id
           ORDER BY i.created_at DESC, i.id DESC LIMIT ? OFFSET ?',
    [PER_PAGE, ($page - 1) * PER_PAGE])->fetchAll();

render_header('Gallery');
echo '<h1>Gallery</h1>';
if (!$rows) {
    echo '<p class="muted">No photos yet. Be the first!</p>';
}
echo '<div class="grid">';
foreach ($rows as $r) {
    echo '<article class="tile"><a href="/image.php?id=' . (int) $r['id'] . '"><img src="/img.php?id=' . (int) $r['id']
        . '" alt="Photo by ' . e($r['username']) . '" loading="lazy"></a><p><strong>' . e($r['username'])
        . '</strong> &middot; ' . (int) $r['likes'] . ' likes &middot; ' . (int) $r['comments'] . ' comments</p>'
        . '<p class="muted">' . e(gmdate('Y-m-d H:i', (int) $r['created_at'])) . ' UTC</p></article>';
}
echo '</div>';
if ($pages > 1) {
    echo '<nav class="pager">';
    if ($page > 1) echo '<a href="/?page=' . ($page - 1) . '">&laquo; Newer</a>';
    echo '<span>Page ' . $page . ' / ' . $pages . '</span>';
    if ($page < $pages) echo '<a href="/?page=' . ($page + 1) . '">Older &raquo;</a>';
    echo '</nav>';
}
render_footer();
