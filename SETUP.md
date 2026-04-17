# MediAssist AI - Setup & Integration Guide

## 🎯 Project Overview

MediAssist AI is an intelligent healthcare support system combining:
- **Frontend**: React + Vite + Tailwind CSS (Modern, responsive UI)
- **Backend**: FastAPI + Python (RAG pipeline with LLM integration)
- **AI Features**: Intent detection, sentiment analysis, urgency classification, appointment booking

## 📋 Prerequisites

### Backend Requirements
- Python 3.8+
- pip (Python package manager)

### Frontend Requirements
- Node.js 16+ 
- npm or yarn

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload --port 8000
```

The backend will be available at: `http://localhost:8000`

Test the health endpoint:
```bash
curl http://localhost:8000/
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at: `http://localhost:5173`

## 🔌 Frontend-Backend Connection

### API Configuration

The frontend automatically connects to the backend using:
- **Default Backend URL**: `http://127.0.0.1:8000`

To use a different backend URL, set the environment variable:

```bash
# In frontend/.env or .env.local
VITE_API_URL=http://your-backend-url:8000
```

### API Endpoints

#### Chat Endpoint
- **URL**: `/chat`
- **Method**: `POST`
- **Request**:
  ```json
  {
    "message": "I have a headache",
    "session_id": "session_123456789_abcdef"
  }
  ```
- **Response**:
  ```json
  {
    "answer": "Based on your symptoms...",
    "intent": "symptom_inquiry",
    "confidence": 0.95,
    "urgency": "low",
    "emotion": "concerned",
    "resolved": false,
    "sources": ["Medical Knowledge Base"],
    "booking_status": "none",
    "booking_id": "",
    "booked_slot": "",
    "booked_department": "",
    "patient_name": ""
  }
  ```

#### Metrics Endpoint
- **URL**: `/metrics`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "resolution_rate": 85,
    "total_queries": 150,
    "resolved_queries": 128,
    "emergency_cases_flagged": 12
  }
  ```

## 🎨 Frontend Features

### Enhanced UI Components

1. **Header & Navigation**
   - API health status indicator
   - Session ID display
   - Live connection indicator

2. **Dashboard**
   - Real-time metrics with animations
   - System status monitoring
   - Performance indicators

3. **Chat Interface**
   - Beautiful message bubbles
   - Typing indicators
   - AI confidence scores
   - Intent and urgency tags
   - Source citations
   - Copy to clipboard
   - Clear conversation button

4. **Features Section**
   - Clinical Support card
   - Real-time Analytics card
   - Security & Privacy card

5. **Footer**
   - Product links
   - Developer documentation
   - Company information
   - Legal links
   - Social media

### Visual Enhancements

- **Gradient Backgrounds**: Dynamic color schemes
- **Glass Morphism**: Modern frosted glass effects
- **Animations**: Smooth transitions and loading states
- **Responsive Design**: Mobile, tablet, and desktop optimized
- **Dark Theme**: Easy on the eyes with cyan/blue accents

## 🔧 Troubleshooting

### Frontend Can't Connect to Backend

**Error**: "Connection Issue - Cannot connect to the backend API"

**Solutions**:
1. Make sure backend is running on port 8000
2. Check if CORS is enabled (it is by default)
3. Verify API URL in browser console (F12)
4. Set `VITE_API_URL` if using different hostname

```bash
# Check if backend is running
curl http://127.0.0.1:8000/

# If running on different machine, update frontend .env
VITE_API_URL=http://your-server-ip:8000
```

### Slow API Responses

The frontend has built-in retry logic and timeout handling:
- **Timeout**: 15 seconds per request
- **Retries**: 2 automatic retries on failure
- **Fallback**: Graceful error messages

### Session Management

Sessions are stored in browser memory:
- **Storage**: sessionStorage (cleared on browser close)
- **Session ID**: Auto-generated and persists during session
- **Message History**: Automatically saved and restored

## 📊 Backend Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# API Settings
API_PORT=8000
API_HOST=0.0.0.0

# LLM Configuration
LLM_PROVIDER=google  # or anthropic
GOOGLE_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Vector Database
FAISS_INDEX_PATH=./data/faiss_index
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Starting with Production Flags

```bash
# Without debug output
uvicorn main:app --port 8000

# With specific workers
uvicorn main:app --workers 4 --port 8000
```

## 🧪 Testing

### Frontend Health Check

Open browser console (F12) and run:
```javascript
fetch('http://127.0.0.1:8000/').then(r => r.json()).then(console.log)
```

### Send Test Message

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are symptoms of fever?",
    "session_id": "test_session_123"
  }'
```

### Get Metrics

```bash
curl http://127.0.0.1:8000/metrics
```

## 📱 Responsive Design

The frontend is optimized for:
- **Mobile**: < 640px
- **Tablet**: 640px - 1024px  
- **Desktop**: > 1024px

Test responsiveness by resizing browser window or using DevTools device emulation.

## 🚢 Deployment

### Frontend (Vercel/Netlify)

```bash
npm run build
# Deploy the 'dist' folder
```

### Backend (Heroku/Railway/DigitalOcean)

```bash
# Ensure Procfile exists
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Then update frontend `.env`:
```
VITE_API_URL=https://your-backend-domain.com
```

## 📚 Additional Resources

- [React Documentation](https://react.dev)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Tailwind CSS](https://tailwindcss.com)
- [Vite Guide](https://vitejs.dev)

## ✨ Features Added in This Update

### Frontend Enhancements
✅ API health check on startup
✅ Connection status indicator
✅ Enhanced error messages
✅ Loading states with animations
✅ Copy message to clipboard
✅ Clear conversation button
✅ Improved meta information display
✅ Better message styling
✅ Features showcase section
✅ Professional footer
✅ Comprehensive CSS animations
✅ Glass morphism effects
✅ Gradient text effects
✅ Responsive grid layouts
✅ Session management

### Backend Integration
✅ CORS properly configured
✅ Error handling with fallbacks
✅ Retry logic for failed requests
✅ Timeout protection
✅ Health check endpoint
✅ Metrics endpoint connection

## 🤝 Support

For issues or questions:
1. Check the Troubleshooting section
2. Review console logs (Frontend: F12, Backend: terminal)
3. Verify API connectivity
4. Check environment variables

---

**Last Updated**: April 2024
**Version**: 1.0.0
