<?php
declare(strict_types=1);

const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;
const MAX_OUTPUT_WIDTH = 800;

function list_overlays(): array
{
    $names = [];
    foreach (glob(OVERLAY_DIR . '/*.png') ?: [] as $path) {
        $name = basename($path, '.png');
        if (preg_match('/^[a-z0-9_-]+$/', $name)) {
            $names[] = $name;
        }
    }
    sort($names);
    return $names;
}

/**
 * Validate raw image bytes (PNG or JPEG), draw the overlay on top, save as a new PNG.
 * Re-encoding with GD also strips anything extra hidden in the upload.
 * Returns the stored file name. Throws RuntimeException with a user-facing message.
 */
function make_photo(string $raw, string $overlay): string
{
    if (!in_array($overlay, list_overlays(), true)) {
        throw new RuntimeException('Please choose a decoration.');
    }
    if ($raw === '' || strlen($raw) > MAX_UPLOAD_BYTES) {
        throw new RuntimeException('The image is empty or too large (max 5 MB).');
    }
    $info = @getimagesizefromstring($raw);
    if (!$info || !in_array($info[2], [IMAGETYPE_PNG, IMAGETYPE_JPEG], true)) {
        throw new RuntimeException('Only PNG and JPEG images are accepted.');
    }
    [$w, $h] = $info;
    if ($w < 1 || $h < 1 || $w > 4000 || $h > 4000 || $w * $h > 12000000) {
        throw new RuntimeException('That image has unsupported dimensions.');
    }
    $src = @imagecreatefromstring($raw);
    if ($src === false) {
        throw new RuntimeException('That image could not be read.');
    }
    $tw = min($w, MAX_OUTPUT_WIDTH);
    $th = max(1, (int) round($h * $tw / $w));

    $dst = imagecreatetruecolor($tw, $th);
    imagefill($dst, 0, 0, imagecolorallocate($dst, 255, 255, 255));
    imagecopyresampled($dst, $src, 0, 0, 0, 0, $tw, $th, $w, $h);

    $ov = imagecreatefrompng(OVERLAY_DIR . '/' . $overlay . '.png');
    imagealphablending($dst, true);
    imagecopyresampled($dst, $ov, 0, 0, 0, 0, $tw, $th, imagesx($ov), imagesy($ov));

    $file = bin2hex(random_bytes(16)) . '.png';
    if (!imagepng($dst, IMG_DIR . '/' . $file)) {
        throw new RuntimeException('Could not save the image.');
    }
    return $file;
}
