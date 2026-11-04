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
  var streamReady = false;
  var mode = 'none'; // 'video' or 'still'

  function setStatus(text) { statusEl.textContent = text; }

  function refresh() {
    captureBtn.disabled = !(selected && mode !== 'none');
  }

  // --- camera ---------------------------------------------------------------
  function onStream(stream) {
    if ('srcObject' in video) {
      video.srcObject = stream;
    } else {
      video.src = window.URL.createObjectURL(stream);
    }
    streamReady = true;
    mode = 'video';
    refresh();
    setStatus('Choose a decoration, then take a photo.');
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
      overlayPreview.src = '/static/overlays/' + encodeURIComponent(selected) + '.png';
      overlayPreview.classList.remove('hidden');
      refresh();
    });
  });

  // --- upload ---------------------------------------------------------------
  fileInput.addEventListener('change', function () {
    var file = fileInput.files[0];
    if (!file) { return; }
    if (!/^image\//.test(file.type)) {
      setStatus('Please choose an image file.');
      return;
    }
    var reader = new FileReader();
    reader.onload = function () {
      still.onload = function () {
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
    form.action = result.url + '/delete';
    var token = document.createElement('input');
    token.type = 'hidden';
    token.name = 'csrf';
    token.value = csrf;
    var del = document.createElement('button');
    del.type = 'submit';
    del.className = 'danger small';
    del.textContent = 'Delete';
    form.appendChild(token);
    form.appendChild(del);
    li.appendChild(link);
    li.appendChild(form);
    thumbs.insertBefore(li, thumbs.firstChild);
  }

  captureBtn.addEventListener('click', function () {
    var source = mode === 'video' ? video : still;
    var width = source.videoWidth || source.naturalWidth;
    var height = source.videoHeight || source.naturalHeight;
    if (!width || !height) {
      setStatus('The image is not ready yet. Please try again.');
      return;
    }
    var scale = Math.min(1, MAX_WIDTH / width);
    var canvas = document.createElement('canvas');
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    canvas.getContext('2d').drawImage(source, 0, 0, canvas.width, canvas.height);

    captureBtn.disabled = true;
    setStatus('Saving...');
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/editor/create');
    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
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
    xhr.send('csrf=' + encodeURIComponent(csrf) +
             '&overlay=' + encodeURIComponent(selected) +
             '&image=' + encodeURIComponent(canvas.toDataURL('image/png')));
  });
}());
