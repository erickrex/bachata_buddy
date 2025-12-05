# Bachata Buddy Modern Frontend - Design Document

## Overview

This document outlines the technical design for the Bachata Buddy frontend - a React 18.3.1 single-page application (SPA) that provides an intuitive interface for generating and managing bachata choreography videos. The design emphasizes simplicity, minimal dependencies, and a clear separation between presentation (frontend) and business logic (backend).

### Design Philosophy

**"Dumb Frontend, Smart Backend"**

The frontend is intentionally kept simple and focused solely on:
- Rendering UI components
- Handling user interactions
- Making API calls
- Displaying data from the backend
- Client-side routing and navigation

All business logic, data processing, AI operations, and video generation happen in the backend. The frontend never processes data or makes decisions - it simply presents what the backend provides.

### Technology Stack

**Core Dependencies:**
- React 18.3.1 (JavaScript only)
- React Router 6.20.0 (client-side routing)
- Tailwind CSS 3.3.6 (styling)
- Vite 5.0.8 (build tool)

**No Additional Libraries:**
- No TypeScript
- No Axios (using native Fetch API)
- No Redux/MobX (using React Context + local state)
- No UI component libraries (building custom with Tailwind)
- No form libraries (using controlled components)
- No date libraries (using native Date)

### Architecture Principles

1. **Component-Based**: Reusable, composable UI components
2. **Unidirectional Data Flow**: Props down, events up
3. **Separation of Concerns**: Components, pages, utilities clearly separated
4. **API-First**: All data comes from backend API
5. **Progressive Enhancement**: Core functionality works, enhancements add polish
6. **Mobile-First**: Design for mobile, enhance for desktop
7. **Accessibility-First**: WCAG 2.1 AA compliance from the start

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER'S BROWSER                          │
│  ┌───────────────────────────────────────────────────────┐ │
│  │           React SPA (Frontend Application)            │ │
│  │                                                       │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │ │
│  │  │   Pages     │  │  Components  │  │  Utilities │ │ │
│  │  │  (Routes)   │  │   (UI)       │  │  (Helpers) │ │ │
│  │  └─────────────┘  └──────────────┘  └────────────┘ │ │
│  │         │                │                  │        │ │
│  │         └────────────────┴──────────────────┘        │ │
│  │                          │                            │ │
│  │                   ┌──────▼──────┐                    │ │
│  │                   │  API Client │                    │ │
│  │                   │ (Fetch API) │                    │ │
│  │                   └──────┬──────┘                    │ │
│  └──────────────────────────┼─────────────────────────┘ │
└────────────────────────────┼───────────────────────────┘
                             │ HTTP/HTTPS
                             │ (JWT Auth)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   Django REST API (Backend)                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Authentication │ Choreography │ Collections │ Songs │ │
│  └───────────────────────────────────────────────────────┘ │
│                          │                                  │
│                          │ Triggers Job                     │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              Cloud Run Job Container                  │ │
│  │         (Video Assembly with FFmpeg)                  │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Frontend Application Flow

```
User Action → Component Event Handler → API Call → Backend Processing
                                                           ↓
User Sees Result ← Component Re-render ← State Update ← API Response
```



## Component Architecture

### Directory Structure

```
frontend/
├── public/
│   ├── favicon.ico
│   └── logo.svg
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── common/          # Generic components
│   │   │   ├── Button.jsx
│   │   │   ├── Input.jsx
│   │   │   ├── Select.jsx
│   │   │   ├── Modal.jsx
│   │   │   ├── Toast.jsx
│   │   │   ├── Spinner.jsx
│   │   │   └── Card.jsx
│   │   ├── layout/          # Layout components
│   │   │   ├── Navbar.jsx
│   │   │   ├── Footer.jsx
│   │   │   └── Container.jsx
│   │   ├── video/           # Video-related components
│   │   │   ├── VideoPlayer.jsx
│   │   │   ├── LoopControls.jsx
│   │   │   └── ProgressBar.jsx
│   │   ├── generation/      # Generation-specific components
│   │   │   ├── SongCard.jsx
│   │   │   ├── ParameterForm.jsx
│   │   │   ├── ProgressTracker.jsx
│   │   │   └── QueryInput.jsx
│   │   └── collection/      # Collection-specific components
│   │       ├── CollectionCard.jsx
│   │       ├── CollectionFilters.jsx
│   │       └── SaveModal.jsx
│   ├── pages/               # Page components (routes)
│   │   ├── Home.jsx
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── SelectSong.jsx
│   │   ├── DescribeChoreo.jsx
│   │   ├── Progress.jsx
│   │   ├── VideoResult.jsx
│   │   ├── Collections.jsx
│   │   ├── BrowseSongs.jsx
│   │   ├── Profile.jsx
│   │   └── Preferences.jsx
│   ├── contexts/            # React Context providers
│   │   ├── AuthContext.jsx
│   │   └── ToastContext.jsx
│   ├── hooks/               # Custom React hooks
│   │   ├── useAuth.js
│   │   ├── useApi.js
│   │   ├── usePolling.js
│   │   └── useLocalStorage.js
│   ├── utils/               # Utility functions
│   │   ├── api.js           # API client
│   │   ├── auth.js          # Auth helpers
│   │   ├── format.js        # Formatting helpers
│   │   └── validation.js    # Form validation
│   ├── App.jsx              # Main app component
│   ├── main.jsx             # Entry point
│   └── index.css            # Global styles
├── .env.example
├── .gitignore
├── index.html
├── package.json
├── tailwind.config.js
└── vite.config.js
```

### Component Hierarchy

```
App
├── AuthContext.Provider
│   └── ToastContext.Provider
│       ├── Navbar
│       │   ├── Logo
│       │   ├── NavLinks
│       │   └── UserMenu
│       ├── Router
│       │   ├── Home
│       │   ├── Login
│       │   ├── Register
│       │   ├── SelectSong
│       │   │   ├── SongCard (multiple)
│       │   │   └── ParameterForm
│       │   ├── DescribeChoreo
│       │   │   ├── QueryInput
│       │   │   └── ParameterPreview
│       │   ├── Progress
│       │   │   └── ProgressTracker
│       │   ├── VideoResult
│       │   │   ├── VideoPlayer
│       │   │   │   └── LoopControls
│       │   │   └── SaveModal
│       │   ├── Collections
│       │   │   ├── CollectionFilters
│       │   │   └── CollectionCard (multiple)
│       │   ├── BrowseSongs
│       │   │   └── SongCard (multiple)
│       │   ├── Profile
│       │   └── Preferences
│       ├── Footer
│       └── Toast (multiple, stacked)
```



## Core Components Design

### 1. Authentication System

#### AuthContext.jsx
**Purpose:** Manages authentication state globally

**State:**
```javascript
{
  user: { id, username, email } | null,
  accessToken: string | null,
  isAuthenticated: boolean,
  isLoading: boolean
}
```

**Methods:**
- `login(username, password)` - Authenticates user, stores tokens
- `register(username, email, password)` - Creates account, auto-login
- `logout()` - Clears tokens, resets state
- `refreshToken()` - Refreshes access token using refresh token
- `updateProfile(data)` - Updates user profile

**Token Management:**
- Access token stored in localStorage
- Refresh token stored in localStorage (or httpOnly cookie if backend supports)
- Automatic token refresh on 401 responses
- Token expiration check before API calls

#### Login.jsx
**Purpose:** Login page component

**State:**
- `username` - Input value
- `password` - Input value
- `error` - Error message
- `isLoading` - Submit state

**Flow:**
1. User enters credentials
2. Form validation on submit
3. Call `POST /api/auth/login/`
4. Store tokens in AuthContext
5. Redirect to home page

#### Register.jsx
**Purpose:** Registration page component

**State:**
- `username`, `email`, `password`, `confirmPassword`
- `errors` - Validation errors object
- `isLoading` - Submit state

**Validation:**
- Username: 3-30 characters, alphanumeric + underscore
- Email: Valid email format
- Password: Minimum 8 characters
- Confirm password: Must match password

### 2. Navigation System

#### Navbar.jsx
**Purpose:** Top navigation bar

**Props:** None (uses AuthContext)

**Responsive Behavior:**
- Desktop (≥1024px): Full horizontal menu
- Tablet (768-1023px): Condensed menu
- Mobile (<768px): Hamburger menu

**Components:**
```jsx
<nav className="sticky top-0 z-50 bg-white shadow-sm">
  <Container>
    <Logo />
    {isAuthenticated ? (
      <>
        <NavLinks />
        <UserMenu />
      </>
    ) : (
      <AuthButtons />
    )}
  </Container>
</nav>
```

**NavLinks:**
- Generate (dropdown: Select Song, Describe Choreo)
- My Collections
- Browse Songs

**UserMenu:**
- User avatar/initials
- Dropdown: Profile, Preferences, Logout

### 3. Song Selection (Path 1)

#### SelectSong.jsx
**Purpose:** Song selection and parameter configuration page

**State:**
```javascript
{
  songs: [],
  selectedSong: null,
  searchQuery: '',
  filters: { genre: '', bpmMin: 0, bpmMax: 200 },
  sortBy: 'title',
  page: 1,
  isLoading: false,
  showParameterForm: false,
  parameters: { difficulty: '', energy_level: 'medium', style: 'modern' }
}
```

**Flow:**
1. Load songs: `GET /api/choreography/songs/`
2. User searches/filters songs
3. User selects song → Show parameter form
4. User fills parameters → Submit
5. Call `POST /api/choreography/generate-from-song/`
6. Navigate to Progress page with task_id

#### SongCard.jsx
**Purpose:** Display individual song information

**Props:**
```javascript
{
  song: {
    id: number,
    title: string,
    artist: string,
    bpm: number,
    genre: string,
    duration: number
  },
  onSelect: (song) => void
}
```

**Design:**
```jsx
<Card className="hover:shadow-lg transition-shadow cursor-pointer">
  <div className="p-4">
    <h3 className="text-lg font-semibold">{title}</h3>
    <p className="text-gray-600">{artist}</p>
    <div className="flex justify-between mt-2">
      <span className="text-sm">{bpm} BPM</span>
      <span className="text-sm">{formatDuration(duration)}</span>
    </div>
    <Button onClick={() => onSelect(song)}>Select</Button>
  </div>
</Card>
```

#### ParameterForm.jsx
**Purpose:** Choreography parameter selection

**Props:**
```javascript
{
  selectedSong: object,
  onSubmit: (parameters) => void,
  onCancel: () => void
}
```

**Fields:**
- Difficulty: Radio buttons (beginner, intermediate, advanced) - Required
- Energy Level: Radio buttons (low, medium, high) - Default: medium
- Style: Dropdown (romantic, energetic, sensual, playful, modern) - Default: modern

**Validation:**
- Difficulty must be selected
- Submit button disabled until valid



### 4. AI Description (Path 2)

#### DescribeChoreo.jsx
**Purpose:** Natural language choreography description page

**State:**
```javascript
{
  query: '',
  parsedParameters: null,
  showPreview: false,
  isLoading: false,
  error: null,
  suggestions: []
}
```

**Flow:**
1. User enters natural language query
2. (Optional) Click "Preview Parameters" → Call `POST /api/choreography/parse-query/`
3. Show parsed parameters for review
4. User confirms → Call `POST /api/choreography/generate-with-ai/`
5. Navigate to Progress page with task_id

#### QueryInput.jsx
**Purpose:** Text area for natural language input

**Props:**
```javascript
{
  value: string,
  onChange: (value) => void,
  onSubmit: () => void,
  maxLength: 500
}
```

**Features:**
- Auto-resizing textarea
- Character counter (current/max)
- Example queries (clickable to auto-populate)
- Validation: minimum 10 characters
- Submit button disabled when invalid

**Example Queries:**
```javascript
const examples = [
  "Create a romantic beginner bachata with smooth transitions",
  "I want an energetic intermediate choreography with lots of turns",
  "Make me an advanced sensual routine to a slow song"
]
```

#### ParameterPreview.jsx
**Purpose:** Display AI-parsed parameters

**Props:**
```javascript
{
  originalQuery: string,
  parsedParameters: {
    difficulty: string,
    energy_level: string,
    style: string,
    special_requirements: string[]
  },
  selectedSong: object,
  onConfirm: () => void,
  onEdit: () => void
}
```

**Design:**
```jsx
<Modal>
  <h2>AI Extracted Parameters</h2>
  <div className="bg-gray-100 p-4 rounded">
    <p className="text-sm text-gray-600">Your Query:</p>
    <p>{originalQuery}</p>
  </div>
  <div className="grid grid-cols-2 gap-4 mt-4">
    <ParameterCard label="Difficulty" value={difficulty} />
    <ParameterCard label="Energy Level" value={energy_level} />
    <ParameterCard label="Style" value={style} />
    <ParameterCard label="Song" value={`${song.title} - ${song.artist}`} />
  </div>
  <div className="flex gap-2 mt-6">
    <Button onClick={onEdit} variant="secondary">Edit Query</Button>
    <Button onClick={onConfirm} variant="primary">Confirm & Generate</Button>
  </div>
</Modal>
```

### 5. Progress Tracking

#### Progress.jsx
**Purpose:** Real-time progress tracking page

**State:**
```javascript
{
  taskId: string,
  status: 'pending' | 'started' | 'running' | 'completed' | 'failed',
  progress: number, // 0-100
  stage: string,
  message: string,
  error: string | null,
  result: object | null
}
```

**Polling Logic:**
```javascript
useEffect(() => {
  if (!taskId) return;
  
  const pollInterval = setInterval(async () => {
    const response = await fetch(`/api/choreography/tasks/${taskId}/`, {
      headers: { Authorization: `Bearer ${accessToken}` }
    });
    const data = await response.json();
    
    setStatus(data.status);
    setProgress(data.progress);
    setStage(data.stage);
    setMessage(data.message);
    
    if (data.status === 'completed') {
      clearInterval(pollInterval);
      navigate(`/video/${taskId}`);
    } else if (data.status === 'failed') {
      clearInterval(pollInterval);
      setError(data.error);
    }
  }, 2000); // Poll every 2 seconds
  
  // Timeout after 5 minutes
  const timeout = setTimeout(() => {
    clearInterval(pollInterval);
    setError('Generation timed out. Please try again.');
  }, 300000);
  
  return () => {
    clearInterval(pollInterval);
    clearTimeout(timeout);
  };
}, [taskId]);
```

#### ProgressTracker.jsx
**Purpose:** Visual progress indicator

**Props:**
```javascript
{
  progress: number, // 0-100
  stage: string,
  message: string,
  taskId: string,
  onCancel: () => void
}
```

**Stage Emojis:**
```javascript
const stageEmojis = {
  generating_blueprint: '⏳',
  submitting_job: '📤',
  video_assembly: '🎬',
  uploading_result: '☁️',
  completed: '✨'
};
```

**Design:**
```jsx
<div className="max-w-2xl mx-auto p-8">
  <div className="text-center mb-8">
    <div className="text-6xl mb-4">{stageEmojis[stage]}</div>
    <h2 className="text-2xl font-bold">Generating Your Choreography</h2>
    <p className="text-gray-600 mt-2">{message}</p>
  </div>
  
  <div className="relative">
    <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
      <div 
        className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500"
        style={{ width: `${progress}%` }}
      />
    </div>
    <p className="text-center mt-2 text-sm text-gray-600">{progress}%</p>
  </div>
  
  <p className="text-center text-xs text-gray-500 mt-4">Task ID: {taskId}</p>
  
  <Button onClick={onCancel} variant="secondary" className="mt-6 w-full">
    Cancel Generation
  </Button>
</div>
```



### 6. Video Player with Loop Controls

#### VideoPlayer.jsx
**Purpose:** Advanced video player with loop functionality

**State:**
```javascript
{
  isPlaying: boolean,
  currentTime: number,
  duration: number,
  volume: number,
  playbackRate: number,
  isFullscreen: boolean,
  loopEnabled: boolean,
  loopStart: number,
  loopEnd: number
}
```

**Props:**
```javascript
{
  videoUrl: string,
  taskId: string,
  onSave: () => void
}
```

**Key Features:**
1. **Basic Controls:**
   - Play/Pause toggle
   - Seekable progress bar
   - Volume control
   - Fullscreen toggle
   - Playback speed selector (0.5x, 0.75x, 1x, 1.25x, 1.5x)

2. **Loop Controls:**
   - Enable/Disable loop toggle
   - Loop start/end time adjustment (+1s/-1s buttons)
   - Visual loop segment indicator on progress bar
   - Automatic jump back to loop start when reaching loop end

3. **Keyboard Shortcuts:**
   - Space: Play/Pause
   - L: Set loop start at current time
   - K: Set loop end at current time
   - R: Toggle loop on/off
   - Left/Right arrows: Seek ±5 seconds
   - Up/Down arrows: Volume ±10%

**Loop Logic:**
```javascript
useEffect(() => {
  if (!loopEnabled || !videoRef.current) return;
  
  const checkLoop = () => {
    const currentTime = videoRef.current.currentTime;
    if (currentTime >= loopEnd) {
      videoRef.current.currentTime = loopStart;
    }
  };
  
  const interval = setInterval(checkLoop, 100);
  return () => clearInterval(interval);
}, [loopEnabled, loopStart, loopEnd]);
```

**Component Structure:**
```jsx
<div className="max-w-4xl mx-auto">
  {/* Video Element */}
  <video
    ref={videoRef}
    src={videoUrl}
    className="w-full rounded-lg shadow-lg"
    onTimeUpdate={handleTimeUpdate}
    onLoadedMetadata={handleLoadedMetadata}
  />
  
  {/* Custom Controls */}
  <div className="mt-4 space-y-4">
    {/* Play/Pause & Progress Bar */}
    <div className="flex items-center gap-4">
      <Button onClick={togglePlay}>
        {isPlaying ? '⏸️' : '▶️'}
      </Button>
      <ProgressBar
        current={currentTime}
        duration={duration}
        loopStart={loopStart}
        loopEnd={loopEnd}
        loopEnabled={loopEnabled}
        onSeek={handleSeek}
      />
      <span className="text-sm">
        {formatTime(currentTime)} / {formatTime(duration)}
      </span>
    </div>
    
    {/* Additional Controls */}
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <VolumeControl value={volume} onChange={setVolume} />
        <PlaybackSpeedSelector value={playbackRate} onChange={setPlaybackRate} />
      </div>
      <Button onClick={toggleFullscreen}>⛶ Fullscreen</Button>
    </div>
    
    {/* Loop Controls */}
    <LoopControls
      enabled={loopEnabled}
      start={loopStart}
      end={loopEnd}
      onToggle={toggleLoop}
      onStartChange={setLoopStart}
      onEndChange={setLoopEnd}
    />
    
    {/* Action Buttons */}
    <div className="flex gap-2">
      <Button onClick={handleDownload}>⬇️ Download</Button>
      <Button onClick={onSave}>💾 Save to Collection</Button>
    </div>
  </div>
</div>
```

#### LoopControls.jsx
**Purpose:** Loop segment configuration

**Props:**
```javascript
{
  enabled: boolean,
  start: number,
  end: number,
  onToggle: () => void,
  onStartChange: (time: number) => void,
  onEndChange: (time: number) => void
}
```

**Design:**
```jsx
<div className="bg-gray-50 rounded-lg p-4">
  <div className="flex items-center justify-between mb-4">
    <h3 className="font-semibold">🔁 Loop Controls</h3>
    <Button
      onClick={onToggle}
      variant={enabled ? 'primary' : 'secondary'}
    >
      {enabled ? 'Disable Loop' : 'Enable Loop'}
    </Button>
  </div>
  
  {enabled && (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm">Loop Start:</span>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={() => onStartChange(start - 1)}>-1s</Button>
          <span className="font-mono">{formatTime(start)}</span>
          <Button size="sm" onClick={() => onStartChange(start + 1)}>+1s</Button>
        </div>
      </div>
      
      <div className="flex items-center justify-between">
        <span className="text-sm">Loop End:</span>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={() => onEndChange(end - 1)}>-1s</Button>
          <span className="font-mono">{formatTime(end)}</span>
          <Button size="sm" onClick={() => onEndChange(end + 1)}>+1s</Button>
        </div>
      </div>
      
      <div className="text-sm text-gray-600 text-center">
        Loop Duration: {formatTime(end - start)}
      </div>
    </div>
  )}
</div>
```

### 7. Save to Collection

#### SaveModal.jsx
**Purpose:** Save choreography to user's collection

**Props:**
```javascript
{
  taskId: string,
  defaultTitle: string,
  defaultDifficulty: string,
  onSave: () => void,
  onClose: () => void
}
```

**State:**
```javascript
{
  title: string,
  difficulty: string,
  notes: string,
  isLoading: boolean,
  error: string | null
}
```

**Flow:**
1. User clicks "Save to Collection"
2. Modal opens with pre-filled data
3. User edits title/difficulty/notes (optional)
4. User clicks "Save"
5. Call `POST /api/collections/save/`
6. Show success toast
7. Close modal

**Design:**
```jsx
<Modal onClose={onClose}>
  <h2 className="text-xl font-bold mb-4">💾 Save to Your Collection</h2>
  
  <form onSubmit={handleSubmit} className="space-y-4">
    <Input
      label="Title"
      value={title}
      onChange={setTitle}
      placeholder="My Awesome Choreography"
      required
    />
    
    <Select
      label="Difficulty"
      value={difficulty}
      onChange={setDifficulty}
      options={[
        { value: 'beginner', label: 'Beginner' },
        { value: 'intermediate', label: 'Intermediate' },
        { value: 'advanced', label: 'Advanced' }
      ]}
    />
    
    <textarea
      className="w-full p-2 border rounded"
      placeholder="Notes (optional)"
      value={notes}
      onChange={(e) => setNotes(e.target.value)}
      rows={3}
    />
    
    {error && <p className="text-red-500 text-sm">{error}</p>}
    
    <div className="flex gap-2">
      <Button type="button" onClick={onClose} variant="secondary">
        Skip
      </Button>
      <Button type="submit" disabled={isLoading}>
        {isLoading ? 'Saving...' : '💾 Save to Collection'}
      </Button>
    </div>
  </form>
</Modal>
```



### 8. Collections Management

#### Collections.jsx
**Purpose:** Display and manage user's saved choreographies

**State:**
```javascript
{
  collections: [],
  stats: { total_count, total_duration, by_difficulty, recent_count },
  searchQuery: '',
  filterDifficulty: 'all',
  sortBy: 'recent',
  page: 1,
  isLoading: false
}
```

**API Calls:**
- Load collections: `GET /api/collections/?difficulty=&search=&page=`
- Load stats: `GET /api/collections/stats/`
- Delete item: `DELETE /api/collections/{id}/`
- Update item: `PUT /api/collections/{id}/`

**Features:**
1. Search by title or song name
2. Filter by difficulty
3. Sort by date, title, or duration
4. Pagination (20 items per page)
5. Statistics panel
6. Empty state with CTA

#### CollectionCard.jsx
**Purpose:** Display individual collection item

**Props:**
```javascript
{
  collection: {
    id: number,
    title: string,
    created_at: string,
    duration: number,
    difficulty: string,
    num_moves: number,
    song_title: string,
    video_url: string
  },
  onPlay: (id) => void,
  onEdit: (id) => void,
  onDelete: (id) => void
}
```

**Design:**
```jsx
<Card className="hover:shadow-lg transition-shadow">
  <div className="p-4">
    <div className="flex items-start justify-between">
      <div>
        <h3 className="text-lg font-semibold">🎬 {title}</h3>
        <p className="text-sm text-gray-600">
          Created: {formatDate(created_at)} • Duration: {formatDuration(duration)}
        </p>
        <p className="text-sm text-gray-600">
          Difficulty: {difficulty} • {num_moves} moves
        </p>
        {song_title && (
          <p className="text-sm text-gray-500 mt-1">Song: {song_title}</p>
        )}
      </div>
      <DifficultyBadge level={difficulty} />
    </div>
    
    <div className="flex gap-2 mt-4">
      <Button onClick={() => onPlay(id)} size="sm">▶️ Play</Button>
      <Button onClick={() => onEdit(id)} size="sm" variant="secondary">✏️ Edit</Button>
      <Button onClick={() => onDelete(id)} size="sm" variant="danger">🗑️ Delete</Button>
    </div>
  </div>
</Card>
```

#### CollectionFilters.jsx
**Purpose:** Search, filter, and sort controls

**Props:**
```javascript
{
  searchQuery: string,
  filterDifficulty: string,
  sortBy: string,
  onSearchChange: (query) => void,
  onFilterChange: (difficulty) => void,
  onSortChange: (sortBy) => void
}
```

**Design:**
```jsx
<div className="flex flex-col md:flex-row gap-4 mb-6">
  <Input
    type="search"
    placeholder="Search by title or song..."
    value={searchQuery}
    onChange={onSearchChange}
    className="flex-1"
  />
  
  <Select
    value={filterDifficulty}
    onChange={onFilterChange}
    options={[
      { value: 'all', label: 'All Difficulties' },
      { value: 'beginner', label: 'Beginner' },
      { value: 'intermediate', label: 'Intermediate' },
      { value: 'advanced', label: 'Advanced' }
    ]}
  />
  
  <Select
    value={sortBy}
    onChange={onSortChange}
    options={[
      { value: 'recent', label: 'Most Recent' },
      { value: 'oldest', label: 'Oldest First' },
      { value: 'title', label: 'Title (A-Z)' },
      { value: 'duration', label: 'Duration' }
    ]}
  />
</div>
```

### 9. Browse Songs

#### BrowseSongs.jsx
**Purpose:** Browse all available songs

**State:**
```javascript
{
  songs: [],
  searchQuery: '',
  filters: { genre: '', bpmMin: 0, bpmMax: 200 },
  sortBy: 'title',
  page: 1,
  isLoading: false
}
```

**Similar to SelectSong.jsx but:**
- No parameter form
- "Generate with this song" button navigates to SelectSong with pre-selected song
- More detailed song information displayed
- Optional audio preview (future enhancement)

### 10. User Profile & Preferences

#### Profile.jsx
**Purpose:** View and edit user profile

**State:**
```javascript
{
  user: { username, email },
  stats: { total_choreographies, total_duration, member_since },
  isEditing: boolean,
  isLoading: boolean,
  error: null
}
```

**Sections:**
1. Profile Information (username, email)
2. Account Statistics
3. Change Password
4. Delete Account

#### Preferences.jsx
**Purpose:** Manage user preferences

**State:**
```javascript
{
  preferences: {
    default_difficulty: 'intermediate',
    default_energy_level: 'medium',
    default_style: 'modern'
  },
  isLoading: boolean,
  error: null
}
```

**Features:**
- Dropdown selectors for defaults
- Save button
- Reset to defaults button



## Data Flow and State Management

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Authentication Flow                       │
└─────────────────────────────────────────────────────────────┘

User enters credentials
        ↓
Login.jsx validates input
        ↓
POST /api/auth/login/
        ↓
Backend validates & returns tokens
        ↓
AuthContext stores tokens in localStorage
        ↓
AuthContext updates state: { user, accessToken, isAuthenticated: true }
        ↓
All components re-render with authenticated state
        ↓
Navbar shows user menu, protected routes accessible
```

### Token Refresh Flow

```
API call returns 401 Unauthorized
        ↓
API client intercepts response
        ↓
POST /api/auth/refresh/ with refresh token
        ↓
Backend returns new access token
        ↓
AuthContext updates access token
        ↓
Retry original API call with new token
        ↓
If refresh fails (401) → Logout user, redirect to login
```

### Choreography Generation Flow (Path 1)

```
User selects song → SelectSong.jsx
        ↓
User fills parameters → ParameterForm.jsx
        ↓
POST /api/choreography/generate-from-song/
        ↓
Backend returns { task_id, status: 'started', poll_url }
        ↓
Navigate to /progress/:taskId
        ↓
Progress.jsx starts polling GET /api/choreography/tasks/:taskId/
        ↓
Poll every 2 seconds while status is 'pending' or 'running'
        ↓
Backend updates progress: { progress: 45, stage: 'video_assembly', message: '...' }
        ↓
ProgressTracker.jsx updates UI
        ↓
Status becomes 'completed' → Stop polling
        ↓
Navigate to /video/:taskId
        ↓
VideoResult.jsx displays video player
        ↓
User watches, practices with loop controls
        ↓
User saves to collection → SaveModal.jsx
        ↓
POST /api/collections/save/
        ↓
Success toast → Navigate to /collections
```

### Choreography Generation Flow (Path 2)

```
User enters query → DescribeChoreo.jsx
        ↓
(Optional) POST /api/choreography/parse-query/ → Show preview
        ↓
POST /api/choreography/generate-with-ai/
        ↓
Backend returns { task_id, parsed_parameters, song, poll_url }
        ↓
Navigate to /progress/:taskId
        ↓
[Same polling flow as Path 1]
```

### Collection Management Flow

```
User navigates to /collections
        ↓
Collections.jsx loads data:
  - GET /api/collections/
  - GET /api/collections/stats/
        ↓
Display collection cards with filters
        ↓
User searches/filters → Update query params → Reload data
        ↓
User clicks "Play" → Navigate to /video/:taskId
        ↓
User clicks "Edit" → Modal opens → PUT /api/collections/:id/
        ↓
User clicks "Delete" → Confirmation dialog → DELETE /api/collections/:id/
        ↓
Reload collections list
```

## API Client Design

### api.js Structure

```javascript
// Base configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_TIMEOUT = 30000;

// Helper to get auth token
const getAuthToken = () => {
  return localStorage.getItem('accessToken');
};

// Helper to refresh token
const refreshAuthToken = async () => {
  const refreshToken = localStorage.getItem('refreshToken');
  if (!refreshToken) throw new Error('No refresh token');
  
  const response = await fetch(`${API_BASE_URL}/api/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken })
  });
  
  if (!response.ok) throw new Error('Token refresh failed');
  
  const data = await response.json();
  localStorage.setItem('accessToken', data.access);
  return data.access;
};

// Main API client function
const apiClient = async (endpoint, options = {}) => {
  const {
    method = 'GET',
    body = null,
    headers = {},
    requiresAuth = true,
    retries = 3
  } = options;
  
  const url = `${API_BASE_URL}${endpoint}`;
  
  const fetchOptions = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers
    }
  };
  
  // Add auth token if required
  if (requiresAuth) {
    const token = getAuthToken();
    if (token) {
      fetchOptions.headers['Authorization'] = `Bearer ${token}`;
    }
  }
  
  // Add body if present
  if (body) {
    fetchOptions.body = JSON.stringify(body);
  }
  
  // Add timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);
  fetchOptions.signal = controller.signal;
  
  try {
    const response = await fetch(url, fetchOptions);
    clearTimeout(timeoutId);
    
    // Handle 401 - Token expired
    if (response.status === 401 && requiresAuth && retries > 0) {
      try {
        await refreshAuthToken();
        // Retry with new token
        return apiClient(endpoint, { ...options, retries: retries - 1 });
      } catch (refreshError) {
        // Refresh failed - logout user
        localStorage.clear();
        window.location.href = '/login';
        throw new Error('Session expired');
      }
    }
    
    // Handle other errors
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.error || 'Request failed');
    }
    
    // Return JSON data
    return await response.json();
    
  } catch (error) {
    clearTimeout(timeoutId);
    
    // Handle network errors
    if (error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    
    throw error;
  }
};

// Exported API methods
export const api = {
  // Auth
  login: (username, password) => 
    apiClient('/api/auth/login/', {
      method: 'POST',
      body: { username, password },
      requiresAuth: false
    }),
  
  register: (username, email, password) =>
    apiClient('/api/auth/register/', {
      method: 'POST',
      body: { username, email, password },
      requiresAuth: false
    }),
  
  getProfile: () => apiClient('/api/auth/me/'),
  
  updateProfile: (data) =>
    apiClient('/api/auth/me/', { method: 'PUT', body: data }),
  
  // Songs
  getSongs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return apiClient(`/api/choreography/songs/?${query}`);
  },
  
  getSong: (id) => apiClient(`/api/choreography/songs/${id}/`),
  
  // Generation
  generateFromSong: (songId, difficulty, energyLevel, style) =>
    apiClient('/api/choreography/generate-from-song/', {
      method: 'POST',
      body: { song_id: songId, difficulty, energy_level: energyLevel, style }
    }),
  
  generateWithAI: (query) =>
    apiClient('/api/choreography/generate-with-ai/', {
      method: 'POST',
      body: { query }
    }),
  
  parseQuery: (query) =>
    apiClient('/api/choreography/parse-query/', {
      method: 'POST',
      body: { query }
    }),
  
  // Tasks
  getTaskStatus: (taskId) =>
    apiClient(`/api/choreography/tasks/${taskId}/`),
  
  cancelTask: (taskId) =>
    apiClient(`/api/choreography/tasks/${taskId}/`, { method: 'DELETE' }),
  
  // Collections
  getCollections: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return apiClient(`/api/collections/?${query}`);
  },
  
  getCollectionStats: () => apiClient('/api/collections/stats/'),
  
  saveToCollection: (taskId, title, difficulty, notes) =>
    apiClient('/api/collections/save/', {
      method: 'POST',
      body: { task_id: taskId, title, difficulty, notes }
    }),
  
  updateCollection: (id, data) =>
    apiClient(`/api/collections/${id}/`, { method: 'PUT', body: data }),
  
  deleteCollection: (id) =>
    apiClient(`/api/collections/${id}/`, { method: 'DELETE' })
};
```



## Custom Hooks

### useAuth Hook

```javascript
// hooks/useAuth.js
import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

### usePolling Hook

```javascript
// hooks/usePolling.js
import { useState, useEffect, useRef } from 'react';

export const usePolling = (fetchFn, interval = 2000, shouldPoll = true) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const intervalRef = useRef(null);
  
  useEffect(() => {
    if (!shouldPoll) return;
    
    const poll = async () => {
      try {
        const result = await fetchFn();
        setData(result);
        setError(null);
        
        // Stop polling if completed or failed
        if (result.status === 'completed' || result.status === 'failed') {
          clearInterval(intervalRef.current);
        }
      } catch (err) {
        setError(err.message);
        clearInterval(intervalRef.current);
      } finally {
        setIsLoading(false);
      }
    };
    
    // Initial poll
    poll();
    
    // Set up interval
    intervalRef.current = setInterval(poll, interval);
    
    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchFn, interval, shouldPoll]);
  
  return { data, error, isLoading };
};
```

### useLocalStorage Hook

```javascript
// hooks/useLocalStorage.js
import { useState, useEffect } from 'react';

export const useLocalStorage = (key, initialValue) => {
  const [value, setValue] = useState(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });
  
  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, value]);
  
  return [value, setValue];
};
```

### useDebounce Hook

```javascript
// hooks/useDebounce.js
import { useState, useEffect } from 'react';

export const useDebounce = (value, delay = 500) => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  
  return debouncedValue;
};
```

## Utility Functions

### format.js

```javascript
// utils/format.js

export const formatTime = (seconds) => {
  if (!seconds || isNaN(seconds)) return '0:00';
  
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export const formatDuration = (seconds) => {
  if (!seconds || isNaN(seconds)) return '0:00';
  
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

export const capitalize = (str) => {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
};
```

### validation.js

```javascript
// utils/validation.js

export const validateEmail = (email) => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

export const validateUsername = (username) => {
  // 3-30 characters, alphanumeric + underscore
  const re = /^[a-zA-Z0-9_]{3,30}$/;
  return re.test(username);
};

export const validatePassword = (password) => {
  // Minimum 8 characters
  return password && password.length >= 8;
};

export const validateQuery = (query) => {
  // Minimum 10 characters, maximum 500
  return query && query.length >= 10 && query.length <= 500;
};

export const getPasswordStrength = (password) => {
  if (!password) return { strength: 0, label: 'None' };
  
  let strength = 0;
  
  if (password.length >= 8) strength++;
  if (password.length >= 12) strength++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
  if (/\d/.test(password)) strength++;
  if (/[^a-zA-Z0-9]/.test(password)) strength++;
  
  const labels = ['Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
  return {
    strength: Math.min(strength, 5),
    label: labels[Math.min(strength - 1, 4)] || 'Weak'
  };
};
```

## Routing Configuration

### App.jsx

```javascript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { useAuth } from './hooks/useAuth';

// Layout
import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';

// Pages
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import SelectSong from './pages/SelectSong';
import DescribeChoreo from './pages/DescribeChoreo';
import Progress from './pages/Progress';
import VideoResult from './pages/VideoResult';
import Collections from './pages/Collections';
import BrowseSongs from './pages/BrowseSongs';
import Profile from './pages/Profile';
import Preferences from './pages/Preferences';

// Protected Route wrapper
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen">
      <Spinner />
    </div>;
  }
  
  return isAuthenticated ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <div className="min-h-screen flex flex-col">
            <Navbar />
            <main className="flex-1">
              <Routes>
                {/* Public routes */}
                <Route path="/" element={<Home />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                
                {/* Protected routes */}
                <Route path="/select-song" element={
                  <ProtectedRoute><SelectSong /></ProtectedRoute>
                } />
                <Route path="/describe-choreo" element={
                  <ProtectedRoute><DescribeChoreo /></ProtectedRoute>
                } />
                <Route path="/progress/:taskId" element={
                  <ProtectedRoute><Progress /></ProtectedRoute>
                } />
                <Route path="/video/:taskId" element={
                  <ProtectedRoute><VideoResult /></ProtectedRoute>
                } />
                <Route path="/collections" element={
                  <ProtectedRoute><Collections /></ProtectedRoute>
                } />
                <Route path="/browse-songs" element={
                  <ProtectedRoute><BrowseSongs /></ProtectedRoute>
                } />
                <Route path="/profile" element={
                  <ProtectedRoute><Profile /></ProtectedRoute>
                } />
                <Route path="/preferences" element={
                  <ProtectedRoute><Preferences /></ProtectedRoute>
                } />
                
                {/* 404 */}
                <Route path="*" element={<Navigate to="/" />} />
              </Routes>
            </main>
            <Footer />
          </div>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
```



## Styling and Design System

### Tailwind Configuration

```javascript
// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7', // Main purple
          600: '#9333ea',
          700: '#7e22ce',
          800: '#6b21a8',
          900: '#581c87',
        },
        secondary: {
          50: '#fdf2f8',
          100: '#fce7f3',
          200: '#fbcfe8',
          300: '#f9a8d4',
          400: '#f472b6',
          500: '#ec4899', // Main pink
          600: '#db2777',
          700: '#be185d',
          800: '#9f1239',
          900: '#831843',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif']
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite'
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideIn: {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' }
        }
      }
    }
  },
  plugins: []
}
```

### Component Styling Patterns

**Button Component:**
```jsx
// components/common/Button.jsx
const variants = {
  primary: 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white hover:from-primary-600 hover:to-secondary-600',
  secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
  danger: 'bg-red-500 text-white hover:bg-red-600',
  ghost: 'bg-transparent text-gray-700 hover:bg-gray-100'
};

const sizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg'
};

export const Button = ({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  disabled = false,
  className = '',
  ...props 
}) => {
  return (
    <button
      className={`
        rounded-lg font-medium transition-all duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
        ${variants[variant]}
        ${sizes[size]}
        ${className}
      `}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};
```

**Card Component:**
```jsx
// components/common/Card.jsx
export const Card = ({ children, className = '', hover = false }) => {
  return (
    <div className={`
      bg-white rounded-xl shadow-sm border border-gray-200
      ${hover ? 'hover:shadow-lg transition-shadow duration-200' : ''}
      ${className}
    `}>
      {children}
    </div>
  );
};
```

**Input Component:**
```jsx
// components/common/Input.jsx
export const Input = ({ 
  label, 
  error, 
  className = '', 
  ...props 
}) => {
  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <input
        className={`
          w-full px-4 py-2 rounded-lg border
          focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
          disabled:bg-gray-100 disabled:cursor-not-allowed
          ${error ? 'border-red-500' : 'border-gray-300'}
          ${className}
        `}
        {...props}
      />
      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}
    </div>
  );
};
```

### Responsive Design Patterns

**Mobile-First Approach:**
```jsx
// Default styles for mobile, then enhance for larger screens
<div className="
  flex flex-col gap-4           // Mobile: vertical stack
  md:flex-row md:gap-6          // Tablet: horizontal layout
  lg:gap-8                      // Desktop: larger gaps
">
  <div className="
    w-full                      // Mobile: full width
    md:w-1/2                    // Tablet: half width
    lg:w-1/3                    // Desktop: third width
  ">
    {/* Content */}
  </div>
</div>
```

**Breakpoint Reference:**
- `sm`: 640px (small tablets)
- `md`: 768px (tablets)
- `lg`: 1024px (laptops)
- `xl`: 1280px (desktops)
- `2xl`: 1536px (large desktops)

## Error Handling Strategy

### Error Boundary Component

```jsx
// components/ErrorBoundary.jsx
import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    // In production, send to error tracking service
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="max-w-md text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              Oops! Something went wrong
            </h1>
            <p className="text-gray-600 mb-6">
              We're sorry for the inconvenience. Please try refreshing the page.
            </p>
            <Button onClick={() => window.location.reload()}>
              Refresh Page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

### Toast Notification System

```jsx
// contexts/ToastContext.jsx
import React, { createContext, useState, useCallback } from 'react';
import Toast from '../components/common/Toast';

export const ToastContext = createContext();

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    
    // Auto-dismiss after 3 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id));
    }, 3000);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map(toast => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
};
```

```jsx
// components/common/Toast.jsx
const typeStyles = {
  success: 'bg-green-500 text-white',
  error: 'bg-red-500 text-white',
  warning: 'bg-yellow-500 text-white',
  info: 'bg-blue-500 text-white'
};

const typeIcons = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ'
};

export const Toast = ({ message, type = 'info', onClose }) => {
  return (
    <div className={`
      ${typeStyles[type]}
      px-4 py-3 rounded-lg shadow-lg
      flex items-center gap-3
      animate-slide-in
      min-w-[300px] max-w-md
    `}>
      <span className="text-xl">{typeIcons[type]}</span>
      <p className="flex-1">{message}</p>
      <button
        onClick={onClose}
        className="text-white hover:opacity-75 transition-opacity"
      >
        ✕
      </button>
    </div>
  );
};
```



## Performance Optimization

### Code Splitting

```javascript
// Lazy load pages for better initial load time
import { lazy, Suspense } from 'react';

const SelectSong = lazy(() => import('./pages/SelectSong'));
const DescribeChoreo = lazy(() => import('./pages/DescribeChoreo'));
const Collections = lazy(() => import('./pages/Collections'));

// Wrap in Suspense with loading fallback
<Suspense fallback={<LoadingSpinner />}>
  <Route path="/select-song" element={<SelectSong />} />
</Suspense>
```

### Image Optimization

```jsx
// Lazy load images
<img
  src={thumbnailUrl}
  alt={title}
  loading="lazy"
  className="w-full h-48 object-cover"
/>
```

### Memoization

```javascript
// Memoize expensive computations
import { useMemo } from 'react';

const filteredSongs = useMemo(() => {
  return songs.filter(song => 
    song.title.toLowerCase().includes(searchQuery.toLowerCase())
  );
}, [songs, searchQuery]);

// Memoize callbacks to prevent re-renders
import { useCallback } from 'react';

const handleSongSelect = useCallback((song) => {
  setSelectedSong(song);
  setShowParameterForm(true);
}, []);
```

### Debouncing Search

```javascript
// Use debounce hook for search input
const [searchQuery, setSearchQuery] = useState('');
const debouncedQuery = useDebounce(searchQuery, 500);

useEffect(() => {
  if (debouncedQuery) {
    fetchSongs(debouncedQuery);
  }
}, [debouncedQuery]);
```

## Accessibility Implementation

### Keyboard Navigation

```jsx
// Ensure all interactive elements are keyboard accessible
<button
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }}
  tabIndex={0}
  aria-label="Select song"
>
  Select
</button>
```

### ARIA Labels

```jsx
// Progress bar with ARIA
<div
  role="progressbar"
  aria-valuenow={progress}
  aria-valuemin={0}
  aria-valuemax={100}
  aria-label="Choreography generation progress"
>
  <div style={{ width: `${progress}%` }} />
</div>

// Modal with proper ARIA
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="modal-title"
  aria-describedby="modal-description"
>
  <h2 id="modal-title">Save to Collection</h2>
  <p id="modal-description">Enter details to save this choreography</p>
</div>
```

### Focus Management

```javascript
// Trap focus in modal
import { useEffect, useRef } from 'react';

const Modal = ({ isOpen, onClose, children }) => {
  const modalRef = useRef(null);
  
  useEffect(() => {
    if (!isOpen) return;
    
    const focusableElements = modalRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    firstElement?.focus();
    
    const handleTab = (e) => {
      if (e.key !== 'Tab') return;
      
      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };
    
    document.addEventListener('keydown', handleTab);
    return () => document.removeEventListener('keydown', handleTab);
  }, [isOpen]);
  
  return isOpen ? (
    <div ref={modalRef} role="dialog" aria-modal="true">
      {children}
    </div>
  ) : null;
};
```

### Screen Reader Announcements

```jsx
// Live region for dynamic updates
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
  className="sr-only"
>
  {statusMessage}
</div>

// Screen reader only text
<span className="sr-only">
  Progress: {progress} percent complete
</span>
```

## Testing Strategy

### Component Testing

```javascript
// Example test for Button component
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });
  
  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
  
  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click me</Button>);
    expect(screen.getByText('Click me')).toBeDisabled();
  });
});
```

### Integration Testing

```javascript
// Example test for login flow
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Login from './pages/Login';

describe('Login Flow', () => {
  it('logs in user with valid credentials', async () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </BrowserRouter>
    );
    
    fireEvent.change(screen.getByLabelText('Username'), {
      target: { value: 'testuser' }
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'password123' }
    });
    
    fireEvent.click(screen.getByText('Login'));
    
    await waitFor(() => {
      expect(window.location.pathname).toBe('/');
    });
  });
});
```

## Deployment Configuration

### Environment Variables

```bash
# .env.development
VITE_API_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
VITE_POLL_INTERVAL=2000
VITE_MAX_POLL_DURATION=300000

# .env.production
VITE_API_URL=https://api.bachatabuddy.com
VITE_API_TIMEOUT=30000
VITE_POLL_INTERVAL=2000
VITE_MAX_POLL_DURATION=300000
```

### Build Configuration

```javascript
// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom']
        }
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
```

### Docker Configuration

```dockerfile
# Dockerfile (Production)
FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

```nginx
# nginx.conf
server {
    listen 80;
    server_name _;
    
    root /usr/share/nginx/html;
    index index.html;
    
    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

## Security Considerations

### XSS Prevention

```javascript
// Always sanitize user input before rendering
import DOMPurify from 'dompurify'; // If needed for rich text

// For simple text, React automatically escapes
<p>{userInput}</p> // Safe

// For HTML content, sanitize first
<div dangerouslySetInnerHTML={{ 
  __html: DOMPurify.sanitize(htmlContent) 
}} />
```

### CSRF Protection

```javascript
// Django handles CSRF for authenticated requests
// Ensure cookies are sent with requests
fetch(url, {
  credentials: 'include', // Send cookies
  headers: {
    'X-CSRFToken': getCookie('csrftoken')
  }
});
```

### Content Security Policy

```html
<!-- index.html -->
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               script-src 'self' 'unsafe-inline'; 
               style-src 'self' 'unsafe-inline'; 
               img-src 'self' data: https:; 
               font-src 'self' data:; 
               connect-src 'self' https://api.bachatabuddy.com;">
```

## Monitoring and Analytics

### Error Tracking

```javascript
// In production, send errors to monitoring service
window.addEventListener('error', (event) => {
  if (process.env.NODE_ENV === 'production') {
    // Send to error tracking service (e.g., Sentry)
    console.error('Global error:', event.error);
  }
});

// Track API errors
const apiClient = async (endpoint, options) => {
  try {
    const response = await fetch(endpoint, options);
    if (!response.ok) {
      // Log API errors
      console.error('API Error:', {
        endpoint,
        status: response.status,
        statusText: response.statusText
      });
    }
    return response;
  } catch (error) {
    // Log network errors
    console.error('Network Error:', error);
    throw error;
  }
};
```

### Performance Monitoring

```javascript
// Track page load performance
window.addEventListener('load', () => {
  const perfData = performance.getEntriesByType('navigation')[0];
  console.log('Page Load Time:', perfData.loadEventEnd - perfData.fetchStart);
  
  // In production, send to analytics service
});

// Track API response times
const trackApiCall = async (endpoint, fetchFn) => {
  const startTime = performance.now();
  try {
    const result = await fetchFn();
    const duration = performance.now() - startTime;
    console.log(`API Call ${endpoint}: ${duration}ms`);
    return result;
  } catch (error) {
    const duration = performance.now() - startTime;
    console.error(`API Call ${endpoint} failed after ${duration}ms`);
    throw error;
  }
};
```

## Summary

This design document provides a comprehensive blueprint for building the Bachata Buddy frontend with:

1. **Simple, maintainable architecture** - Component-based with clear separation of concerns
2. **Minimal dependencies** - React 18.3.1 + Tailwind CSS + React Router
3. **API-first approach** - All business logic in backend, frontend is "dumb"
4. **Excellent UX** - Real-time progress, loop controls, responsive design
5. **Accessibility** - WCAG 2.1 AA compliance from the start
6. **Performance** - Code splitting, lazy loading, optimized builds
7. **Security** - XSS prevention, CSRF protection, secure token management
8. **Testability** - Clear component structure, easy to test

The design preserves all legacy features while modernizing the user experience and following React best practices.

---

**Next Steps:**
1. Review and approve design document
2. Create implementation tasks
3. Set up project structure
4. Begin component development
5. Implement API integration
6. Add tests
7. Deploy to staging
8. User acceptance testing
9. Deploy to production

