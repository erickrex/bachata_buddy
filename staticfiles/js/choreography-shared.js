/**
 * Shared functionality for choreography templates
 * Used by both select-song and describe-choreo templates
 */

window.ChoreographyShared = {
    /**
     * Format seconds to MM:SS format
     */
    formatTime(seconds) {
        if (!seconds || seconds < 0) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    },

    /**
     * Get emoji for generation stage
     */
    getStageEmoji(stage) {
        const emojis = {
            'initializing': '⏳',
            'downloading': '⬇️',
            'analyzing': '🎵',
            'selecting': '💃',
            'generating': '🎬',
            'explaining': '🤖',
            'finalizing': '✨',
            'completed': '🎉',
            'failed': '❌'
        };
        return emojis[stage] || '⏳';
    },

    /**
     * Show toast notification
     */
    showNotification(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg text-white font-semibold transition-all transform translate-x-0 ${
            type === 'success' ? 'bg-green-500' :
            type === 'error' ? 'bg-red-500' :
            type === 'warning' ? 'bg-yellow-500' :
            'bg-blue-500'
        }`;
        toast.textContent = message;
        toast.style.animation = 'slideIn 0.3s ease-out';
        
        document.body.appendChild(toast);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
        
        // Add CSS animations if not already present
        if (!document.getElementById('toast-animations')) {
            const style = document.createElement('style');
            style.id = 'toast-animations';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(400px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(400px); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    },

    /**
     * Video Player Mixin
     * Provides all video player functionality
     */
    videoPlayerMixin() {
        return {
            // Video player state
            videoDuration: 0,
            currentTime: 0,
            progressPercentage: 0,
            isPlaying: false,
            
            // Loop functionality
            isLooping: false,
            loopStart: -1,
            loopEnd: -1,
            
            // Computed properties for loop indicators
            get loopStartPercentage() {
                return this.videoDuration > 0 && this.loopStart >= 0 
                    ? (this.loopStart / this.videoDuration) * 100 : 0;
            },
            
            get loopSegmentWidth() {
                return this.videoDuration > 0 && this.loopStart >= 0 && this.loopEnd > this.loopStart 
                    ? ((this.loopEnd - this.loopStart) / this.videoDuration) * 100 : 0;
            },

            // Video control methods
            togglePlayPause() {
                const video = this.$refs.videoPlayer;
                if (!video) return;
                
                if (video.paused) {
                    if (this.isLooping && this.loopStart >= 0) {
                        video.currentTime = this.loopStart;
                    }
                    video.play();
                    this.isPlaying = true;
                } else {
                    video.pause();
                    this.isPlaying = false;
                }
            },

            seekTo(time) {
                const video = this.$refs.videoPlayer;
                if (video) video.currentTime = time;
            },

            initVideoPlayer() {
                const video = this.$refs.videoPlayer;
                if (video) {
                    this.videoDuration = video.duration;
                    this.currentTime = video.currentTime;
                    this.isPlaying = !video.paused;
                    this.updateVideoProgress();
                }
            },

            updateVideoProgress() {
                const video = this.$refs.videoPlayer;
                if (!video) return;
                
                this.currentTime = video.currentTime;
                this.progressPercentage = (video.currentTime / video.duration) * 100;
                this.isPlaying = !video.paused;
                
                // Loop check
                if (this.isLooping && this.loopEnd > 0 && video.currentTime >= this.loopEnd) {
                    video.currentTime = this.loopStart;
                }
            },

            handleVideoEnd() {
                this.isPlaying = false;
                if (this.isLooping && this.loopStart >= 0) {
                    const video = this.$refs.videoPlayer;
                    if (video) {
                        video.currentTime = this.loopStart;
                        video.play();
                    }
                }
            },

            seekToPosition(event) {
                const video = this.$refs.videoPlayer;
                if (!video || this.videoDuration <= 0) return;
                
                const rect = event.currentTarget.getBoundingClientRect();
                const percentage = (event.clientX - rect.left) / rect.width;
                const newTime = percentage * this.videoDuration;
                video.currentTime = newTime;
                
                // Auto-create 10-second segment if looping but no segment exists
                if (this.isLooping && (this.loopStart < 0 || this.loopEnd <= this.loopStart)) {
                    this.loopStart = Math.max(0, newTime - 5);
                    this.loopEnd = Math.min(this.videoDuration, newTime + 5);
                }
            },

            // Loop control methods
            toggleLoop() {
                this.isLooping = !this.isLooping;
                
                if (this.isLooping) {
                    this.selectCurrent10Seconds();
                    if (this.loopStart >= 0) {
                        const video = this.$refs.videoPlayer;
                        if (video) video.currentTime = this.loopStart;
                    }
                } else {
                    this.loopStart = -1;
                    this.loopEnd = -1;
                }
            },

            selectCurrent10Seconds() {
                const video = this.$refs.videoPlayer;
                if (video && this.videoDuration > 0) {
                    this.loopStart = Math.max(0, this.currentTime - 5);
                    this.loopEnd = Math.min(this.videoDuration, this.currentTime + 5);
                }
            },

            adjustLoopStart(seconds) {
                if (this.loopStart >= 0) {
                    this.loopStart = Math.max(0, Math.min(this.loopStart + seconds, this.loopEnd - 1));
                }
            },

            adjustLoopEnd(seconds) {
                if (this.loopEnd > 0) {
                    this.loopEnd = Math.min(this.videoDuration, Math.max(this.loopEnd + seconds, this.loopStart + 1));
                }
            },

            formatTime(seconds) {
                return ChoreographyShared.formatTime(seconds);
            }
        };
    },

    /**
     * Save Functionality Mixin
     * Provides save to collection functionality
     */
    saveMixin() {
        return {
            // Save form state
            saveTitle: '',
            saveDifficulty: 'intermediate',
            isSaving: false,
            saveSuccess: false,

            /**
             * Save choreography to collection
             * @param {Object} videoData - Video data including path, duration, etc.
             * @param {string} csrfToken - CSRF token for POST request
             * @param {string} saveUrl - URL to save endpoint
             */
            async saveToCollection(videoData, csrfToken, saveUrl) {
                if (!videoData || !videoData.video_path) {
                    ChoreographyShared.showNotification('No video to save', 'error');
                    return;
                }

                this.isSaving = true;
                this.saveSuccess = false;

                try {
                    const formData = new URLSearchParams({
                        'title': this.saveTitle || 'Untitled Choreography',
                        'difficulty': this.saveDifficulty,
                        'video_path': videoData.video_path,
                        'duration': videoData.duration || videoData.sequence_duration || 0,
                        'music_info': JSON.stringify(videoData.music_info || {}),
                        'generation_parameters': JSON.stringify(videoData.generation_parameters || {})
                    });

                    const response = await fetch(saveUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-CSRFToken': csrfToken
                        },
                        body: formData
                    });

                    const data = await response.json();

                    if (data.success) {
                        this.saveSuccess = true;
                        ChoreographyShared.showNotification('💾 Choreography saved to your collection!', 'success');
                        
                        // Reset success message after 3 seconds
                        setTimeout(() => {
                            this.saveSuccess = false;
                        }, 3000);
                    } else {
                        ChoreographyShared.showNotification(data.error || 'Failed to save choreography', 'error');
                    }
                } catch (err) {
                    console.error('Save error:', err);
                    ChoreographyShared.showNotification('Failed to save choreography. Please try again.', 'error');
                } finally {
                    this.isSaving = false;
                }
            }
        };
    }
};

// Make helper functions globally available for backward compatibility
window.HelperUtils = {
    formatTime: ChoreographyShared.formatTime,
    getStageEmoji: ChoreographyShared.getStageEmoji
};
