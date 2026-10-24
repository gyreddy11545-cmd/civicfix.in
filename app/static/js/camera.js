/**
 * CIVICFIX — REAL MOBILE CAMERA CAPTURE & GALLERY PICKER
 * Android environment camera capture, live preview, replace/remove controls,
 * object URL lifecycle management, and smooth zoom-in effects.
 */

document.addEventListener('DOMContentLoaded', () => {
  initCameraControls();
});

function initCameraControls() {
  const cameraInput = document.getElementById('camera-file-input');
  const galleryInput = document.getElementById('gallery-file-input');
  const takePhotoBtn = document.getElementById('take-photo-btn');
  const chooseGalleryBtn = document.getElementById('choose-gallery-btn');
  const replacePhotoBtn = document.getElementById('replace-photo-btn');
  const removePhotoBtn = document.getElementById('remove-photo-btn');
  const dropzone = document.getElementById('camera-dropzone');
  const previewContainer = document.getElementById('preview-container');
  const previewImage = document.getElementById('preview-image');
  const previewFilename = document.getElementById('preview-filename');
  const previewMeta = document.getElementById('preview-meta');
  const dropzonePrompt = document.getElementById('dropzone-prompt');
  const form = document.getElementById('civic-report-form');
  const uploadProgress = document.getElementById('preview-upload-progress');

  if (!cameraInput || !galleryInput) return;

  // Track active object URL to revoke when replaced/removed
  let currentObjectURL = null;

  // Trigger camera file input (capture="environment" for rear camera on mobile)
  if (takePhotoBtn) {
    takePhotoBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      cameraInput.click();
    });
  }

  // Trigger gallery file input (without capture constraint)
  if (chooseGalleryBtn) {
    chooseGalleryBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      galleryInput.click();
    });
  }

  // Replace photo triggers gallery file selection
  if (replacePhotoBtn) {
    replacePhotoBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      galleryInput.click();
    });
  }

  // Handle files selected from camera
  cameraInput.addEventListener('change', () => {
    if (cameraInput.files && cameraInput.files.length > 0) {
      handleFileSelection(cameraInput.files[0], cameraInput);
    }
  });

  // Handle files selected from gallery
  galleryInput.addEventListener('change', () => {
    if (galleryInput.files && galleryInput.files.length > 0) {
      handleFileSelection(galleryInput.files[0], galleryInput);
    }
  });

  // Desktop drag and drop onto dropzone
  if (dropzone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dropzone-active');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dropzone-active');
      }, false);
    });

    dropzone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt ? dt.files : null;
      if (files && files.length > 0) {
        galleryInput.files = files; // Assign files to gallery input
        handleFileSelection(files[0], galleryInput);
      }
    });
  }

  // Remove photo handler
  if (removePhotoBtn) {
    removePhotoBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      resetPhotoSelection();
    });
  }

  function handleFileSelection(file, activeInput) {
    if (!file) return;

    // Validate type (common image formats: JPEG, PNG, WEBP, HEIC)
    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/jpg'];
    const isImage = file.type.startsWith('image/') || validTypes.includes(file.type.toLowerCase()) ||
                    /\.(jpe?g|png|webp|heic)$/i.test(file.name);

    if (!isImage) {
      showPhotoFeedback('Unsupported file format. Please upload a JPG, PNG, WEBP, or HEIC photo.', 'error');
      resetPhotoSelection();
      return;
    }

    // Validate size (16MB max limit)
    const maxSize = 16 * 1024 * 1024;
    if (file.size > maxSize) {
      const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
      showPhotoFeedback(`File size (${sizeMb} MB) exceeds the 16 MB limit. Please select a smaller photo.`, 'error');
      resetPhotoSelection();
      return;
    }

    // Revoke previous object URL to prevent memory leaks
    if (currentObjectURL) {
      try {
        URL.revokeObjectURL(currentObjectURL);
      } catch (err) {}
    }

    // Create safe object URL for instantaneous high-performance preview
    currentObjectURL = URL.createObjectURL(file);

    if (previewImage) {
      previewImage.src = currentObjectURL;
      // Trigger zoom-in animation
      previewImage.classList.remove('preview-animated');
      void previewImage.offsetWidth; // Force reflow
      previewImage.classList.add('preview-animated');
    }

    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
    if (previewFilename) {
      previewFilename.textContent = file.name;
    }
    if (previewMeta) {
      previewMeta.textContent = `${sizeMb} MB • Ready for municipal verification`;
    }

    if (previewContainer) {
      previewContainer.style.display = 'block';
    }
    if (dropzonePrompt) {
      dropzonePrompt.style.display = 'none';
    }

    // Synchronize inputs so the non-active one is cleared
    if (activeInput === cameraInput && galleryInput) {
      galleryInput.value = '';
    } else if (activeInput === galleryInput && cameraInput) {
      cameraInput.value = '';
    }

    showPhotoFeedback('Photo evidence attached successfully.', 'success');
  }

  function resetPhotoSelection() {
    if (currentObjectURL) {
      try {
        URL.revokeObjectURL(currentObjectURL);
      } catch (err) {}
      currentObjectURL = null;
    }

    if (cameraInput) cameraInput.value = '';
    if (galleryInput) galleryInput.value = '';
    if (previewImage) previewImage.src = '';
    if (previewFilename) previewFilename.textContent = '';
    if (previewMeta) previewMeta.textContent = '';
    if (previewContainer) previewContainer.style.display = 'none';
    if (dropzonePrompt) dropzonePrompt.style.display = 'block';
  }

  function showPhotoFeedback(msg, type) {
    const feedback = document.getElementById('camera-feedback');
    if (!feedback) return;
    feedback.textContent = msg;
    feedback.className = `camera-feedback ${type}`;
    feedback.style.display = 'block';
    setTimeout(() => {
      if (feedback && type === 'success') {
        feedback.style.display = 'none';
      }
    }, 4000);
  }

  // Upload progress indicator on form submission
  if (form) {
    form.addEventListener('submit', () => {
      const hasPhoto = (cameraInput.files && cameraInput.files.length > 0) ||
                       (galleryInput.files && galleryInput.files.length > 0);
      if (hasPhoto && uploadProgress) {
        uploadProgress.style.display = 'block';
      }
    });
  }
}
