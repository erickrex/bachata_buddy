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
VITE_API_URL=https://your-app-runner-service-url.us-east-1.awsapprunner.com
```

See `.env.example` for all available environment variables.

## Deployment

### AWS Deployment (Production)

The frontend is deployed to AWS using the following architecture:

1. **Build**: Static files are built using Vite (`npm run build`)
2. **Storage**: Built files are uploaded to an S3 bucket
3. **CDN**: CloudFront distribution serves the files globally
4. **Infrastructure**: Managed via AWS CDK (TypeScript)

**Deployment Steps:**

```bash
# 1. Set the API URL for production
export VITE_API_URL=https://your-app-runner-service-url.us-east-1.awsapprunner.com

# 2. Build the frontend
npm run build

# 3. Deploy using AWS CDK (from infrastructure directory)
cd ../../infrastructure
cdk deploy FrontendStack
```

The CDK stack will:
- Create an S3 bucket for static files
- Create a CloudFront distribution
- Upload the built files to S3
- Configure caching and security headers

See the `infrastructure/` directory for CDK configuration.

### Docker Deployment (Alternative)

The frontend can also be deployed as a containerized application using the production `Dockerfile`:

```bash
# Build the Docker image
docker build -t bachata-frontend .

# Run the container
docker run -p 8080:8080 -e VITE_API_URL=https://your-api-url.com bachata-frontend
```

This serves the static files using nginx.

## Architecture Philosophy

This is a "dumb" frontend - all business logic lives in Django. React is only responsible for:

- Rendering UI components
- Handling user interactions
- Making API calls
- Displaying data from the API
- Client-side routing

No complex state management, no data processing, no business rules.
