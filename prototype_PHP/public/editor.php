<?php
declare(strict_types=1);
require __DIR__ . '/../src/bootstrap.php';

$user = require_login();
$mine = q('SELECT id FROM images WHERE user_id = ? ORDER BY created_at DESC, id DESC', [$user['id']])->fetchAll();
render_header('Editor');
?>
<h1>Editor</h1>
<div class="editor">
<section class="card main-col">
<div class="stage"><video id="video" autoplay playsinline muted></video>
<img id="still" class="hidden" alt="Selected photo"><img id="overlay-preview" class="hidden" alt=""></div>
<p id="status" class="muted" role="status">Choose a decoration, then take a photo.</p>
<div class="overlays">
<?php foreach (list_overlays() as $name): ?>
<button type="button" class="overlay" data-name="<?= e($name) ?>"><img src="/overlays/<?= e($name) ?>.png" alt="<?= e($name) ?>"></button>
<?php endforeach; ?>
</div>
<div class="actions">
<button type="button" id="capture" disabled>Take photo</button>
<label class="button secondary">Upload image<input type="file" id="upload" accept="image/png,image/jpeg" class="visually-hidden"></label>
<button type="button" id="use-camera" class="secondary hidden">Use camera</button>
</div>
<input type="hidden" id="csrf" value="<?= e($_SESSION['csrf']) ?>">
</section>
<aside class="card side-col"><h2>Your photos</h2>
<ul id="thumbs" class="thumbs"><?php foreach ($mine as $m) { echo thumb_html((int) $m['id']); } ?></ul>
</aside>
</div>
<?php render_footer(['/editor.js']);
