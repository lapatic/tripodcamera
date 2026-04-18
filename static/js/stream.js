/**
 * Stream monitoring and control functionality
 */

let streamLoadTime = null;
let isStreamLoaded = false;

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
 * Toggle fullscreen mode
 */
function toggleFullscreen() {
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
        // ESC also exits fullscreen (handled by browser, but log it)
        if (e.key === 'Escape' && document.fullscreenElement) {
            console.log('Exiting fullscreen via ESC');
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
