/**
 * General Helper Utilities
 */

/**
 * Format seconds to MM:SS
 * @param {number} seconds - Seconds to format
 * @returns {string} - Formatted time string
 */
export function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '0:00';
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Get stage emoji for choreography generation
 * @param {string} stage - Current stage
 * @returns {string} - Emoji for stage
 */
export function getStageEmoji(stage) {
    const emojis = {
        initializing: '🚀',
        downloading: '⬇️',
        analyzing: '🎵',
        selecting: '💃',
        generating: '🎬',
        finalizing: '✨',
        completed: '🎉',
        failed: '❌'
    };
    return emojis[stage] || '⏳';
}

/**
 * Safely call a function if it exists
 * @param {function} fn - Function to call
 * @param {...any} args - Arguments to pass
 */
export function safeCall(fn, ...args) {
    if (typeof fn === 'function') {
        try {
            return fn(...args);
        } catch (e) {
            console.error('Error calling function:', e);
        }
    }
}

/**
 * Safely show notification via $root if available
 * @param {object} $root - Alpine.js $root reference
 * @param {string} message - Message to show
 * @param {string} type - Type (success, error, info, warning)
 */
export function showNotification($root, message, type = 'info') {
    if ($root?.showNotification) {
        $root.showNotification(message, type);
    } else {
        console.log(`[${type.toUpperCase()}]:`, message);
    }
}

// Make available globally
window.HelperUtils = {
    formatTime,
    getStageEmoji,
    safeCall,
    showNotification
};
