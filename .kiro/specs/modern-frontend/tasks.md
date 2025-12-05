# Bachata Buddy Modern Frontend - Implementation Tasks

This document outlines the implementation tasks for building the Bachata Buddy frontend application. Tasks are organized in a logical sequence that builds incrementally, with each task referencing specific requirements from the requirements document.

---

## Task List

- [x] 1. Project Setup and Configuration
- [x] 1.1 Initialize project structure with Vite and React 18.3.1
  - Create directory structure (components, pages, utils, contexts, hooks)
  - Configure Vite with React plugin
  - Set up Tailwind CSS with custom configuration
  - Create .env.example with required environment variables
  - _Requirements: NFR-1_

- [x] 1.2 Configure routing with React Router 6
  - Install react-router-dom
  - Create App.jsx with BrowserRouter and Routes
  - Set up route structure for all pages
  - Implement ProtectedRoute wrapper component
  - _Requirements: Requirement 2_

- [ ]* 1.3 Set up ESLint and code quality tools
  - Configure ESLint for React
  - Add lint script to package.json
  - Create .gitignore with appropriate entries
  - _Requirements: NFR-2_

- [x] 2. Core Utilities and Helpers
- [x] 2.1 Create API client utility (utils/api.js)
  - Implement base apiClient function with fetch
  - Add automatic JWT token injection
  - Implement token refresh logic on 401 responses
  - Add timeout handling and retry logic
  - Export API methods for all endpoints (auth, songs, generation, collections)
  - _Requirements: Requirement 1, Requirement 15_

- [x] 2.2 Create formatting utilities (utils/format.js)
  - Implement formatTime (seconds to MM:SS)
  - Implement formatDuration (seconds to HH:MM:SS)
  - Implement formatDate (ISO string to readable date)
  - Implement formatFileSize (bytes to KB/MB/GB)
  - Implement capitalize helper
  - _Requirements: Requirement 6, Requirement 8_

- [x] 2.3 Create validation utilities (utils/validation.js)
  - Implement validateEmail
  - Implement validateUsername (3-30 chars, alphanumeric + underscore)
  - Implement validatePassword (minimum 8 chars)
  - Implement validateQuery (10-500 chars)
  - Implement getPasswordStrength
  - _Requirements: Requirement 1_

- [x] 3. Custom React Hooks
- [x] 3.1 Create useLocalStorage hook (hooks/useLocalStorage.js)
  - Implement state synchronization with localStorage
  - Handle JSON serialization/deserialization
  - Add error handling for storage failures
  - _Requirements: Requirement 1_

- [x] 3.2 Create useDebounce hook (hooks/useDebounce.js)
  - Implement debounce logic with configurable delay
  - Use for search input optimization
  - _Requirements: Requirement 3, Requirement 8, Requirement 14_

- [x] 3.3 Create usePolling hook (hooks/usePolling.js)
  - Implement interval-based polling
  - Add automatic stop on completion/failure
  - Handle cleanup on unmount
  - _Requirements: Requirement 5_

- [x] 3.4 Create useAuth hook (hooks/useAuth.js)
  - Export AuthContext consumer
  - Provide type-safe access to auth state
  - _Requirements: Requirement 1_

- [x] 4. Authentication System
- [x] 4.1 Create AuthContext provider (contexts/AuthContext.jsx)
  - Implement authentication state management
  - Create login method (calls API, stores tokens)
  - Create register method (calls API, auto-login)
  - Create logout method (clears tokens, resets state)
  - Create refreshToken method (handles token refresh)
  - Implement automatic token refresh on mount
  - _Requirements: Requirement 1_

- [x] 4.2 Create Login page (pages/Login.jsx)
  - Build login form with username and password inputs
  - Add "Remember me" checkbox
  - Implement form validation
  - Handle login submission with loading state
  - Display error messages
  - Add link to registration page
  - Redirect to home on successful login
  - _Requirements: Requirement 1.1_

- [x] 4.3 Create Register page (pages/Register.jsx)
  - Build registration form (username, email, password, confirm password)
  - Add password strength indicator
  - Implement form validation
  - Handle registration submission
  - Auto-login after successful registration
  - Display error messages
  - _Requirements: Requirement 1.2_



- [x] 5. Common UI Components
- [x] 5.1 Create Button component (components/common/Button.jsx)
  - Implement variants (primary, secondary, danger, ghost)
  - Implement sizes (sm, md, lg)
  - Add disabled state styling
  - Add focus ring for accessibility
  - _Requirements: Requirement 13_

- [x] 5.2 Create Input component (components/common/Input.jsx)
  - Implement text input with label
  - Add error state and message display
  - Add focus ring styling
  - Ensure accessibility with proper labels
  - _Requirements: Requirement 13_

- [x] 5.3 Create Select component (components/common/Select.jsx)
  - Implement dropdown with label
  - Add options prop for select items
  - Add error state styling
  - Ensure keyboard navigation
  - _Requirements: Requirement 13_

- [x] 5.4 Create Card component (components/common/Card.jsx)
  - Implement base card styling with shadow and border
  - Add optional hover effect
  - Make responsive with proper padding
  - _Requirements: Requirement 12_

- [x] 5.5 Create Modal component (components/common/Modal.jsx)
  - Implement modal overlay with backdrop
  - Add focus trap for accessibility
  - Handle ESC key to close
  - Prevent body scroll when open
  - _Requirements: Requirement 13_

- [x] 5.6 Create Spinner component (components/common/Spinner.jsx)
  - Implement loading spinner with animation
  - Add size variants
  - Add ARIA label for screen readers
  - _Requirements: Requirement 11, Requirement 13_

- [x] 6. Toast Notification System
- [x] 6.1 Create ToastContext provider (contexts/ToastContext.jsx)
  - Implement toast state management
  - Create addToast method with auto-dismiss
  - Create removeToast method
  - Position toasts in top-right corner
  - _Requirements: Requirement 11_

- [x] 6.2 Create Toast component (components/common/Toast.jsx)
  - Implement toast with type-based styling (success, error, warning, info)
  - Add slide-in animation
  - Add close button
  - Auto-dismiss after 3 seconds
  - _Requirements: Requirement 11_

- [x] 7. Layout Components
- [x] 7.1 Create Navbar component (components/layout/Navbar.jsx)
  - Implement sticky navigation bar
  - Add logo on left side
  - Add navigation links (Generate dropdown, My Collections, Browse Songs)
  - Add user menu with avatar/initials (Profile, Preferences, Logout)
  - Show Login/Sign Up buttons for anonymous users
  - Implement hamburger menu for mobile
  - Highlight active page
  - _Requirements: Requirement 2_

- [x] 7.2 Create Container component (components/layout/Container.jsx)
  - Implement max-width container with responsive padding
  - Center content horizontally
  - _Requirements: Requirement 12_

- [ ]* 7.3 Create Footer component (components/layout/Footer.jsx)
  - Add copyright and links
  - Make responsive
  - _Requirements: Requirement 12_

- [x] 8. Song Selection (Path 1)
- [x] 8.1 Create SongCard component (components/generation/SongCard.jsx)
  - Display song title, artist, BPM, duration
  - Add "Select" button
  - Implement hover effect
  - Make responsive
  - _Requirements: Requirement 3.1_

- [x] 8.2 Create SelectSong page (pages/SelectSong.jsx)
  - Implement song list loading from API
  - Add search input with debounce
  - Add genre filter dropdown
  - Add BPM range filter
  - Add sort dropdown (title, artist, BPM)
  - Implement pagination (20 songs per page)
  - Display skeleton loaders while fetching
  - Show empty state when no songs match
  - _Requirements: Requirement 3.1_

- [x] 8.3 Create ParameterForm component (components/generation/ParameterForm.jsx)
  - Display selected song details
  - Add difficulty radio buttons (beginner, intermediate, advanced) - required
  - Add energy level radio buttons (low, medium, high) - default: medium
  - Add style dropdown (romantic, energetic, sensual, playful, modern) - default: modern
  - Add "Change Song" button
  - Add "Generate Choreography" button (disabled until valid)
  - Implement form validation
  - _Requirements: Requirement 3.2_

- [x] 8.4 Integrate parameter form into SelectSong page
  - Show parameter form when song is selected
  - Handle form submission
  - Call POST /api/choreography/generate-from-song/
  - Navigate to Progress page with task_id
  - _Requirements: Requirement 3.2_

- [x] 9. AI Description (Path 2)
- [x] 9.1 Create QueryInput component (components/generation/QueryInput.jsx)
  - Implement large auto-resizing textarea
  - Add character counter (current/500 max)
  - Display example queries (clickable to auto-populate)
  - Add validation (minimum 10 characters)
  - Disable submit button when invalid
  - _Requirements: Requirement 4.1_

- [ ]* 9.2 Create ParameterPreview component (components/generation/ParameterPreview.jsx)
  - Display original query in gray box
  - Show parsed parameters in grid (difficulty, energy, style, song)
  - Add "Edit Query" button
  - Add "Confirm & Generate" button
  - _Requirements: Requirement 4.2_

- [x] 9.3 Create DescribeChoreo page (pages/DescribeChoreo.jsx)
  - Implement query input view
  - Add optional "Preview Parameters" button
  - Call POST /api/choreography/parse-query/ for preview
  - Show parameter preview modal
  - Call POST /api/choreography/generate-with-ai/ on confirm
  - Navigate to Progress page with task_id
  - Handle errors with suggestions
  - _Requirements: Requirement 4_

- [x] 10. Progress Tracking
- [x] 10.1 Create ProgressTracker component (components/generation/ProgressTracker.jsx)
  - Display animated progress bar (0-100%)
  - Show stage-specific emoji indicators
  - Display current stage message
  - Show task ID
  - Add "Cancel Generation" button
  - Implement smooth progress bar animation
  - _Requirements: Requirement 5.1_

- [x] 10.2 Create Progress page (pages/Progress.jsx)
  - Get task_id from URL params
  - Implement polling with usePolling hook
  - Call GET /api/choreography/tasks/:taskId/ every 2 seconds
  - Update progress state from API response
  - Navigate to VideoResult page when status is "completed"
  - Display error when status is "failed"
  - Implement 5-minute timeout
  - Handle "Cancel" button click (DELETE /api/choreography/tasks/:taskId/)
  - Continue polling in background if user navigates away
  - _Requirements: Requirement 5_



- [x] 11. Video Player with Loop Controls
- [x] 11.1 Create ProgressBar component (components/video/ProgressBar.jsx)
  - Implement seekable progress bar
  - Show current position in blue
  - Show loop segment in green overlay (when loop enabled)
  - Handle click to seek
  - Display current time and duration
  - _Requirements: Requirement 6.1_

- [x] 11.2 Create LoopControls component (components/video/LoopControls.jsx)
  - Add "Enable/Disable Loop" toggle button
  - Show loop start time with -1s/+1s buttons
  - Show loop end time with -1s/+1s buttons
  - Display loop duration
  - Implement collapsible section
  - _Requirements: Requirement 6.1_

- [x] 11.3 Create VideoPlayer component (components/video/VideoPlayer.jsx)
  - Implement HTML5 video element
  - Add play/pause button
  - Add volume control
  - Add fullscreen toggle
  - Add playback speed selector (0.5x, 0.75x, 1x, 1.25x, 1.5x)
  - Integrate ProgressBar component
  - Integrate LoopControls component
  - Implement loop logic (jump back to loop start when reaching loop end)
  - Add keyboard shortcuts (Space, L, K, R, Arrow keys)
  - Add download button
  - Make responsive for mobile
  - _Requirements: Requirement 6_

- [x] 12. Save to Collection
- [x] 12.1 Create SaveModal component (components/collection/SaveModal.jsx)
  - Display modal with title input (pre-filled)
  - Add difficulty dropdown (pre-filled)
  - Add optional notes textarea
  - Add "Skip" and "Save to Collection" buttons
  - Handle form submission
  - Call POST /api/collections/save/
  - Show success toast on save
  - Close modal after save
  - _Requirements: Requirement 7_

- [x] 12.2 Create VideoResult page (pages/VideoResult.jsx)
  - Get task_id from URL params
  - Load task details from API
  - Display VideoPlayer component with video URL
  - Show SaveModal component
  - Add "Save to Collection" button
  - Handle save completion
  - Provide link to Collections page
  - _Requirements: Requirement 6, Requirement 7_

- [x] 13. Collections Management
- [x] 13.1 Create CollectionCard component (components/collection/CollectionCard.jsx)
  - Display title with emoji
  - Show creation date, duration, difficulty, number of moves
  - Show song title if available
  - Add difficulty badge
  - Add "Play", "Edit", "Delete" buttons
  - Implement hover effect
  - _Requirements: Requirement 8.1_

- [x] 13.2 Create CollectionFilters component (components/collection/CollectionFilters.jsx)
  - Add search input
  - Add difficulty filter dropdown (All, Beginner, Intermediate, Advanced)
  - Add sort dropdown (Recent, Oldest, Title, Duration)
  - Make responsive (stack vertically on mobile)
  - _Requirements: Requirement 8.1_

- [x] 13.3 Create Collections page (pages/Collections.jsx)
  - Load collections from GET /api/collections/
  - Load stats from GET /api/collections/stats/
  - Display CollectionFilters component
  - Display CollectionCard components in grid
  - Implement search with debounce
  - Implement filtering by difficulty
  - Implement sorting
  - Implement pagination (20 items per page)
  - Display statistics panel (total count, duration, breakdown)
  - Show empty state with CTA when no collections
  - Handle "Play" button (navigate to VideoResult)
  - Handle "Edit" button (show modal, call PUT /api/collections/:id/)
  - Handle "Delete" button (show confirmation, call DELETE /api/collections/:id/)
  - _Requirements: Requirement 8_

- [ ]* 14. Browse Songs
- [ ]* 14.1 Create BrowseSongs page (pages/BrowseSongs.jsx)
  - Load songs from GET /api/choreography/songs/
  - Display SongCard components in grid
  - Add search input with debounce
  - Add genre filter dropdown
  - Add BPM range filter
  - Add sort dropdown
  - Implement pagination
  - Add "Generate with this song" button on each card
  - Navigate to SelectSong with pre-selected song
  - _Requirements: Requirement 9_

- [ ]* 15. User Profile and Preferences
- [ ]* 15.1 Create Profile page (pages/Profile.jsx)
  - Load user data from GET /api/auth/me/
  - Display username and email
  - Show account statistics
  - Add edit form for username and email
  - Add change password section
  - Handle profile update (PUT /api/auth/me/)
  - Add "Delete Account" button with confirmation
  - _Requirements: Requirement 10.1_

- [ ]* 15.2 Create Preferences page (pages/Preferences.jsx)
  - Load preferences from GET /api/auth/preferences/
  - Add dropdown for default difficulty
  - Add dropdown for default energy level
  - Add dropdown for default style
  - Handle preferences update (PUT /api/auth/preferences/)
  - Add "Reset to Defaults" button
  - _Requirements: Requirement 10.2_

- [x] 16. Home Page
- [x] 16.1 Create Home page (pages/Home.jsx)
  - Display welcome message
  - Show feature highlights
  - Add CTA buttons for both generation paths
  - Show recent collections (if authenticated)
  - Make responsive
  - _Requirements: Requirement 2_

- [ ] 17. Error Handling and User Feedback
- [x] 17.1 Create ErrorBoundary component (components/ErrorBoundary.jsx)
  - Catch React errors
  - Display user-friendly error message
  - Add "Refresh Page" button
  - Log errors to console (production: send to monitoring)
  - _Requirements: Requirement 11_

- [x] 17.2 Integrate error handling in API client
  - Handle network errors with user-friendly messages
  - Implement automatic retry logic (max 3 attempts)
  - Handle 401 with token refresh
  - Handle 400 with validation error display
  - Handle 500 with generic error message
  - _Requirements: Requirement 11, Requirement 15_

- [x] 17.3 Add toast notifications throughout app
  - Success toasts for save operations
  - Error toasts for failed operations
  - Info toasts for background processes
  - Warning toasts for session expiration
  - _Requirements: Requirement 11_

- [x] 18. Responsive Design Implementation
- [x] 18.1 Implement mobile navigation
  - Create hamburger menu component
  - Add slide-in menu animation
  - Ensure all navigation items accessible
  - _Requirements: Requirement 12_

- [x] 18.2 Optimize layouts for mobile
  - Stack form elements vertically on mobile
  - Make video player full-width on mobile
  - Adjust card grids for mobile (1 column)
  - Ensure touch targets are 44x44px minimum
  - _Requirements: Requirement 12_

- [x] 18.3 Test on multiple devices
  - Test on iOS Safari 14+
  - Test on Chrome Mobile 90+
  - Test on tablets (768-1023px)
  - Test portrait and landscape orientations
  - _Requirements: Requirement 12_


- [ ]* 20. Performance Optimization
- [ ]* 20.1 Implement code splitting
  - Lazy load page components
  - Add Suspense with loading fallback
  - Split vendor chunks in build config
  - _Requirements: Requirement 14_

- [ ]* 20.2 Optimize images and assets
  - Add lazy loading to images
  - Compress images
  - Use appropriate image formats
  - _Requirements: Requirement 14_

- [ ]* 20.3 Implement caching strategy
  - Cache song list for 5 minutes
  - Cache user profile for session
  - Invalidate cache on mutations
  - _Requirements: Requirement 14_

- [ ]* 20.4 Add performance monitoring
  - Track page load times
  - Track API response times
  - Log performance metrics
  - _Requirements: Requirement 14_

- [x] 21. Security Implementation
- [x] 21.1 Implement XSS prevention
  - Sanitize user inputs
  - Use React's automatic escaping
  - Avoid dangerouslySetInnerHTML
  - _Requirements: Requirement 15_

- [x] 21.2 Add Content Security Policy
  - Configure CSP meta tag
  - Restrict script sources
  - Restrict style sources
  - _Requirements: Requirement 15_

- [x] 21.3 Secure token storage
  - Store tokens in localStorage with caution
  - Clear tokens on logout
  - Implement automatic token refresh
  - _Requirements: Requirement 15_

- [ ]* 22. Testing
- [ ]* 22.1 Write unit tests for utilities
  - Test format.js functions
  - Test validation.js functions
  - Test API client functions
  - _Requirements: NFR-2_

- [ ]* 22.2 Write component tests
  - Test Button component
  - Test Input component
  - Test Modal component
  - Test VideoPlayer component
  - _Requirements: NFR-2_

- [ ]* 22.3 Write integration tests
  - Test authentication flow
  - Test choreography generation flow
  - Test collection management flow
  - _Requirements: NFR-2_

- [x] 23. Deployment Configuration
- [x] 23.1 Create production Dockerfile
  - Multi-stage build with Node and nginx 
  - Aim for a Dockerfile to be deployed in Google Cloud Run (serverless)
  - Copy built files to nginx
  - Configure nginx for SPA routing
  - Add gzip compression
  - _Requirements: NFR-4_

- [x] 23.2 Configure environment variables
  - Create .env.example
  - Document all required variables
  - Set up production environment
  - _Requirements: NFR-4_

- [x] 23.3 Set up CI/CD pipeline
  - Configure build process
  - Run tests before deployment
  - Deploy to staging environment
  - Deploy to production after approval
  - _Requirements: NFR-4_

- [ ]* 24. Documentation
- [ ]* 24.1 Update README.md
  - Add project description
  - Document setup instructions
  - Add development workflow
  - Document deployment process
  - _Requirements: NFR-5_

- [ ]* 24.2 Add inline code comments
  - Document complex logic
  - Explain non-obvious decisions
  - Add JSDoc comments for functions
  - _Requirements: NFR-5_

- [ ] 25. Final Testing and Polish
- [ ] 25.1 Cross-browser testing
  - Test on Chrome 90+
  - Test on Firefox 88+
  - Test on Safari 14+
  - Test on Edge 90+
  - _Requirements: NFR-3_

- [ ] 25.2 User acceptance testing
  - Test all user flows end-to-end
  - Verify all requirements are met
  - Fix any bugs found
  - _Requirements: All requirements_

- [ ]* 25.3 Performance audit
  - Run Lighthouse audit
  - Achieve score of 90+
  - Fix any performance issues
  - _Requirements: Requirement 14_

- [ ]* 25.4 Accessibility audit
  - Run accessibility checker
  - Achieve WCAG 2.1 AA compliance
  - Fix any accessibility issues
  - _Requirements: Requirement 13_

---

## Implementation Notes

### Task Execution Order

Tasks should be executed in the order listed, as each task builds upon previous work:

1. **Phase 1 (Tasks 1-3):** Foundation - Project setup, utilities, hooks
2. **Phase 2 (Tasks 4-7):** Core Infrastructure - Auth, common components, layout
3. **Phase 3 (Tasks 8-10):** Generation Features - Both paths and progress tracking
4. **Phase 4 (Tasks 11-12):** Video Playback - Player and save functionality
5. **Phase 5 (Tasks 13-15):** Management Features - Collections, browse, profile
6. **Phase 6 (Tasks 16-21):** Polish - Error handling, responsive, accessibility, performance, security
7. **Phase 7 (Tasks 22-25):** Quality Assurance - Testing, deployment, documentation, final polish

### Development Guidelines

- Keep components small and focused (< 200 lines)
- Use functional components with hooks (no class components)
- Follow React best practices and conventions
- Write clean, readable code with descriptive names
- Test each component as you build it
- Commit frequently with clear messages
- Review requirements before starting each task

### Testing Strategy

- Write tests alongside implementation (not after)
- Focus on critical user flows first
- Test edge cases and error scenarios
- Ensure accessibility in all tests

### Deployment Strategy

- Deploy to staging after each phase
- Get user feedback before moving to next phase
- Deploy to production only after full testing
- Monitor errors and performance after deployment

---

**Total Tasks:** 25 main tasks with 80+ sub-tasks  
**Estimated Timeline:** 4-5 weeks for MVP (core features), 6-8 weeks for full implementation  
**Priority:** Tasks marked with * are optional for MVP and can be implemented later

**MVP Focus (4-5 weeks):**
- Core authentication and navigation
- Both choreography generation paths
- Video player with loop controls
- Collections management
- Responsive design and basic accessibility
- Error handling and deployment

**Optional Enhancements (post-MVP):**
- ESLint configuration
- Footer component
- Parameter preview for AI path
- Browse Songs page
- Profile and Preferences pages
- Advanced performance optimization
- Comprehensive testing suite
- Detailed documentation
- Performance and accessibility audits

