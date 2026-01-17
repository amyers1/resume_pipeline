# Resume Pipeline Frontend

A modern, responsive React frontend for the AI-powered resume generation pipeline. Built with React 18, Vite, Tailwind CSS, and featuring real-time job monitoring via Server-Sent Events (SSE).

## ✨ Features

- **Real-Time Monitoring**: Live progress tracking with SSE for job generation
- **Dark/Light Mode**: Automatic theme switching with system preference support
- **Responsive Design**: Mobile-first design that works on all devices
- **Production-Ready**: Optimized build with code splitting and lazy loading
- **Type-Safe**: Structured data models and API contracts
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Health Monitoring**: System health dashboard with component status

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend API running on port 8000 (default)

### Installation

```bash
# Navigate to frontend directory
cd resume-frontend

# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`

## 📋 Available Scripts

```bash
# Development server with hot reload
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## 🏗️ Project Structure

```
resume-frontend/
├── public/                 # Static assets
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── ArtifactList.jsx      # File download list
│   │   ├── Header.jsx            # App header with navigation
│   │   ├── HealthBadge.jsx       # System health indicator
│   │   ├── JobCard.jsx           # Job preview card
│   │   ├── LiveLog.jsx           # Real-time activity log
│   │   ├── ProgressBar.jsx       # Progress visualization
│   │   └── StageTimeline.jsx     # Pipeline stage tracker
│   ├── contexts/          # React Context for state management
│   │   └── AppContext.jsx        # Global application state
│   ├── hooks/             # Custom React hooks (future)
│   ├── pages/             # Page components
│   │   ├── Dashboard.jsx         # Job list and overview
│   │   ├── JobDetailPage.jsx     # Job monitoring and results
│   │   └── NewJobPage.jsx        # Job submission form
│   ├── services/          # API and external services
│   │   └── api.js                # Axios client and SSE handlers
│   ├── utils/             # Utility functions and constants
│   │   ├── constants.js          # App-wide constants
│   │   └── helpers.js            # Helper functions
│   ├── App.jsx            # Main app component with routing
│   ├── index.css          # Global styles and Tailwind imports
│   └── main.jsx           # React entry point
├── .env.example           # Environment variables template
├── .gitignore
├── index.html             # HTML entry point
├── package.json
├── postcss.config.js      # PostCSS configuration
├── tailwind.config.js     # Tailwind CSS configuration
└── vite.config.js         # Vite bundler configuration
```

## 🎨 Key Components

### Dashboard
- Paginated job list with filtering and sorting
- Search by company name
- Quick actions for job management
- Empty state with call-to-action

### New Job Form
- Multi-section form with validation
- Real-time character count for job description
- Template and backend selection
- Priority slider (0-10)
- Career profile selector

### Job Detail Page
- Real-time progress monitoring with SSE
- Live activity log with auto-scroll
- Pipeline stage visualization
- Download buttons for all generated artifacts
- Quality score and processing time display
- Regenerate and delete actions

### Components

**HealthBadge**: System health indicator with detailed modal
- API status
- RabbitMQ connectivity
- Component-level health checks

**ProgressBar**: Animated progress visualization
- Color-coded by stage
- Percentage display
- Current stage and message

**StageTimeline**: Vertical timeline showing pipeline stages
- Completed, active, pending, and failed states
- Visual icons and connecting lines

**LiveLog**: Terminal-style activity log
- Timestamped events
- Color-coded messages
- Copy to clipboard functionality

**ArtifactList**: File download manager
- File type icons
- Size display
- Preview for JSON files
- Bulk download support

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# API Configuration
VITE_API_URL=http://localhost:8000
```

For production:

```env
VITE_API_URL=https://api.yourproductiondomain.com
```

### API Integration

The frontend communicates with the backend API through:

1. **REST API** for CRUD operations (axios)
2. **Server-Sent Events (SSE)** for real-time updates

All API calls are centralized in `src/services/api.js` for easy maintenance.

## 🎨 Theming

The application supports both light and dark themes:

- Theme preference is stored in localStorage
- Manual toggle in header
- Automatic system preference detection
- Smooth transitions between themes

### Color Palette

Primary colors are defined in `tailwind.config.js` and can be customized:

```javascript
colors: {
  primary: {
    500: '#3b82f6',  // Main brand color
    600: '#2563eb',  // Darker variant
    // ... other shades
  }
}
```

## 📡 Real-Time Features

### Server-Sent Events (SSE)

The frontend uses SSE for real-time job monitoring:

```javascript
// Automatic connection management
const cleanup = createJobStatusSSE(jobId, {
  onMessage: (data) => {
    // Handle progress updates
  },
  onError: (error) => {
    // Handle connection errors
  }
});

// Cleanup on unmount
return () => cleanup();
```

**Features:**
- Automatic reconnection on disconnect
- Progress percentage updates
- Stage transitions
- Terminal state detection (completed/failed)

## 🚀 Production Deployment

### Build for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

### Deployment Options

#### 1. Static Hosting (Netlify, Vercel)

```bash
# Build the app
npm run build

# Deploy dist/ folder to your hosting provider
```

Configure build settings:
- Build command: `npm run build`
- Publish directory: `dist`
- Environment variables: `VITE_API_URL`

#### 2. Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Create `nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Build and run:

```bash
docker build -t resume-frontend .
docker run -p 3000:80 resume-frontend
```

#### 3. Serve with Backend

If deploying with the backend, add to `docker-compose.yml`:

```yaml
services:
  frontend:
    build: ./resume-frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://api:8000
    depends_on:
      - api
```

### CORS Configuration

Ensure the backend API allows the frontend origin in `api.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Development
        "https://yourfrontenddomain.com",  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🧪 Testing

### Manual Testing Checklist

- [ ] Submit a new job with valid data
- [ ] Submit a job with invalid data (validation errors)
- [ ] Monitor job progress in real-time
- [ ] Download generated files
- [ ] Regenerate a completed job
- [ ] Delete a job
- [ ] Search and filter jobs
- [ ] Paginate through job list
- [ ] Toggle dark/light theme
- [ ] Check health badge status
- [ ] Test on mobile device

### Future: Automated Tests

```bash
# Unit tests with Vitest
npm run test

# E2E tests with Playwright
npm run test:e2e
```

## 🐛 Troubleshooting

### Common Issues

**1. API Connection Failed**

```
Error: Failed to fetch jobs
```

- Check that backend API is running on port 8000
- Verify `VITE_API_URL` in `.env`
- Check browser console for CORS errors

**2. SSE Not Connecting**

```
SSE connection error
```

- Ensure backend SSE endpoint is accessible
- Check network tab for 503 errors
- Verify RabbitMQ is running (if enabled)

**3. Build Fails**

```
Error: Cannot find module
```

- Clear node_modules: `rm -rf node_modules`
- Reinstall: `npm install`
- Clear Vite cache: `rm -rf node_modules/.vite`

**4. Dark Mode Not Working**

- Clear localStorage: Open DevTools → Application → Local Storage → Clear
- Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

## 🔐 Security Considerations

- All API calls use the configured `VITE_API_URL`
- File downloads are validated server-side
- No sensitive data stored in localStorage
- CSRF protection handled by backend
- Input validation on all forms

## 📚 Technology Stack

- **React 18** - UI library
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Router v6** - Client-side routing
- **Axios** - HTTP client
- **Server-Sent Events (SSE)** - Real-time updates

## 🤝 Contributing

1. Follow the existing code style
2. Use functional components with hooks
3. Keep components small and focused
4. Add proper error handling
5. Update documentation for new features

## 📄 License

Same as parent project.

## 🆘 Support

For issues and questions:
- Check this README
- Review the backend API specification
- Check browser console for errors
- Review network tab in DevTools

---

**Built with ❤️ for efficient resume generation**
