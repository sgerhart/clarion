#!/bin/bash
#
# Setup React Frontend
#
# Installs dependencies and prepares the frontend for development.
#

set -e

cd "$(dirname "$0")/../frontend"

echo "🚀 Setting up Clarion React Frontend..."
echo ""

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ is required. Current: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v) detected"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install

echo ""
echo "✅ Frontend setup complete!"
echo ""
echo "To start the development server:"
echo "  cd frontend && npm run dev"
echo ""
echo "The frontend will be available at: http://localhost:3000"
echo "Make sure the backend API is running on: http://localhost:8000"

