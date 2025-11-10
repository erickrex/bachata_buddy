# Frontend Quick Start Guide

## Testing the Dockerfile.dev

### Option 1: Docker Compose (Recommended)

From the `bachata_buddy` directory:

```bash
# Build the frontend service
docker-compose build frontend

# Start the frontend service
docker-compose up frontend

# Or start all services
docker-compose up -d
```

The frontend will be available at http://localhost:5173

### Option 2: Standalone Docker

From the `bachata_buddy/frontend` directory:

```bash
# Build the development image
docker build -f Dockerfile.dev -t bachata-frontend-dev .

# Run the container with volume mount for hot-reload
docker run -p 5173:5173 \
  -v $(pwd):/app \
  -v /app/node_modules \
  bachata-frontend-dev
```

### Option 3: Native Development (No Docker)

From the `bachata_buddy/frontend` directory:

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

## Verifying the Setup

1. Open http://localhost:5173 in your browser
2. You should see "Bachata Buddy - Choreography Generator - Coming Soon"
3. Changes to files in `src/` should trigger hot-reload

## Next Steps

- Implement authentication pages (Login, Register)
- Create choreography generation form
- Build collections management UI
- Integrate with Django REST API

## Troubleshooting

### Port 5173 already in use

```bash
# Find and kill the process using port 5173
lsof -ti:5173 | xargs kill -9

# Or change the port in vite.config.js
```

### Hot reload not working in Docker

The `vite.config.js` is already configured with `usePolling: true` for Docker compatibility.

### npm install fails

Make sure you're using Node.js 18 or higher:

```bash
node --version
```
