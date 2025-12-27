// AI Vision Dashboard JavaScript
// Handles CTA navigation, animated elements, and reduced motion preferences

(function() {
    'use strict';
    
    // Check for reduced motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    function init() {
        setupCTAButtons();
        setupDragAndDrop();
        handleReducedMotion();
        addAccessibilityFeatures();
    }
    
    // Setup CTA button navigation
    function setupCTAButtons() {
        const ctaButtons = document.querySelectorAll('.btn-cta');
        
        ctaButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                // Add ripple effect
                if (!prefersReducedMotion) {
                    createRipple(e, this);
                }
            });
        });
    }
    
    // Create ripple effect on button click
    function createRipple(event, button) {
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        button.appendChild(ripple);
        
        setTimeout(() => ripple.remove(), 600);
    }
    
    // Setup drag and drop for upload zone
    function setupDragAndDrop() {
        const dropZone = document.querySelector('.drag-drop-zone');
        if (!dropZone) return;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-over');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-over');
            }, false);
        });
        
        dropZone.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                const fileInput = document.getElementById('video-file-input');
                if (fileInput) {
                    fileInput.files = files;
                    // Trigger change event
                    const event = new Event('change', { bubbles: true });
                    fileInput.dispatchEvent(event);
                }
            }
        }
    }
    
    // Handle reduced motion preferences
    function handleReducedMotion() {
        if (prefersReducedMotion) {
            document.body.classList.add('reduce-motion');
            
            // Disable blob animations
            const blobs = document.querySelectorAll('.blob, .glass-shape');
            blobs.forEach(blob => {
                blob.style.animation = 'none';
            });
            
            // Disable background animation
            const animatedBg = document.querySelector('.animated-bg');
            if (animatedBg) {
                animatedBg.style.animation = 'none';
            }
        }
    }
    
    // Add accessibility features
    function addAccessibilityFeatures() {
        // Add keyboard navigation for cards
        const cards = document.querySelectorAll('.feature-card');
        cards.forEach(card => {
            card.setAttribute('tabindex', '0');
            
            card.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const link = this.querySelector('a');
                    if (link) link.click();
                }
            });
        });
        
        // Announce status changes for screen readers
        const statusRegion = document.querySelector('[aria-live]');
        if (statusRegion) {
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList' || mutation.type === 'characterData') {
                        // Status has changed, screen reader will announce
                        console.log('Status updated:', statusRegion.textContent);
                    }
                });
            });
            
            observer.observe(statusRegion, {
                childList: true,
                characterData: true,
                subtree: true
            });
        }
    }
    
    // Update status region (called from upload logic)
    window.updateStatus = function(message, type) {
        const statusRegion = document.querySelector('[aria-live="polite"]');
        if (statusRegion) {
            statusRegion.textContent = message;
            statusRegion.className = 'status-region status-' + type;
            statusRegion.style.display = 'block';
        }
    };
    
    // Smooth scroll to upload section (if on same page)
    window.scrollToUpload = function() {
        const uploadSection = document.getElementById('upload-section');
        if (uploadSection) {
            uploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };
    
})();
