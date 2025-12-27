// static/js/upload.js
console.log('🎬 upload.js loaded');

let selectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
  setupFileUpload();
  setupProcessing();
});

function setupFileUpload() {
  const fileInput = document.getElementById('video-file-input');
  const dropZone = document.getElementById('drop-zone');
  const fileInfo = document.getElementById('file-info');
  const fileName = document.getElementById('file-name');
  const fileSize = document.getElementById('file-size');
  const processBtn = document.getElementById('process-btn');

  fileInput.addEventListener('change', (e) => {
    const f = e.target.files[0];
    if (!f) return;
    if (!f.type.startsWith('video/')) return showError('Please select a valid video file.');
    if (f.size > 500*1024*1024) return showError('Maximum size is 500MB.');

    selectedFile = f;
    fileName.textContent = f.name;
    fileSize.textContent = formatSize(f.size);
    fileInfo.classList.remove('hidden');
    processBtn.classList.remove('hidden');
  });

  ['dragenter','dragover','dragleave','drop'].forEach(ev => {
    dropZone.addEventListener(ev, (e)=>{e.preventDefault(); e.stopPropagation();});
  });
  ['dragenter','dragover'].forEach(ev => dropZone.addEventListener(ev, ()=>dropZone.classList.add('border-indigo-500','bg-indigo-50')));
  ['dragleave','drop'].forEach(ev => dropZone.addEventListener(ev, ()=>dropZone.classList.remove('border-indigo-500','bg-indigo-50')));

  dropZone.addEventListener('drop', (e) => {
    const f = e.dataTransfer.files[0];
    if (!f) return;
    fileInput.files = e.dataTransfer.files;
    fileInput.dispatchEvent(new Event('change'));
  });
}

function setupProcessing() {
  const processBtn = document.getElementById('process-btn');
  const retryBtn = document.getElementById('retry-btn');
  const againBtn = document.getElementById('process-another-btn');

  processBtn.addEventListener('click', (e)=>{e.preventDefault(); processVideo();});
  retryBtn?.addEventListener('click', ()=>{hideAll(); document.getElementById('upload-section').classList.remove('hidden');});
  againBtn?.addEventListener('click', resetState);
}

async function processVideo() {
  if (!selectedFile) return showError('Please select a video file first.');

  console.log('🚀 Starting video processing...');
  hideAll();
  document.getElementById('processing-state').classList.remove('hidden');

  const fd = new FormData();
  fd.append('video', selectedFile, selectedFile.name);

  try {
    console.log('📤 Uploading to /api/upload-video...');

    const res = await fetch('/api/upload-video', {
      method: 'POST',
      body: fd,
      credentials: 'same-origin'  // Important for session cookies
    });

    console.log('📥 Response status:', res.status);

    if (!res.ok) {
      let errorMsg = `Server error ${res.status}`;
      try {
        const errorData = await res.json();
        errorMsg = errorData.message || errorData.error || errorMsg;
      } catch {
        const text = await res.text();
        errorMsg = text.slice(0, 200) || errorMsg;
      }
      throw new Error(errorMsg);
    }

    const data = await res.json();
    console.log('✅ Response data:', data);

    if (data.status !== 'ok') {
      throw new Error(data.message || 'Processing failed.');
    }

    document.getElementById('processing-state').classList.add('hidden');
    showResults(data);

  } catch (err) {
    console.error('❌ Processing error:', err);
    document.getElementById('processing-state').classList.add('hidden');
    showError(err.message || 'Failed to process video. Please try again.');
  }
}

function showResults(data) {
  console.log('📊 Showing results:', data);
  hideAll();
  document.getElementById('results-section').classList.remove('hidden');

  // Video
  const videoEl = document.getElementById('result-video');
  const videoUrl = data.video_url;

  console.log('🎬 Video URL:', videoUrl);

  if (videoEl && videoUrl) {
    videoEl.src = videoUrl;
    videoEl.load();

    const dl = document.getElementById('download-video');
    if (dl) {
      dl.href = videoUrl;
      dl.classList.remove('hidden');
    }
  } else {
    console.error('❌ No video URL found in response');
    showError('No video URL returned from server. Check console for details.');
    return;
  }

  console.log('✅ Results displayed successfully');
}

function showError(msg) {
  console.error('💥 Showing error:', msg);
  hideAll();
  document.getElementById('error-message').textContent = msg;
  document.getElementById('error-section').classList.remove('hidden');
  document.getElementById('upload-section').classList.remove('hidden');
}

function hideAll() {
  ['processing-state','results-section','error-section'].forEach(id=>{
    const el = document.getElementById(id);
    el && el.classList.add('hidden');
  });
}

function resetState() {
  selectedFile = null;
  const fileInfo = document.getElementById('file-info');
  const processBtn = document.getElementById('process-btn');
  document.getElementById('video-file-input').value = '';
  fileInfo.classList.add('hidden');
  processBtn.classList.add('hidden');
  hideAll();
  document.getElementById('upload-section').classList.remove('hidden');
}

function formatSize(bytes){
  if (bytes===0) return '0 Bytes';
  const k=1024, sizes=['Bytes','KB','MB','GB'];
  const i=Math.floor(Math.log(bytes)/Math.log(k));
  return (bytes/Math.pow(k,i)).toFixed(2)+' '+sizes[i];
}