<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

header('Content-Type: application/json');
header('Cache-Control: no-store');

function json_out(array $data, int $status = 200): never
{
    http_response_code($status);
    echo json_encode($data);
    exit;
}

if (!is_post()) {
    json_out(['error' => 'Method not allowed.'], 405);
}
$user = current_user();
if (!$user) {
    json_out(['error' => 'Please log in first.'], 401);
}
$sent = $_POST['csrf'] ?? '';
if (!is_string($sent) || !hash_equals($_SESSION['csrf'], $sent)) {
    json_out(['error' => 'Invalid form token. Please reload the page.'], 403);
}

try {
    if (isset($_FILES['upload'])) {                       // uploaded file (PNG / JPEG)
        $f = $_FILES['upload'];
        if (!is_array($f) || ($f['error'] ?? 1) !== UPLOAD_ERR_OK || !is_uploaded_file($f['tmp_name'])) {
            throw new RuntimeException('The upload failed (max 5 MB).');
        }
        $raw = (string) file_get_contents($f['tmp_name']);
    } else {                                              // webcam frame sent as a PNG data URL
        $prefix = 'data:image/png;base64,';
        $data = post('image');
        if (!str_starts_with($data, $prefix)) {
            throw new RuntimeException('Invalid image.');
        }
        $raw = base64_decode(substr($data, strlen($prefix)), true);
        if ($raw === false) {
            throw new RuntimeException('Invalid image.');
        }
    }
    $file = make_photo($raw, post('overlay'));
} catch (RuntimeException $ex) {
    json_out(['error' => $ex->getMessage()], 400);
}
q('INSERT INTO images (user_id, file, created_at) VALUES (?, ?, ?)', [$user['id'], $file, time()]);
$id = (int) db()->lastInsertId();
json_out(['id' => $id, 'url' => '/image.php?id=' . $id, 'img' => '/img.php?id=' . $id]);
