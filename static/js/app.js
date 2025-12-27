// Video upload and recording functionality

let mediaRecorder;
let recordedChunks = [];
let stream;
let recordedBlob;
let selectedFile;

// Initialize upload page
function initUploadPage() {
    setupTabs();
    setupFileUpload();
    setupRecording();
    setupProcessing();
}

// Tab switching
function setupTabs() {
    const uploadTab = document.getElementById('upload-tab');
    const recordTab = document.getElementById('record-tab');
    const uploadSection = document.getElementById('upload-section');
    const recordSection = document.getElementById('record-section');
    
    if (!uploadTab || !recordTab) return;
    
    uploadTab.addEventListener('click', () => {
        uploadTab.classList.add('border-blue-500', 'text-blue-600');
        uploadTab.classList.remove('text-gray-600');
        recordTab.classList.remove('border-blue-500', 'text-blue-600');
        recordTab.classList.add('text-gray-600');
        uploadSection.classList.remove('hidden');
        recordSection.classList.add('hidden');
        resetState();
    });
    
    recordTab.addEventListener('click', () => {
        recordTab.classList.add('border-blue-500', 'text-blue-600');
        recordTab.classList.remove('text-gray-600');
        uploadTab.classList.remove('border-blue-500', 'text-blue-600');
        uploadTab.classList.add('text-gray-600');
        recordSection.classList.remove('hidden');
        uploadSection.classList.add('hidden');
        resetState();
    });
}

// File upload handling
function setupFileUpload() {
    const fileInput = document.getElementById('video-file-input');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    const processBtn = document.getElementById('process-btn');
    
    if (!fileInput) return;
    
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            selectedFile = file;
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            fileInfo.classList.remove('hidden');
            processBtn.classList.remove('hidden');
        }
    });
}

// Camera recording setup
function setupRecording() {
    const startCameraBtn = document.getElementById('start-camera-btn');
    const startRecordBtn = document.getElementById('start-record-btn');
    const stopRecordBtn = document.getElementById('stop-record-btn');
    const rerecordBtn = document.getElementById('rerecord-btn');
    const cameraPreview = document.getElementById('camera-preview');
    const recordedPreview = document.getElementById('recorded-preview');
    const processBtn = document.getElementById('process-btn');
    
    if (!startCameraBtn) return;
    
    startCameraBtn.addEventListener('click', async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ 
                video: true, 
                audio: true 
            });
            cameraPreview.srcObject = stream;
            startCameraBtn.classList.add('hidden');
            startRecordBtn.classList.remove('hidden');
        } catch (error) {
            showError('Camera access denied: ' + error.message);
        }
    });
    
    startRecordBtn.addEventListener('click', () => {
        recordedChunks = [];
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
        
        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                recordedChunks.push(e.data);
            }
        };
        
        mediaRecorder.onstop = () => {
            recordedBlob = new Blob(recordedChunks, { type: 'video/webm' });
            recordedPreview.src = URL.createObjectURL(recordedBlob);
            cameraPreview.classList.add('hidden');
            recordedPreview.classList.remove('hidden');
            processBtn.classList.remove('hidden');
        };
        
        mediaRecorder.start();
        startRecordBtn.classList.add('hidden');
        stopRecordBtn.classList.remove('hidden');
    });
    
    stopRecordBtn.addEventListener('click', () => {
        mediaRecorder.stop();
        stream.getTracks().forEach(track => track.stop());
        stopRecordBtn.classList.add('hidden');
        rerecordBtn.classList.remove('hidden');
    });
    
    rerecordBtn.addEventListener('click', () => {
        recordedPreview.classList.add('hidden');
        cameraPreview.classList.remove('hidden');
        rerecordBtn.classList.add('hidden');
        startCameraBtn.classList.remove('hidden');
        processBtn.classList.add('hidden');
        recordedBlob = null;
    });
}

// Processing setup
function setupProcessing() {
    const processBtn = document.getElementById('process-btn');
    const retryBtn = document.getElementById('retry-btn');
    const processAnotherBtn = document.getElementById('process-another-btn');
    
    if (!processBtn) return;
    
    processBtn.addEventListener('click', processVideo);
    
    if (retryBtn) {
        retryBtn.addEventListener('click', processVideo);
    }
    
    if (processAnotherBtn) {
        processAnotherBtn.addEventListener('click', resetState);
    }
}

// Process video
async function processVideo() {
    const processingState = document.getElementById('processing-state');
    const resultsSection = document.getElementById('results-section');
    const errorSection = document.getElementById('error-section');
    const processBtn = document.getElementById('process-btn');
    
    // Hide previous states
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
    processBtn.classList.add('hidden');
    
    // Show processing
    processingState.classList.remove('hidden');
    
    // Update status for accessibility
    if (typeof updateUploadStatus === 'function') {
        updateUploadStatus('Uploading video...', 'uploading');
    }
    
    try {
        const formData = new FormData();
        
        if (selectedFile) {
            formData.append('video', selectedFile);
        } else if (recordedBlob) {
            formData.append('video', recordedBlob, 'recorded-video.webm');
        } else {
            throw new Error('No video selected');
        }
        
        // Update status
        if (typeof updateUploadStatus === 'function') {
            updateUploadStatus('Processing video with AI...', 'processing');
        }
        
        const response = await fetch('/api/upload-video', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        processingState.classList.add('hidden');
        
        if (data.status === 'ok') {
            if (typeof updateUploadStatus === 'function') {
                updateUploadStatus('Processing complete!', 'complete');
            }
            showResults(data);
        } else {
            showError(data.message || 'Processing failed');
        }
    } catch (error) {
        processingState.classList.add('hidden');
        showError(error.message);
    }
}

// Show results
function showResults(data) {
    const resultsSection = document.getElementById('results-section');
    const resultVideo = document.getElementById('result-video');
    const downloadVideo = document.getElementById('download-video');
    
    if (data.video_url && resultVideo) {
        resultVideo.src = data.video_url;
        resultVideo.load();
        if (downloadVideo) {
            downloadVideo.href = data.video_url;
        }
    }
    
    if (resultsSection) {
        resultsSection.classList.remove('hidden');
    }
}

// Show error
function showError(message) {
    const errorSection = document.getElementById('error-section');
    const errorMessage = document.getElementById('error-message');
    
    errorMessage.textContent = message;
    errorSection.classList.remove('hidden');
    
    // Update status for accessibility
    if (typeof updateUploadStatus === 'function') {
        updateUploadStatus('Error: ' + message, 'error');
    }
}

// Reset state
function resetState() {
    selectedFile = null;
    recordedBlob = null;
    
    const fileInput = document.getElementById('video-file-input');
    const fileInfo = document.getElementById('file-info');
    const processBtn = document.getElementById('process-btn');
    const resultsSection = document.getElementById('results-section');
    const errorSection = document.getElementById('error-section');
    const processingState = document.getElementById('processing-state');
    
    if (fileInput) fileInput.value = '';
    if (fileInfo) fileInfo.classList.add('hidden');
    if (processBtn) processBtn.classList.add('hidden');
    if (resultsSection) resultsSection.classList.add('hidden');
    if (errorSection) errorSection.classList.add('hidden');
    if (processingState) processingState.classList.add('hidden');
}


// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Auto-initialize when page loads (only if elements exist)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (document.getElementById('upload-tab')) {
            initUploadPage();
        }
    });
} else {
    if (document.getElementById('upload-tab')) {
        initUploadPage();
    }
}
