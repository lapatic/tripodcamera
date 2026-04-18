/**
 * Stream monitoring and control functionality
 */

let streamLoadTime = null;
let isStreamLoaded = false;
let isMobileFullscreen = false;

/**
 * Detect if the device is iOS
 */
function isIOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
}

/**
 * Detect if fullscreen API is available
 */
function supportsFullscreen() {
    return !!(document.fullscreenEnabled ||
              document.webkitFullscreenEnabled ||
              document.mozFullScreenEnabled ||
              document.msFullscreenEnabled);
}

/**
 * Handle successful stream load
 */
function handleStreamLoad() {
    console.log('Stream loaded successfully');
    streamLoadTime = Date.now();
    isStreamLoaded = true;

    updateStatus('connected', 'Connected');
    hideLoading();
}

/**
 * Handle stream error
 */
function handleStreamError() {
    console.error('Stream error at:', new Date());
    isStreamLoaded = false;

    updateStatus('error', 'Connection Lost');
    showLoading();

    // Attempt to reconnect after 5 seconds
    setTimeout(() => {
        if (!isStreamLoaded) {
            console.log('Attempting to reconnect...');
            reloadStream();
        }
    }, 5000);
}

/**
 * Update connection status indicator
 * @param {string} state - Status state: 'connecting', 'connected', or 'error'
 * @param {string} message - Status message to display
 */
function updateStatus(state, message) {
    const status = document.getElementById('status');
    const statusText = status.querySelector('.status-text');

    status.className = `status ${state}`;
    statusText.textContent = message;
}

/**
 * Reload the stream with a cache-busting timestamp
 */
function reloadStream() {
    console.log('Reloading stream...');
    updateStatus('connecting', 'Reconnecting...');
    showLoading();

    const img = document.getElementById('stream');
    const url = img.src.split('?')[0];
    img.src = url + '?t=' + Date.now();
}

/**
 * Show loading overlay
 */
function showLoading() {
    const loading = document.getElementById('loading');
    loading.classList.remove('hidden');
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    const loading = document.getElementById('loading');
    loading.classList.add('hidden');
}

/**
 * Toggle fullscreen mode (iOS-compatible)
 */
function toggleFullscreen() {
    // Use mobile fullscreen mode for iOS or when Fullscreen API is not supported
    if (isIOS() || !supportsFullscreen()) {
        toggleMobileFullscreen();
        return;
    }

    // Use standard Fullscreen API for other devices
    const container = document.getElementById('streamContainer');

    if (!document.fullscreenElement &&
        !document.webkitFullscreenElement &&
        !document.mozFullScreenElement) {
        // Enter fullscreen
        if (container.requestFullscreen) {
            container.requestFullscreen();
        } else if (container.webkitRequestFullscreen) {
            container.webkitRequestFullscreen();
        } else if (container.mozRequestFullScreen) {
            container.mozRequestFullScreen();
        } else if (container.msRequestFullscreen) {
            container.msRequestFullscreen();
        }
        console.log('Entering fullscreen mode');
    } else {
        // Exit fullscreen
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.mozCancelFullScreen) {
            document.mozCancelFullScreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
        console.log('Exiting fullscreen mode');
    }
}

/**
 * Toggle mobile fullscreen mode (for iOS and devices without Fullscreen API)
 */
function toggleMobileFullscreen() {
    if (!isMobileFullscreen) {
        // Enter mobile fullscreen
        document.body.classList.add('mobile-fullscreen');
        isMobileFullscreen = true;
        console.log('Entering mobile fullscreen mode');

        // Scroll to top to hide browser chrome on mobile
        window.scrollTo(0, 0);

        // Lock scroll position
        document.body.style.overflow = 'hidden';
        document.body.style.position = 'fixed';
        document.body.style.width = '100%';
        document.body.style.height = '100%';

    } else {
        // Exit mobile fullscreen
        document.body.classList.remove('mobile-fullscreen');
        isMobileFullscreen = false;
        console.log('Exiting mobile fullscreen mode');

        // Unlock scroll
        document.body.style.overflow = '';
        document.body.style.position = '';
        document.body.style.width = '';
        document.body.style.height = '';
    }
}

/**
 * Initialize the stream interface
 */
function init() {
    console.log('Initializing stream interface...');
    updateStatus('connecting', 'Connecting...');

    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Press 'R' to reload stream
        if (e.key === 'r' || e.key === 'R') {
            reloadStream();
        }
        // Press 'F' to toggle fullscreen
        if (e.key === 'f' || e.key === 'F') {
            toggleFullscreen();
        }
        // ESC exits both types of fullscreen
        if (e.key === 'Escape') {
            if (isMobileFullscreen) {
                toggleMobileFullscreen();
            } else if (document.fullscreenElement) {
                console.log('Exiting fullscreen via ESC');
            }
        }
    });

    // Monitor fullscreen changes
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);

    // Monitor stream health
    setInterval(() => {
        if (isStreamLoaded && streamLoadTime) {
            const uptime = Math.floor((Date.now() - streamLoadTime) / 1000);
            console.log(`Stream uptime: ${uptime}s`);
        }
    }, 30000); // Log every 30 seconds
}

/**
 * Handle fullscreen state changes
 */
function handleFullscreenChange() {
    const isFullscreen = !!(document.fullscreenElement ||
                            document.webkitFullscreenElement ||
                            document.mozFullScreenElement ||
                            document.msFullscreenElement);

    console.log(`Fullscreen mode: ${isFullscreen ? 'ON' : 'OFF'}`);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
