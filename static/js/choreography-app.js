/**
 * Choreography Generator Component
 * Main Alpine.js component for creating and managing dance choreographies
 */

function choreographyApp() {
    return {
        // Form state
        selectedSong: '',
        youtubeUrl: '',
        difficulty: 'intermediate',
        
        // Generation state
        isGenerating: false,
        currentTaskId: null,
        progress: 0,
        progressMessage: 'Starting...',
        currentStage: 'initializing',
        isCheckingProgress: false,
        
        // Save state
        isSaving: false,
        
        // Results
        result: null,
        error: false,
        errorMessage: '',
         
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
        
        // Initialize component
        init() {
            this.resumeTaskIfExists();
            // Watch for auth changes if $root is available
            if (this.$root?.user) {
                this.$watch('$root.user.isAuthenticated', (isAuth) => {
                    if (!isAuth && this.isGenerating) this.clearTaskId();
                });
            }
        },
        
        // Resume existing task
        async resumeTaskIfExists() {
            const taskId = localStorage.getItem('currentTaskId');
            const isAuthenticated = this.$root?.user?.isAuthenticated || localStorage.getItem('auth_token');
            
            if (taskId && isAuthenticated) {
                try {
                    const response = await fetch(`/api/task/${taskId}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.status === 'running' || data.status === 'started') {
                            this.currentTaskId = taskId;
                            this.isGenerating = true;
                            this.updateProgressFromData(data);
                            this.startPolling();
                        } else {
                            localStorage.removeItem('currentTaskId');
                        }
                    } else {
                        localStorage.removeItem('currentTaskId');
                    }
                } catch (e) {
                    localStorage.removeItem('currentTaskId');
                }
            } else if (taskId && !isAuthenticated) {
                localStorage.removeItem('currentTaskId');
            }
        },
        
        // Form validation
        canGenerate() {
            const isAuthenticated = this.$root?.user?.isAuthenticated || localStorage.getItem('auth_token');
            if (!isAuthenticated) return false;
            if (this.selectedSong === 'new_song') {
                return this.youtubeUrl.trim() && this.isValidYouTubeUrl(this.youtubeUrl);
            }
            return this.selectedSong !== '';
        },
        
        isValidYouTubeUrl(url) {
            return window.ValidationUtils?.isValidYouTubeUrl(url) || 
                   /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)[a-zA-Z0-9_-]{11}/.test(url);
        },
        
        toggleYouTubeInput() {
            if (this.selectedSong !== 'new_song') this.youtubeUrl = '';
        },
        
        updateHiddenField() {
            const field = document.querySelector('#hidden_youtube_url');
            if (field) field.value = this.getYoutubeUrl();
        },
        
        prepareFormSubmission() {
            this.updateHiddenField();
        },
        
        getYoutubeUrl() {
            return this.selectedSong === 'new_song' ? this.youtubeUrl : this.selectedSong;
        },
        
        getStageEmoji() {
            return window.HelperUtils?.getStageEmoji(this.currentStage) || '⏳';
        },
        
        // Generation flow
        startGeneration() {
            this.isGenerating = true;
            this.result = null;
            this.error = false;
            this.progress = 5;
            this.progressMessage = 'Starting generation...';
            this.currentStage = 'initializing';
            this.currentTaskId = null;
        },
        
        handleGenerationResponse(event) {
            const xhr = event.detail.xhr;
            
            if (xhr.status === 0) {
                this.handleError('Failed to connect to server. Please try again.');
                return;
            }
            
            // Handle successful response
            if (xhr.status === 200) {
                try {
                    // Try multiple ways to get the response
                    let responseText = xhr.responseText || xhr.response;
                    if (typeof responseText === 'object') {
                        // Already parsed
                        const data = responseText;
                        this.currentTaskId = data.task_id;
                        localStorage.setItem('currentTaskId', data.task_id);
                        this.progress = 10;
                        this.progressMessage = 'Generation started, analyzing music...';
                        this.currentStage = 'downloading';
                        this.startPolling();
                    } else {
                        // Need to parse
                        const data = JSON.parse(responseText);
                        this.currentTaskId = data.task_id;
                        localStorage.setItem('currentTaskId', data.task_id);
                        this.progress = 10;
                        this.progressMessage = 'Generation started, analyzing music...';
                        this.currentStage = 'downloading';
                        this.startPolling();
                    }
                } catch (e) {
                    console.error('Failed to process server response:', e);
                    this.handleError('Failed to process server response. Please try again.');
                }
            } else if (xhr.status === 401) {
                this.handleError('🔐 Login Required: Please sign in to generate choreographies.');
                setTimeout(() => {
                    if (this.$root?.showLogin !== undefined) this.$root.showLogin = true;
                }, 1500);
            } else {
                try {
                    const data = JSON.parse(xhr.responseText || xhr.response);
                    this.handleError(data.message || data.detail || 'Generation failed');
                } catch (e) {
                    this.handleError(`Server error (${xhr.status}). Please try again.`);
                }
            }
        },
        
        // Simplified polling - HTMX + backup
        startPolling() {
            // Check if user is authenticated - handle case where $root might not be available
            const isAuthenticated = this.$root?.user?.isAuthenticated || localStorage.getItem('auth_token');
            
            if (this.currentTaskId && isAuthenticated) {
                const element = this.$refs.progressPollingElement;
                if (element) {
                    element.setAttribute('hx-get', `/api/task/${this.currentTaskId}`);
                    element.setAttribute('hx-trigger', 'every 2s');
                    element.setAttribute('hx-target', 'this');
                    element.setAttribute('hx-swap', 'none');
                    htmx.process(element);
                }
                this.pollBackup();
            }
        },
        
        async pollBackup() {
            const isAuthenticated = this.$root?.user?.isAuthenticated || localStorage.getItem('auth_token');
            if (!this.currentTaskId || !this.isGenerating || !isAuthenticated) return;
            
            try {
                const response = await fetch(`/api/task/${this.currentTaskId}`);
                if (response.status === 404) {
                    this.clearTaskId();
                    return;
                }
                
                const data = await response.json();
                this.updateProgressFromData(data);
                
                if (data.status === 'running' || data.status === 'started') {
                    setTimeout(() => this.pollBackup(), 2000);
                }
            } catch (error) {
                setTimeout(() => this.pollBackup(), 3000);
            }
        },
        
        handleProgressUpdate(event) {
            if (event.detail.xhr.status === 200) {
                try {
                    const data = JSON.parse(event.detail.xhr.responseText || event.detail.xhr.response);
                    this.updateProgressFromData(data);
                } catch (e) {
                    console.error('Failed to parse progress response:', e);
                }
            } else if (event.detail.xhr.status === 404) {
                this.clearTaskId();
            }
        },
        
        updateProgressFromData(data) {
            this.progress = data.progress || 0;
            this.progressMessage = data.message || 'Processing...';
            this.currentStage = data.stage || 'processing';
            
            if (data.status === 'completed') {
                this.showResult(data.result);
                this.clearTaskId();
            } else if (data.status === 'failed') {
                this.handleError(data.error || 'Generation failed');
                this.clearTaskId();
            }
        },
        
        clearTaskId() {
            this.currentTaskId = null;
            this.isGenerating = false;
            localStorage.removeItem('currentTaskId');
            this.stopPolling();
        },
        
        stopPolling() {
            const element = this.$refs.progressPollingElement;
            if (element) {
                ['hx-get', 'hx-trigger', 'hx-target', 'hx-swap'].forEach(attr => 
                    element.removeAttribute(attr));
            }
        },
        
        async manualProgressCheck() {
            const isAuthenticated = this.$root?.user?.isAuthenticated || localStorage.getItem('auth_token');
            if (!this.currentTaskId || !isAuthenticated) return;
            
            this.isCheckingProgress = true;
            try {
                const response = await fetch(`/api/task/${this.currentTaskId}`);
                if (response.status === 404) {
                    this.clearTaskId();
                    if (this.$root?.showNotification) {
                        this.$root.showNotification('Task no longer exists', 'warning');
                    }
                } else {
                    const data = await response.json();
                    this.updateProgressFromData(data);
                }
            } catch (error) {
                if (this.$root?.showNotification) {
                    this.$root.showNotification('Failed to check progress', 'error');
                }
            } finally {
                this.isCheckingProgress = false;
            }
        },
        
        handleError(message) {
            this.isGenerating = false;
            this.error = true;
            this.errorMessage = message;
            this.currentStage = 'failed';
            // Safely call showNotification if available
            if (this.$root?.showNotification) {
                this.$root.showNotification(message, 'error');
            } else {
                console.error('Error:', message);
            }
        },
        
        // Save functionality
        startSaving() {
            this.isSaving = true;
        },
        
        handleSaveResponse(event) {
            this.isSaving = false;
            if (event.detail.xhr.status === 200) {
                if (this.$root?.showNotification) {
                    this.$root.showNotification('💾 Choreography saved to your collection!', 'success');
                }
            } else {
                try {
                    const errorData = JSON.parse(event.detail.xhr.responseText || event.detail.xhr.response);
                    if (this.$root?.showNotification) {
                        this.$root.showNotification(errorData.message || 'Failed to save choreography', 'error');
                    }
                } catch (e) {
                    if (this.$root?.showNotification) {
                        this.$root.showNotification('Failed to save choreography', 'error');
                    }
                }
            }
        },
        
        showResult(resultData) {
            this.isGenerating = false;
            this.result = resultData;
            this.error = false;
            this.progress = 100;
            this.currentStage = 'completed';
            if (this.$root?.showNotification) {
                this.$root.showNotification('🎉 Choreography generated successfully!', 'success');
            }
        },
        
        // VIDEO PLAYER FUNCTIONS
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

        // LOOP FUNCTIONALITY
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
            return window.HelperUtils?.formatTime(seconds) || '0:00';
        },
        
        resetForm() {
            Object.assign(this, {
                selectedSong: '', youtubeUrl: '', difficulty: 'intermediate',
                isGenerating: false, result: null, error: false, progress: 0,
                progressMessage: 'Starting...', currentStage: 'initializing',
                currentTaskId: null, isSaving: false, isCheckingProgress: false,
                // Reset video state
                videoDuration: 0, currentTime: 0, progressPercentage: 0,
                isPlaying: false, isLooping: false, loopStart: -1, loopEnd: -1
            });
        }
    }
}

// Make available globally for Alpine.js
window.choreographyApp = choreographyApp;
