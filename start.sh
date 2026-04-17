#!/bin/bash
# Quick Start Script for MediAssist AI
# This script sets up and runs both backend and frontend

set -e

echo "🏥 MediAssist AI - Quick Start"
echo "=============================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is already running
check_backend() {
  echo -e "${BLUE}Checking if backend is running...${NC}"
  if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is already running${NC}"
    return 0
  else
    echo -e "${YELLOW}✗ Backend is not running${NC}"
    return 1
  fi
}

# Start backend
start_backend() {
  echo -e "${BLUE}Starting backend...${NC}"
  cd backend
  
  # Check if virtual environment exists
  if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
  fi
  
  # Activate virtual environment
  source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null
  
  # Install dependencies
  echo -e "${YELLOW}Installing backend dependencies...${NC}"
  pip install -r requirements.txt > /dev/null 2>&1
  
  echo -e "${GREEN}✓ Backend dependencies installed${NC}"
  echo -e "${BLUE}Starting FastAPI server...${NC}"
  
  # Start backend in the background
  uvicorn main:app --reload --port 8000 &
  BACKEND_PID=$!
  echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
  
  # Give backend time to start
  sleep 3
  
  cd ..
}

# Start frontend
start_frontend() {
  echo -e "${BLUE}Starting frontend...${NC}"
  cd frontend
  
  # Check if node_modules exists
  if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
  fi
  
  echo -e "${GREEN}✓ Frontend dependencies ready${NC}"
  echo -e "${BLUE}Starting Vite dev server...${NC}"
  
  npm run dev
  
  cd ..
}

# Main logic
echo ""
if ! check_backend; then
  start_backend
else
  echo ""
fi

echo ""
echo -e "${YELLOW}Starting frontend...${NC}"
echo ""

start_frontend
