# Bachata Buddy Modern Frontend - Requirements Document

## Introduction

This document defines the requirements for building a modern, production-ready React frontend for Bachata Buddy - an AI-powered bachata choreography generator. The frontend will provide an intuitive, accessible interface for generating custom dance choreographies through two methods: song selection and natural language AI description. The application emphasizes simplicity, performance, and an exceptional user experience while maintaining minimal dependencies.

## Glossary

- **Frontend Application**: The React-based web interface that users interact with
- **Backend API**: The Django REST API that handles all business logic and data processing
- **JWT Token**: JSON Web Token used for user authentication
- **Task**: An asynchronous choreography generation job tracked by task_id
- **Blueprint**: JSON document containing complete video assembly instructions
- **Loop Segment**: A portion of video marked for repeated playback practice
- **Collection**: User's personal library of saved choreographies
- **Path 1**: Song selection method - user selects pre-existing song
- **Path 2**: AI description method - user describes choreography in natural language
- **Progress Polling**: Repeatedly checking server for task status updates
- **Toast Notification**: Temporary message that appears and auto-dismisses

## Requirements

### Requirement 1: Authentication System

**User Story:** As a user, I want to securely log in and register so that I can access the choreography generation features and save my work.

#### Acceptance Criteria

1. WHEN a user navigates to the login page, THE Frontend Application SHALL display a centered login form with username and password fields
2. WHEN a user submits valid credentials, THE Frontend Application SHALL store the JWT access token in localStorage and redirect to the home page
3. WHEN a user submits invalid credentials, THE Frontend Application SHALL display a clear error message without exposing technical details
4. WHEN a user's access token expires, THE Frontend Application SHALL automatically refresh the token using the refresh token
5. IF the refresh token is invalid or expired, THEN THE Frontend Application SHALL redirect the user to the login page
6. WHEN a user navigates to the registration page, THE Frontend Application SHALL display a form with username, email, password, and confirm password fields
7. WHEN a user successfully registers, THE Frontend Application SHALL automatically log them in and redirect to the home page
8. WHEN a user clicks logout, THE Frontend Application SHALL clear all stored tokens and redirect to the login page

### Requirement 2: Navigation System

**User Story:** As a user, I want a clear, persistent navigation menu so that I can easily access all features of the application.

#### Acceptance Criteria

1. THE Frontend Application SHALL display a sticky navigation bar at the top of all pages
2. THE Frontend Application SHALL display the Bachata Buddy logo on the left side of the navigation bar
3. WHEN a user is authenticated, THE Frontend Application SHALL display navigation links for "Generate", "My Collections", and "Browse Songs"
4. WHEN a user clicks "Generate", THE Frontend Application SHALL display a dropdown menu with "Select Song" and "Describe Choreo" options
5. WHEN a user is authenticated, THE Frontend Application SHALL display a user menu on the right side with avatar/initials and dropdown options for Profile, Preferences, and Logout
6. WHEN a user is not authenticated, THE Frontend Application SHALL display "Login" and "Sign Up" buttons on the right side
7. WHEN the viewport width is less than 768px, THE Frontend Application SHALL display a hamburger menu icon that expands to show all navigation options
8. THE Frontend Application SHALL highlight the currently active page in the navigation menu

### Requirement 3: Song Selection Generation (Path 1)

**User Story:** As a user, I want to generate choreography by selecting a song from the database so that I can create routines for specific music I like.

#### Acceptance Criteria

1. WHEN a user navigates to the Select Song page, THE Frontend Application SHALL display a searchable list of available songs
2. THE Frontend Application SHALL allow users to filter songs by genre and BPM range
3. THE Frontend Application SHALL display song cards showing title, artist, BPM, and duration
4. WHEN a user clicks on a song card, THE Frontend Application SHALL navigate to the generation parameters form
5. THE Frontend Application SHALL display the selected song details and parameter selection form with difficulty, energy level, and style options
6. WHEN a user submits the generation form with valid parameters, THE Frontend Application SHALL call POST /api/choreography/generate-from-song/ and receive a task_id
7. THE Frontend Application SHALL navigate to the progress tracking view and begin polling GET /api/choreography/tasks/{task_id}/ every 2 seconds
8. WHEN the task status is "completed", THE Frontend Application SHALL display the video player with the generated choreography
9. IF the task status is "failed", THEN THE Frontend Application SHALL display the error message and provide a retry option

### Requirement 4: AI Natural Language Generation (Path 2)

**User Story:** As a user, I want to describe my desired choreography in natural language so that I can generate routines without knowing technical dance terminology.

#### Acceptance Criteria

1. WHEN a user navigates to the Describe Choreo page, THE Frontend Application SHALL display a large text area for natural language input
2. THE Frontend Application SHALL display example queries that users can click to auto-populate the text area
3. THE Frontend Application SHALL display a character counter showing current length out of 500 maximum characters
4. WHEN a user enters less than 10 characters, THE Frontend Application SHALL disable the submit button and show validation message
5. WHEN a user submits a valid query, THE Frontend Application SHALL call POST /api/choreography/generate-with-ai/ and receive task_id and parsed_parameters
6. THE Frontend Application SHALL display the AI-parsed parameters (difficulty, energy_level, style, selected song) for user review
7. THE Frontend Application SHALL navigate to the progress tracking view and begin polling for task status
8. WHEN the task completes, THE Frontend Application SHALL display the video player with the generated choreography
9. IF query parsing fails, THEN THE Frontend Application SHALL display error message with alternative query suggestions

### Requirement 5: Progress Tracking

**User Story:** As a user, I want to see real-time progress of my choreography generation so that I know the system is working and how long to wait.

#### Acceptance Criteria

1. WHEN choreography generation starts, THE Frontend Application SHALL display an animated progress bar showing 0-100% completion
2. THE Frontend Application SHALL poll GET /api/choreography/tasks/{task_id}/ every 2-3 seconds while status is "pending" or "running"
3. THE Frontend Application SHALL display the current stage message from the API (e.g., "Analyzing audio...", "Assembling video...")
4. THE Frontend Application SHALL display stage-specific emoji indicators that change based on the current stage
5. THE Frontend Application SHALL update the progress bar smoothly without jarring jumps
6. WHEN the user navigates away from the progress page, THE Frontend Application SHALL continue polling in the background
7. IF the user returns to the application, THE Frontend Application SHALL resume displaying progress for any in-progress tasks
8. THE Frontend Application SHALL provide a "Cancel Generation" button that calls DELETE /api/choreography/tasks/{task_id}/
9. IF polling continues for more than 5 minutes, THEN THE Frontend Application SHALL display a timeout error message
10. THE Frontend Application SHALL stop polling when status is "completed" or "failed"

### Requirement 6: Video Player with Loop Controls

**User Story:** As a user, I want to watch my generated choreography and practice specific sections repeatedly so that I can learn the moves effectively.

#### Acceptance Criteria

1. WHEN a choreography generation completes, THE Frontend Application SHALL display an HTML5 video player with the generated video
2. THE Frontend Application SHALL display standard playback controls including play/pause, seek bar, volume, and fullscreen
3. THE Frontend Application SHALL display current time and total duration in MM:SS format
4. THE Frontend Application SHALL provide a "Loop Controls" section below the video player
5. WHEN a user clicks "Enable Loop", THE Frontend Application SHALL create a 10-second loop segment centered on the current playback position
6. THE Frontend Application SHALL display loop start and loop end times with +1s and -1s adjustment buttons
7. WHEN loop is enabled, THE Frontend Application SHALL display a green overlay on the progress bar showing the loop segment
8. WHEN the video reaches the loop end time, THE Frontend Application SHALL automatically jump back to the loop start time and continue playing
9. THE Frontend Application SHALL provide playback speed controls (0.5x, 0.75x, 1x, 1.25x, 1.5x)
10. THE Frontend Application SHALL support keyboard shortcuts: Space (play/pause), L (set loop start), K (set loop end), R (toggle loop), Arrow keys (seek ±5 seconds)
11. THE Frontend Application SHALL display a "Download" button that downloads the video file
12. THE Frontend Application SHALL be responsive and work on mobile devices with touch controls

### Requirement 7: Save to Collection

**User Story:** As a user, I want to save my generated choreographies to a personal collection so that I can access them later for practice.

#### Acceptance Criteria

1. WHEN a choreography generation completes, THE Frontend Application SHALL display a "Save to Collection" form below the video player
2. THE Frontend Application SHALL display a title input field pre-filled with an auto-generated title
3. THE Frontend Application SHALL display a difficulty dropdown pre-filled with the generation parameters
4. THE Frontend Application SHALL display an optional notes textarea
5. WHEN a user clicks "Save to Collection", THE Frontend Application SHALL call POST /api/collections/save/ with task_id, title, difficulty, and notes
6. WHEN the save succeeds, THE Frontend Application SHALL display a success toast notification
7. THE Frontend Application SHALL provide a "View in My Collections" link that navigates to the collections page
8. IF the save fails, THEN THE Frontend Application SHALL display an error toast with the specific error message
9. THE Frontend Application SHALL only display the save form to authenticated users

### Requirement 8: Collections Management

**User Story:** As a user, I want to view, search, filter, and manage my saved choreographies so that I can organize my practice routines.

#### Acceptance Criteria

1. WHEN a user navigates to My Collections, THE Frontend Application SHALL call GET /api/collections/ and display a list of saved choreographies
2. THE Frontend Application SHALL display each collection item as a card showing title, creation date, duration, difficulty, and number of moves
3. THE Frontend Application SHALL provide a search input that filters collections by title or song name in real-time
4. THE Frontend Application SHALL provide filter dropdowns for difficulty level (All, Beginner, Intermediate, Advanced)
5. THE Frontend Application SHALL provide sort options (Most Recent, Oldest First, Title A-Z, Duration)
6. WHEN a user clicks "Play" on a collection item, THE Frontend Application SHALL navigate to the video player page with that choreography
7. WHEN a user clicks "Edit" on a collection item, THE Frontend Application SHALL display a modal to update title, difficulty, and notes
8. WHEN a user clicks "Delete" on a collection item, THE Frontend Application SHALL display a confirmation dialog before calling DELETE /api/collections/{id}/
9. THE Frontend Application SHALL display collection statistics showing total count, total duration, and breakdown by difficulty
10. THE Frontend Application SHALL implement pagination loading 20 items per page
11. WHEN no collections exist, THE Frontend Application SHALL display an empty state with a "Generate Your First Choreography" button

### Requirement 9: Browse Songs

**User Story:** As a user, I want to browse all available songs in the database so that I can discover new music for choreography generation.

#### Acceptance Criteria

1. WHEN a user navigates to Browse Songs, THE Frontend Application SHALL call GET /api/choreography/songs/ and display a grid of song cards
2. THE Frontend Application SHALL display each song card showing title, artist, BPM, genre, and duration
3. THE Frontend Application SHALL provide a search input that filters songs by title or artist
4. THE Frontend Application SHALL provide filter dropdowns for genre and BPM range
5. THE Frontend Application SHALL provide sort options (Title, Artist, BPM, Date Added)
6. WHEN a user clicks "Generate with this song" on a song card, THE Frontend Application SHALL navigate to the generation parameters form with that song pre-selected
7. THE Frontend Application SHALL implement pagination loading 20 songs per page
8. THE Frontend Application SHALL display skeleton loaders while fetching songs

### Requirement 10: User Profile and Preferences

**User Story:** As a user, I want to view and update my profile information and preferences so that I can customize my experience.

#### Acceptance Criteria

1. WHEN a user navigates to Profile, THE Frontend Application SHALL call GET /api/auth/me/ and display username, email, and account statistics
2. THE Frontend Application SHALL provide a form to update username and email
3. THE Frontend Application SHALL provide a "Change Password" section with current password, new password, and confirm password fields
4. WHEN a user updates their profile, THE Frontend Application SHALL call PUT /api/auth/me/ and display a success message
5. WHEN a user navigates to Preferences, THE Frontend Application SHALL call GET /api/auth/preferences/ and display preference options
6. THE Frontend Application SHALL provide dropdowns for default difficulty level, default energy level, and default style
7. WHEN a user updates preferences, THE Frontend Application SHALL call PUT /api/auth/preferences/ and display a success message
8. THE Frontend Application SHALL provide a "Delete Account" button that displays a confirmation dialog with password verification

### Requirement 11: Error Handling and User Feedback

**User Story:** As a user, I want clear, helpful error messages and feedback so that I understand what went wrong and how to fix it.

#### Acceptance Criteria

1. WHEN a network error occurs, THE Frontend Application SHALL display a user-friendly message: "Failed to connect to server. Please check your internet connection."
2. WHEN a 401 Unauthorized response is received, THE Frontend Application SHALL attempt to refresh the access token
3. IF token refresh fails, THEN THE Frontend Application SHALL redirect to the login page with a message: "Your session has expired. Please log in again."
4. WHEN a 400 Bad Request response is received, THE Frontend Application SHALL display the specific validation errors from the API
5. WHEN a 500 Internal Server Error occurs, THE Frontend Application SHALL display: "Something went wrong. Our team has been notified. Please try again later."
6. THE Frontend Application SHALL display toast notifications for success, error, warning, and info messages
7. THE Frontend Application SHALL auto-dismiss toast notifications after 3 seconds
8. THE Frontend Application SHALL allow users to manually dismiss toast notifications by clicking an X button
9. THE Frontend Application SHALL implement retry logic for transient network failures (maximum 3 attempts with exponential backoff)
10. THE Frontend Application SHALL display loading spinners or skeleton screens during data fetching

### Requirement 12: Responsive Design

**User Story:** As a user, I want the application to work seamlessly on my mobile device, tablet, and desktop so that I can practice anywhere.

#### Acceptance Criteria

1. THE Frontend Application SHALL implement a mobile-first responsive design using Tailwind CSS breakpoints
2. WHEN viewport width is less than 768px, THE Frontend Application SHALL display a hamburger menu for navigation
3. WHEN viewport width is less than 768px, THE Frontend Application SHALL stack form elements vertically
4. WHEN viewport width is less than 768px, THE Frontend Application SHALL display full-width video player
5. THE Frontend Application SHALL ensure all touch targets are minimum 44x44 pixels on mobile devices
6. THE Frontend Application SHALL support both portrait and landscape orientations on mobile devices
7. THE Frontend Application SHALL scale video player responsively while maintaining aspect ratio
8. THE Frontend Application SHALL ensure text remains readable at all viewport sizes (minimum 14px font size)
9. THE Frontend Application SHALL test and support iOS Safari 14+, Chrome Mobile 90+, and modern desktop browsers

### Requirement 13: Accessibility

**User Story:** As a user with disabilities, I want the application to be fully accessible so that I can use all features regardless of my abilities.

#### Acceptance Criteria

1. THE Frontend Application SHALL achieve WCAG 2.1 Level AA compliance
2. THE Frontend Application SHALL support full keyboard navigation with visible focus indicators
3. THE Frontend Application SHALL provide proper ARIA labels for all interactive elements
4. THE Frontend Application SHALL ensure color contrast ratio of at least 4.5:1 for all text
5. THE Frontend Application SHALL provide alt text for all images and icons
6. THE Frontend Application SHALL announce dynamic content changes to screen readers
7. THE Frontend Application SHALL support browser zoom up to 200% without breaking layout
8. THE Frontend Application SHALL use semantic HTML elements (nav, main, article, section, etc.)
9. THE Frontend Application SHALL provide skip navigation links for keyboard users
10. THE Frontend Application SHALL ensure form inputs have associated labels

### Requirement 14: Performance

**User Story:** As a user, I want the application to load quickly and respond instantly so that I have a smooth, frustration-free experience.

#### Acceptance Criteria

1. THE Frontend Application SHALL achieve initial page load time of less than 2 seconds on 3G connection
2. THE Frontend Application SHALL achieve Time to Interactive of less than 3 seconds
3. THE Frontend Application SHALL display loading states within 100ms of user interaction
4. THE Frontend Application SHALL implement code splitting to reduce initial bundle size
5. THE Frontend Application SHALL lazy load images and videos
6. THE Frontend Application SHALL cache API responses appropriately (songs list for 5 minutes, user profile for session duration)
7. THE Frontend Application SHALL achieve Lighthouse performance score of 90 or higher
8. THE Frontend Application SHALL maintain 60 FPS during animations and transitions
9. THE Frontend Application SHALL optimize video player for smooth playback with minimal buffering
10. THE Frontend Application SHALL implement service worker for offline capability (future enhancement)

### Requirement 15: Security

**User Story:** As a user, I want my data and credentials to be secure so that I can trust the application with my personal information.

#### Acceptance Criteria

1. THE Frontend Application SHALL store JWT access tokens in localStorage with appropriate security considerations
2. THE Frontend Application SHALL never log sensitive information (passwords, tokens) to the console in production
3. THE Frontend Application SHALL sanitize all user inputs to prevent XSS attacks
4. THE Frontend Application SHALL make all API calls over HTTPS in production
5. THE Frontend Application SHALL implement Content Security Policy headers
6. THE Frontend Application SHALL clear all stored credentials on logout
7. THE Frontend Application SHALL implement automatic token refresh before expiration
8. THE Frontend Application SHALL validate all form inputs on the client side before submission
9. THE Frontend Application SHALL display generic error messages that don't expose system internals
10. THE Frontend Application SHALL implement rate limiting on the client side for API calls (prevent abuse)

---

## Non-Functional Requirements

### NFR-1: Technology Stack

THE Frontend Application SHALL be built using:
- React 18.3.1 (JavaScript only, no TypeScript)
- React Router 6 for client-side routing
- Tailwind CSS for styling
- Vite as build tool and dev server
- Native Fetch API for HTTP requests (no Axios)
- Minimal additional dependencies

### NFR-2: Code Quality

THE Frontend Application SHALL maintain:
- ESLint configuration for code quality
- Consistent code formatting
- Component-based architecture
- Reusable utility functions
- Clear file and folder structure
- Inline code comments for complex logic

### NFR-3: Browser Compatibility

THE Frontend Application SHALL support:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- iOS Safari 14+
- Chrome Mobile 90+

### NFR-4: Deployment

THE Frontend Application SHALL:
- Build to static files for deployment
- Support environment-specific configuration via .env files
- Deploy to Google Cloud Run or similar static hosting
- Serve via CDN for global distribution
- Support custom domain configuration

### NFR-5: Maintainability

THE Frontend Application SHALL:
- Follow React best practices and conventions
- Implement clear separation of concerns (components, utils, pages)
- Use descriptive variable and function names
- Avoid premature optimization
- Keep components small and focused (< 200 lines)
- Document complex logic and business rules

---

## Out of Scope

The following features are explicitly out of scope for this initial implementation:

1. TypeScript - Application will use JavaScript only
2. Complex state management libraries (Redux, MobX) - Will use React Context API and local state
3. GraphQL - Will use REST API only
4. Server-side rendering - Will be a client-side SPA
5. Progressive Web App features - Future enhancement
6. Offline mode - Future enhancement
7. Real-time WebSocket updates - Will use polling
8. Social features (sharing, comments, likes) - Future enhancement
9. Instructor dashboard - Future enhancement
10. Multi-language support - Future enhancement
11. Voice input for AI queries - Future enhancement
12. Video editing capabilities - Future enhancement
13. Mobile native apps - Future enhancement
14. Payment/subscription features - Future enhancement
15. Analytics dashboard - Future enhancement

---

## Success Criteria

The Frontend Application will be considered successful when:

1. All 15 functional requirements are implemented and tested
2. WCAG 2.1 Level AA accessibility compliance is achieved
3. Lighthouse performance score is 90 or higher
4. All user flows can be completed without errors
5. Application works on all supported browsers and devices
6. API integration is complete and reliable
7. User feedback is positive (> 4.5/5 satisfaction score)
8. Error rate is less than 1% of all user interactions
9. Page load time is consistently under 2 seconds
10. Video playback is smooth with minimal buffering

---

## Dependencies

### External Dependencies

- Backend API must be running and accessible
- JWT authentication must be configured
- All API endpoints must be implemented and tested
- Video files must be accessible via URL
- CORS must be configured for frontend domain

### Technical Dependencies

- Node.js 18+ for development
- npm or yarn for package management
- Modern browser for testing
- Internet connection for API calls

---

## Assumptions

1. Backend API is fully functional and tested
2. Video files are in MP4 format (H.264/AAC codec)
3. Users have modern browsers with JavaScript enabled
4. Users have stable internet connection for video streaming
5. Backend handles all business logic and validation
6. Frontend is a "dumb" client that only renders UI and makes API calls
7. JWT tokens have reasonable expiration times (access: 15 min, refresh: 7 days)
8. Video files are reasonably sized (< 100MB)
9. Users understand basic web application concepts
10. Backend provides clear, actionable error messages

---

## Risks and Mitigations

### Risk 1: Video Playback Performance
**Impact:** High  
**Probability:** Medium  
**Mitigation:** Implement adaptive streaming, optimize video encoding, provide quality selection

### Risk 2: Token Expiration During Long Operations
**Impact:** Medium  
**Probability:** Low  
**Mitigation:** Implement automatic token refresh, handle 401 responses gracefully

### Risk 3: Browser Compatibility Issues
**Impact:** Medium  
**Probability:** Medium  
**Mitigation:** Test on all supported browsers, use polyfills where needed, provide fallbacks

### Risk 4: Network Failures During Polling
**Impact:** Medium  
**Probability:** Medium  
**Mitigation:** Implement retry logic, exponential backoff, clear error messages

### Risk 5: Mobile Performance
**Impact:** High  
**Probability:** Low  
**Mitigation:** Optimize bundle size, lazy load components, test on real devices

---

## Appendix A: API Endpoints Reference

### Authentication
- POST /api/auth/register/
- POST /api/auth/login/
- POST /api/auth/refresh/
- GET /api/auth/me/
- PUT /api/auth/me/
- GET /api/auth/preferences/
- PUT /api/auth/preferences/

### Choreography
- GET /api/choreography/songs/
- GET /api/choreography/songs/{id}/
- POST /api/choreography/generate-from-song/
- POST /api/choreography/generate-with-ai/
- POST /api/choreography/parse-query/
- GET /api/choreography/tasks/
- GET /api/choreography/tasks/{task_id}/
- DELETE /api/choreography/tasks/{task_id}/

### Collections
- GET /api/collections/
- POST /api/collections/save/
- GET /api/collections/{id}/
- PUT /api/collections/{id}/
- DELETE /api/collections/{id}/
- GET /api/collections/stats/

---

**Document Version:** 1.0  
**Last Updated:** November 10, 2025  
**Status:** ✅ Ready for Design Phase  
**Next Steps:** Create design document with component architecture and user flows
