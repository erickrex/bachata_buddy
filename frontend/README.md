# Bachata Buddy Frontend

React 18.3.1 frontend for the Bachata Buddy choreography generator.

## Technology Stack

- **React 18.3.1** - JavaScript only (NO TypeScript)
- **React Router 6** - Client-side routing
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Fetch API** - HTTP requests (no Axios)

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Local Development (Standalone)

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

The dev server will run at http://localhost:5173

### Docker Development

```bash
# Build the development image
docker build -f Dockerfile.dev -t bachata-frontend-dev .

# Run the container
docker run -p 5173:5173 -v $(pwd):/app -v /app/node_modules bachata-frontend-dev
```

### Docker Compose Development

From the root `bachata_buddy` directory:

```bash
# Start all services including frontend
docker-compose up -d

# View frontend logs
docker-compose logs -f frontend

# Stop services
docker-compose down
```

The frontend will be available at http://localhost:5173

## Project Structure

```
frontend/
├── public/              # Static assets
│   └── index.html
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
│   │   ├── Collections.jsx
│   │   ├── CollectionDetail.jsx
│   │   └── Profile.jsx
│   ├── utils/          # Utility functions
│   │   ├── api.js      # API calls with JWT
│   │   └── auth.js     # Auth helpers
│   ├── App.jsx         # Main app with routing
│   └── main.jsx        # Entry point
├── Dockerfile          # Production build
├── Dockerfile.dev      # Development build
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## API Integration

The frontend communicates with the Django REST API using JWT authentication:

- Access tokens stored in localStorage
- Automatic token refresh on 401 responses
- All API calls use the Fetch API
- CORS configured for local development

## Environment Variables

Create a `.env` file in the frontend directory:

```bash
VITE_API_URL=http://localhost:8000
```

For production:

```bash
VITE_API_URL=https://bachata-api-xxx.run.app
```

## Deployment

The frontend is deployed to Google Cloud Run as a static site served by nginx.

See the production `Dockerfile` for the multi-stage build configuration.

## Architecture Philosophy

This is a "dumb" frontend - all business logic lives in Django. React is only responsible for:

- Rendering UI components
- Handling user interactions
- Making API calls
- Displaying data from the API
- Client-side routing

No complex state management, no data processing, no business rules.
