# AI Interview Platform - React Frontend

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm/yarn
- Backend server running on port 5000

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable React components
│   │   ├── Layout.jsx       # Main layout with navigation
│   │   ├── ProtectedRoute.jsx
│   │   ├── LoadingSpinner.jsx
│   │   └── ErrorBoundary.jsx
│   ├── contexts/            # React Context providers
│   │   ├── AppStateContext.jsx  # Centralized state management
│   │   └── WebSocketContext.jsx # WebSocket connection & rehydration
│   ├── pages/               # Page components
│   │   ├── LoginPage.jsx
│   │   ├── DashboardPage.jsx
│   │   ├── CodingPage.jsx
│   │   ├── CodingQuestionPage.jsx
│   │   ├── InterviewPage.jsx
│   │   └── ...
│   ├── services/            # API clients
│   │   └── api.js           # Centralized API service
│   ├── App.jsx              # Main app component with routing
│   ├── main.jsx             # Entry point
│   └── index.css            # Global styles
├── package.json
├── vite.config.js           # Vite configuration
└── index-react.html          # HTML template
```

## 🎯 Key Features

### ✅ State Management
- **React Context API** for centralized state
- Single source of truth
- Immutable state updates
- No race conditions

### ✅ Routing
- **React Router** with History API
- Protected routes
- No hash routing bugs
- Proper back/forward button support

### ✅ WebSocket Integration
- Automatic reconnection
- State rehydration from backend
- Interview state persistence

### ✅ API Integration
- Centralized API client
- Automatic token refresh
- Error handling
- Request/response interceptors

## 🔧 Development

### Environment Variables
Create `.env` file:
```
VITE_API_URL=http://localhost:5000
```

### Available Scripts
- `npm run dev` - Start dev server (port 3000)
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## 🏗️ Build Output

Production build outputs to `../dist/` directory for Flask to serve.

## 📝 Migration Notes

This React frontend replaces the vanilla JavaScript implementation:
- ✅ No more blank pages
- ✅ No rendering conflicts
- ✅ No navigation bugs
- ✅ Proper state management
- ✅ Better error handling
- ✅ Improved UX
