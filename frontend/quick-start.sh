#!/bin/bash

# Resume Pipeline Frontend - Quick Start Script
# This script helps you get the frontend running quickly

set -e

echo "================================================"
echo "Resume Pipeline Frontend - Quick Start"
echo "================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found"
    echo "Please run this script from the resume-frontend directory"
    exit 1
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Error: Node.js version must be 18 or higher"
    echo "Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v) detected"
echo ""

# Check for npm
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed"
    exit 1
fi

echo "✅ npm $(npm -v) detected"
echo ""

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
fi

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies (this may take a few minutes)..."
    npm install
    echo "✅ Dependencies installed"
    echo ""
else
    echo "✅ Dependencies already installed"
    echo ""
fi

# Check if backend is running
echo "🔍 Checking backend connection..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend API is running on http://localhost:8000"
    echo ""
else
    echo "⚠️  Warning: Backend API is not responding on http://localhost:8000"
    echo ""
    echo "To start the backend:"
    echo "  cd /path/to/resume-pipeline"
    echo "  docker-compose up api redis worker"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "================================================"
echo "🚀 Starting Development Server"
echo "================================================"
echo ""
echo "Frontend will be available at: http://localhost:3000"
echo "Backend API endpoint: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
sleep 2

# Start the development server
npm run dev
