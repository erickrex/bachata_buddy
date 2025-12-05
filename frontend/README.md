# Bachata Buddy Frontend

React 18.3 frontend for the Bachata Buddy AI choreography generator.

## Technology Stack

- **React 18.3** - UI library
- **React Router 6** - Client-side routing
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Fetch API** - HTTP requests

## Quick Start

### Local Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

Dev server runs at http://localhost:5173

### Docker Development

```bash
# From root directory
docker-compose up -d

# View logs
docker-compose logs -f frontend

# Stop services
docker-compose down
```

Frontend available at http://localhost:5173

## Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable UI components
│   │   ├── Button.jsx
│   │   ├── Input.jsx
│   │   ├── Spinner.jsx
│   │   ├── VideoPlayer.jsx
│   │   └── Toast.jsx
│   ├── pages/          # Page components
│   │   ├── Home.jsx
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── Generate.jsx
│   │   ├── Describe.jsx
│   │   ├── Collections.jsx
│   │   └── Profile.jsx
│   ├── utils/          # Utility functions
│   │   ├── api.js      # API client with JWT
│   │   └── auth.js     # Auth helpers
│   ├── App.jsx         # Main app with routing
│   └── main.jsx        # Entry point
├── public/             # Static assets
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## Features

### Two Choreography Generation Paths

**Path 1: Song Selection (Traditional)**
- Browse available songs
- Filter by genre, BPM, artist
- Select difficulty, style, energy
- Generate choreography

**Path 2: AI Description (Conversational)**
- Describe choreography in natural language
- AI extracts parameters automatically
- Real-time reasoning panel
- Auto-save to collections

### Collection Management
- Save and organize choreographies
- Search and filter
- View statistics
- Bulk operations

### User Profile
- Update preferences
- Set default difficulty
- Configure auto-save
- Email notifications

## API Integration

### Authentication

JWT tokens stored in localStorage:
- Access token (1 hour)
- Refresh token (7 days)
- Automatic refresh on 401

### API Client

```javascript
// utils/api.js
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function apiCall(endpoint, options = {}) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
      ...options.headers,
    },
  });
  
  if (response.status === 401) {
    // Refresh token logic
    await refreshToken();
    return apiCall(endpoint, options);
  }
  
  return response.json();
}
```

### Key Endpoints

```javascript
// Authentication
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/refresh/
GET  /api/auth/profile/

// Choreography
GET  /api/choreography/songs/
POST /api/choreography/generate-from-song/
POST /api/choreography/describe/
GET  /api/choreography/tasks/{id}/

// Collections
GET  /api/collections/
POST /api/collections/save/
GET  /api/collections/stats/
```

## Environment Variables

Create `.env` file:

```bash
# Development
VITE_API_URL=http://localhost:8000

# Production
VITE_API_URL=https://your-api-url.awsapprunner.com
```

## Architecture Philosophy

This is a "thin" frontend - all business logic lives in Django:

**Frontend Responsibilities:**
- Render UI components
- Handle user interactions
- Make API calls
- Display API data
- Client-side routing
- JWT token management

**NOT Frontend Responsibilities:**
- ❌ Data processing
- ❌ Business rules
- ❌ Complex state management
- ❌ Data validation (beyond UX)

## Deployment

### AWS S3 + CloudFront

```bash
# Build for production
npm run build

# Deploy to S3
aws s3 sync dist/ s3://your-bucket/

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/*"
```

### Docker (Alternative)

```bash
# Build image
docker build -t bachata-frontend .

# Run container
docker run -p 8080:8080 \
  -e VITE_API_URL=https://your-api-url.com \
  bachata-frontend
```

## Development Tips

### Hot Reload

Vite provides instant hot module replacement (HMR):
- Save file → See changes immediately
- No full page reload
- State preserved

### API Mocking

For frontend-only development:

```javascript
// utils/api.js
const MOCK_MODE = import.meta.env.VITE_MOCK_API === 'true';

if (MOCK_MODE) {
  return mockResponse(endpoint);
}
```

### Debugging

```javascript
// Enable API logging
localStorage.setItem('debug', 'api:*');

// View all API calls in console
```

## Common Issues

### CORS Errors

Ensure backend CORS is configured:

```python
# Django settings.py
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:3000',
]
```

### Token Expiration

Tokens expire after 1 hour. The app automatically refreshes them, but if you see 401 errors:

```javascript
// Clear tokens and re-login
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
```

### Build Errors

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf .vite
```

## Contributing

1. Follow React best practices
2. Use functional components with hooks
3. Keep components small and focused
4. Use Tailwind for styling (no custom CSS)
5. Test with real API, not mocks

## License

[Your License]
