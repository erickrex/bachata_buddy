/**
 * Choreography Generator Component
 * Main Alpine.js component for creating and managing dance choreographies
 */

function choreographyApp() {
    return {
        // Form state
        selectedSong: '',
        difficulty: 'intermediate',
        
        // Generation state
        isGenerating: false,
        currentTaskId: null,
        progress: 0,
        progressMessage: 'Starting...',
        currentStage: 'initializing',
        isCheckingProgress: false,
        
        // Results
        result: null,
        error: false,
        errorMessage: '',
        
        // Merge in shared mixins
        ...ChoreographyShared.videoPlayerMixin(),
        ...ChoreographyShared.saveMixin(),
        
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
            // Check if user is authenticated (server-side rendered or stored)
            const isAuthenticated = this.$root?.user?.isAuthenticated || 
                                   localStorage.getItem('auth_token') ||
                                   document.querySelector('meta[name="user-authenticated"]')?.content === 'true';
            
            if (!isAuthenticated) return false;
            
            return this.selectedSong !== '' && this.selectedSong !== null;
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
        
        // Notification wrapper (uses shared function)
        showNotification(message, type = 'info') {
            ChoreographyShared.showNotification(message, type);
        },
        
        showResult(resultData) {
            this.isGenerating = false;
            this.result = resultData;
            this.error = false;
            this.progress = 100;
            this.currentStage = 'completed';
            this.showNotification('🎉 Choreography generated successfully!', 'success');
        },
        
        resetForm() {
            Object.assign(this, {
                selectedSong: '', difficulty: 'intermediate',
                isGenerating: false, result: null, error: false, progress: 0,
                progressMessage: 'Starting...', currentStage: 'initializing',
                currentTaskId: null, isCheckingProgress: false,
                // Reset video state
                videoDuration: 0, currentTime: 0, progressPercentage: 0,
                isPlaying: false, isLooping: false, loopStart: -1, loopEnd: -1,
                // Reset save state
                saveTitle: '', saveDifficulty: 'intermediate', isSaving: false, saveSuccess: false
            });
        }
    }
}

// Make available globally for Alpine.js
window.choreographyApp = choreographyApp;
