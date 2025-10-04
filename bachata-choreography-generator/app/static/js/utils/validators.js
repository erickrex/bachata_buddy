/**
 * Validation Utilities
 */

/**
 * Validate YouTube URL format
 * @param {string} url - URL to validate
 * @returns {boolean} - True if valid YouTube URL
 */
export function isValidYouTubeUrl(url) {
    return /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)[a-zA-Z0-9_-]{11}/.test(url);
}

/**
 * Check if user is authenticated
 * @param {object} $root - Alpine.js $root reference
 * @returns {boolean} - True if authenticated
 */
export function isAuthenticated($root) {
    return $root?.user?.isAuthenticated || !!localStorage.getItem('auth_token');
}

/**
 * Parse XHR response safely
 * @param {XMLHttpRequest} xhr - XHR object
 * @returns {object|null} - Parsed response or null
 */
export function parseXhrResponse(xhr) {
    try {
        const responseText = xhr.responseText || xhr.response;
        if (typeof responseText === 'object') {
            return responseText;
        }
        return JSON.parse(responseText);
    } catch (e) {
        console.error('Failed to parse response:', e);
        return null;
    }
}

// Make available globally
window.ValidationUtils = {
    isValidYouTubeUrl,
    isAuthenticated,
    parseXhrResponse
};
