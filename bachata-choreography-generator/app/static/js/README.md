# JavaScript Architecture

This directory contains all extracted JavaScript code from the application templates, organized for maintainability and reusability.

## Directory Structure

```
js/
├── core/               # Core application functionality
│   └── app-state.js   # Global Alpine.js state (authentication, notifications)
├── components/         # Page-specific Alpine.js components
│   └── choreography-app.js  # Main choreography generator component
└── utils/              # Shared utility functions
    ├── validators.js   # Validation utilities (URLs, auth checks)
    └── helpers.js      # General helpers (formatters, notifications)
```

## File Descriptions

### Core (`core/`)

#### `app-state.js`
Global application state managed by Alpine.js. Loaded on all pages via `base.html`.

**Provides:**
- `appState()` - Main Alpine.js state function
- User authentication management
- HTMX authentication headers
- Global notification system
- Login/logout/register handlers

**Usage in templates:**
```html
<body x-data="appState()" x-init="initApp()">
```

### Components (`components/`)

#### `choreography-app.js`
Main choreography generator component for creating and managing dance sequences.

**Provides:**
- `choreographyApp()` - Alpine.js component function
- Form state management (song selection, difficulty)
- Generation flow (API calls, progress tracking)
- Video player controls with loop functionality
- Save/load choreography management

**Usage in templates:**
```html
<div x-data="choreographyApp()">
  <!-- Component HTML -->
</div>

<!-- In template footer -->
<script src="/static/js/components/choreography-app.js"></script>
```

**Key Features:**
- Real-time progress polling via HTMX and fetch backup
- Video player with loop segment selection
- Task resumption on page reload
- Defensive $root checks for Alpine.js compatibility

### Utils (`utils/`)

#### `validators.js`
Validation and parsing utilities.

**Functions:**
- `isValidYouTubeUrl(url)` - Validates YouTube URL format
- `isAuthenticated($root)` - Checks authentication status
- `parseXhrResponse(xhr)` - Safely parses XHR responses

**Global Access:**
```javascript
window.ValidationUtils.isValidYouTubeUrl(url);
```

#### `helpers.js`
General-purpose helper functions.

**Functions:**
- `formatTime(seconds)` - Formats seconds to MM:SS
- `getStageEmoji(stage)` - Returns emoji for generation stage
- `safeCall(fn, ...args)` - Safely calls functions with error handling
- `showNotification($root, message, type)` - Shows notifications

**Global Access:**
```javascript
window.HelperUtils.formatTime(123);
```

## Loading Order

JavaScript files must be loaded in the correct order in templates:

### In `base.html` (loaded on all pages):
```html
<!-- 1. Utility scripts -->
<script src="/static/js/utils/validators.js"></script>
<script src="/static/js/utils/helpers.js"></script>

<!-- 2. Core application state -->
<script src="/static/js/core/app-state.js"></script>
```

### In page templates (e.g., `index.html`):
```html
{% block extra_scripts %}
<!-- Page-specific components -->
<script src="/static/js/components/choreography-app.js"></script>
{% endblock %}
```

## Design Principles

### 1. **Global Registration**
All Alpine.js functions are registered globally on the `window` object for compatibility:
```javascript
window.appState = appState;
window.choreographyApp = choreographyApp;
```

### 2. **Utility Namespaces**
Utilities are grouped under namespace objects:
```javascript
window.ValidationUtils = { ... };
window.HelperUtils = { ... };
```

### 3. **Defensive Coding**
All code handles cases where dependencies might not be loaded:
```javascript
const isAuth = this.$root?.user?.isAuthenticated || localStorage.getItem('auth_token');
```

### 4. **No Build Step**
Files are served directly without bundling/transpiling for simplicity. Browser caching handles performance.

## Adding New Components

To add a new page component:

1. **Create component file:**
   ```javascript
   // static/js/components/my-component.js
   function myComponent() {
       return {
           // Component state and methods
       };
   }
   window.myComponent = myComponent;
   ```

2. **Load in template:**
   ```html
   {% block extra_scripts %}
   <script src="/static/js/components/my-component.js"></script>
   {% endblock %}
   ```

3. **Use in HTML:**
   ```html
   <div x-data="myComponent()">
       <!-- Your HTML -->
   </div>
   ```

## Migration Notes

This structure was created by extracting ~800 lines of inline JavaScript from templates:
- **Before:** All JavaScript embedded in `<script>` tags within HTML templates
- **After:** Modular files with clear separation of concerns

### Benefits:
- ✅ Better IDE support (syntax highlighting, autocomplete)
- ✅ Easier debugging and maintenance
- ✅ Browser caching for performance
- ✅ Reusable utility functions
- ✅ Clear dependency management

### Backward Compatibility:
All functions maintain the same API and behavior as before. No changes required to HTML or Alpine.js directives.

## Future Enhancements

Potential improvements for Phase 3:

1. **Build System** - Add Vite/Rollup for bundling and minification
2. **TypeScript** - Add type safety
3. **Unit Tests** - Test utilities and components independently
4. **Source Maps** - Better debugging in production
5. **Tree Shaking** - Remove unused code
6. **Module Format** - Convert to ES6 modules when appropriate

## Troubleshooting

### Component not found
**Error:** `choreographyApp is not defined`
**Solution:** Ensure script is loaded before Alpine.js initializes:
```html
<script src="/static/js/components/choreography-app.js"></script>
<script defer src="https://unpkg.com/alpinejs@3.13.5/dist/cdn.min.js"></script>
```

### Utilities not available
**Error:** `ValidationUtils is not defined`
**Solution:** Check load order - utilities must load before components that use them.

### $root is undefined
This is expected in some contexts. Code uses defensive checks:
```javascript
this.$root?.user?.isAuthenticated || localStorage.getItem('auth_token')
```
