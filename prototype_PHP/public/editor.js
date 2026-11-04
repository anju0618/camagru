(function () {
  'use strict';

  var video = document.getElementById('video');
  var still = document.getElementById('still');
  var overlayPreview = document.getElementById('overlay-preview');
  var captureBtn = document.getElementById('capture');
  var useCameraBtn = document.getElementById('use-camera');
  var fileInput = document.getElementById('upload');
  var statusEl = document.getElementById('status');
  var thumbs = document.getElementById('thumbs');
  var csrf = document.getElementById('csrf').value;
  var MAX_WIDTH = 640;

  var selected = null;
  var uploadedFile = null;
  var streamReady = false;
  var mode = 'none'; // 'video' or 'still'

  function setStatus(text) { statusEl.textContent = text; }
  function refresh() { captureBtn.disabled = !(selected && mode !== 'none'); }

  // --- camera ---------------------------------------------------------------
  function onStream(stream) {
    if ('srcObject' in video) {
      video.srcObject = stream;
    } else {
      video.src = window.URL.createObjectURL(stream);
    }
    streamReady = true;
    if (mode !== 'still') { mode = 'video'; }
    refresh();
  }

  function onNoCamera() {
    video.classList.add('hidden');
    setStatus('No camera available. Choose a decoration and upload an image instead.');
  }

  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia({ video: true }).then(onStream, onNoCamera);
  } else {
    var legacy = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
    if (legacy) {
      legacy.call(navigator, { video: true }, onStream, onNoCamera);
    } else {
      onNoCamera();
    }
  }

  // --- decorations ----------------------------------------------------------
  var buttons = document.querySelectorAll('.overlay');
  Array.prototype.forEach.call(buttons, function (button) {
    button.addEventListener('click', function () {
      Array.prototype.forEach.call(buttons, function (b) { b.classList.remove('selected'); });
      button.classList.add('selected');
      selected = button.getAttribute('data-name');
      overlayPreview.src = '/overlays/' + encodeURIComponent(selected) + '.png';
      overlayPreview.classList.remove('hidden');
      refresh();
    });
  });

  // --- upload (the server accepts PNG and JPEG) -----------------------------
  fileInput.addEventListener('change', function () {
    var file = fileInput.files[0];
    if (!file) { return; }
    if (!/^image\/(png|jpeg)$/.test(file.type)) {
      setStatus('Please choose a PNG or JPEG image.');
      return;
    }
    var reader = new FileReader();
    reader.onload = function () {
      still.onload = function () {
        uploadedFile = file;
        video.classList.add('hidden');
        still.classList.remove('hidden');
        mode = 'still';
        if (streamReady) { useCameraBtn.classList.remove('hidden'); }
        refresh();
        setStatus('Image ready. Choose a decoration and press "Take photo".');
      };
      still.onerror = function () { setStatus('That file could not be read as an image.'); };
      still.src = reader.result;
    };
    reader.readAsDataURL(file);
    fileInput.value = '';
  });

  useCameraBtn.addEventListener('click', function () {
    still.classList.add('hidden');
    video.classList.remove('hidden');
    useCameraBtn.classList.add('hidden');
    uploadedFile = null;
    mode = 'video';
    refresh();
  });

  // --- capture --------------------------------------------------------------
  function addThumb(result) {
    var li = document.createElement('li');
    var link = document.createElement('a');
    link.href = result.url;
    var img = document.createElement('img');
    img.src = result.img;
    img.alt = 'Your photo';
    link.appendChild(img);
    var form = document.createElement('form');
    form.method = 'post';
    form.action = result.url;
    var token = document.createElement('input');
    token.type = 'hidden';
    token.name = 'csrf';
    token.value = csrf;
    var action = document.createElement('input');
    action.type = 'hidden';
    action.name = 'action';
    action.value = 'delete';
    var del = document.createElement('button');
    del.type = 'submit';
    del.className = 'danger small';
    del.textContent = 'Delete';
    form.appendChild(token);
    form.appendChild(action);
    form.appendChild(del);
    li.appendChild(link);
    li.appendChild(form);
    thumbs.insertBefore(li, thumbs.firstChild);
  }

  captureBtn.addEventListener('click', function () {
    var data = new FormData();
    data.append('csrf', csrf);
    data.append('overlay', selected);
    if (mode === 'still') {
      data.append('upload', uploadedFile);
    } else {
      var width = video.videoWidth;
      var height = video.videoHeight;
      if (!width || !height) {
        setStatus('The camera is not ready yet. Please try again.');
        return;
      }
      var scale = Math.min(1, MAX_WIDTH / width);
      var canvas = document.createElement('canvas');
      canvas.width = Math.round(width * scale);
      canvas.height = Math.round(height * scale);
      canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
      data.append('image', canvas.toDataURL('image/png'));
    }

    captureBtn.disabled = true;
    setStatus('Saving...');
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/create.php');
    xhr.onload = function () {
      var result = {};
      try { result = JSON.parse(xhr.responseText); } catch (e) { result = {}; }
      if (xhr.status === 200 && result.url) {
        addThumb(result);
        setStatus('Saved! Your photo is in the gallery.');
      } else {
        setStatus(result.error || 'Something went wrong. Please try again.');
      }
      refresh();
    };
    xhr.onerror = function () {
      setStatus('Network error. Please try again.');
      refresh();
    };
    xhr.send(data);
  });
}());
