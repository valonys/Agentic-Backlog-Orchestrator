#!/bin/bash

# Backlog Inspector Dashboard - macOS Setup Script
# Makes setup easy on MacBook Pro

set -e

echo "🔍 Backlog Inspector Dashboard - Setup Script"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ This script is designed for macOS${NC}"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
echo "📋 Checking prerequisites..."
if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    echo "Install with: brew install python@3.11"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"

# Check Node.js
if ! command_exists node; then
    echo -e "${RED}❌ Node.js not found${NC}"
    echo "Install with: brew install node"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js $NODE_VERSION found${NC}"

# Check npm
if ! command_exists npm; then
    echo -e "${RED}❌ npm not found${NC}"
    exit 1
fi

NPM_VERSION=$(npm --version)
echo -e "${GREEN}✅ npm $NPM_VERSION found${NC}"

echo ""
echo "🎯 Setup Options:"
echo "1) Quick Setup (Docker)"
echo "2) Manual Setup (Python venv + npm)"
echo "3) Generate Test Data Only"
echo "4) Exit"
echo ""
read -p "Select option (1-4): " option

case $option in
    1)
        echo ""
        echo "🐳 Docker Setup"
        echo "==============="
        
        if ! command_exists docker; then
            echo -e "${RED}❌ Docker not found${NC}"
            echo "Install from: https://docs.docker.com/desktop/mac/install/"
            exit 1
        fi
        
        # Check for .env file
        if [ ! -f "backend/.env" ]; then
            echo -e "${YELLOW}⚠️  No .env file found${NC}"
            cp backend/.env.example backend/.env
            echo "Created backend/.env from template"
            echo ""
            echo -e "${YELLOW}⚠️  IMPORTANT: Edit backend/.env and add your OPENROUTER_API_KEY${NC}"
            read -p "Press Enter after adding your API key..."
        fi
        
        echo "Starting services with Docker Compose..."
        docker-compose up --build -d
        
        echo ""
        echo -e "${GREEN}✅ Services started!${NC}"
        echo "Backend: http://localhost:8000"
        echo "Frontend: http://localhost:5173"
        echo ""
        echo "View logs: docker-compose logs -f"
        echo "Stop services: docker-compose down"
        ;;
        
    2)
        echo ""
        echo "🔧 Manual Setup"
        echo "==============="
        
        # Backend setup
        echo ""
        echo "📦 Setting up backend..."
        cd backend
        
        if [ ! -d "venv" ]; then
            echo "Creating virtual environment..."
            python3 -m venv venv
        fi
        
        echo "Activating virtual environment..."
        source venv/bin/activate
        
        echo "Installing Python dependencies..."
        pip install --upgrade pip
        pip install -r requirements.txt
        
        if [ ! -f ".env" ]; then
            cp .env.example .env
            echo ""
            echo -e "${YELLOW}⚠️  Created backend/.env from template${NC}"
            echo -e "${YELLOW}⚠️  IMPORTANT: Edit backend/.env and add your OPENROUTER_API_KEY${NC}"
            read -p "Press Enter after adding your API key..."
        fi
        
        echo ""
        echo "Starting backend server..."
        python main.py &
        BACKEND_PID=$!
        cd ..
        
        # Frontend setup
        echo ""
        echo "📦 Setting up frontend..."
        cd frontend
        
        if [ ! -d "node_modules" ]; then
            echo "Installing npm dependencies..."
            npm install
        fi
        
        if [ ! -f ".env" ]; then
            cp .env.example .env
            echo "Created frontend/.env"
        fi
        
        echo ""
        echo "Starting frontend server..."
        npm run dev &
        FRONTEND_PID=$!
        cd ..
        
        echo ""
        echo -e "${GREEN}✅ Services started!${NC}"
        echo "Backend: http://localhost:8000 (PID: $BACKEND_PID)"
        echo "Frontend: http://localhost:5173 (PID: $FRONTEND_PID)"
        echo ""
        echo "To stop services:"
        echo "  kill $BACKEND_PID $FRONTEND_PID"
        echo ""
        echo "Opening browser in 3 seconds..."
        sleep 3
        open http://localhost:5173
        ;;
        
    3)
        echo ""
        echo "📊 Generating Test Data"
        echo "======================="
        
        if [ -f "generate_test_data.py" ]; then
            python3 generate_test_data.py
            echo ""
            echo -e "${GREEN}✅ Test data generated: sample_backlog_data.xlsx${NC}"
        else
            echo -e "${RED}❌ generate_test_data.py not found${NC}"
        fi
        ;;
        
    4)
        echo "Exiting..."
        exit 0
        ;;
        
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo "🎉 Setup complete!"
