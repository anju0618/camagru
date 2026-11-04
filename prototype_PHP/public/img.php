<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

$row = db_query('SELECT file FROM images WHERE id = ?', [(int) ($_GET['id'] ?? 0)])->fetch();
$path = $row ? IMG_DIR . '/' . basename($row['file']) : '';
if (!$row || !is_file($path)) {
    http_response_code(404);
    exit;
}
header('Content-Type: image/png');
header('Content-Length: ' . filesize($path));
header('Cache-Control: no-cache');
readfile($path);
