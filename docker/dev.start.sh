#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════════════════════════
# TRUE DEV HOT RELOAD STARTUP SCRIPT
# 
# Runs TWO servers:
#   1. Uvicorn (port 7860) - Backend with --reload for Python hot reload
#   2. Vite dev server (port 3000) - Frontend with HMR hot reload
#
# Vite proxies /api/* requests to the backend automatically (see vite.config.mts)
# Access the app at: http://localhost:3001 (maps to Vite on port 3000)
# ═══════════════════════════════════════════════════════════════════════════════

echo "════════════════════════════════════════════════════════════════════"
echo "  🔧 DEVELOPMENT MODE - Full Hot Reload"
echo "════════════════════════════════════════════════════════════════════"
echo ""

cd /app

# Ensure Python dependencies are installed
echo "📦 Syncing Python dependencies..."
uv sync --frozen --extra postgresql

# Start backend first (in background) using uv run to access venv
echo ""
echo "🚀 Starting backend server (port 7860) with hot reload..."
uv run uvicorn \
    --factory langflow.main:create_app \
    --host 0.0.0.0 \
    --port 7860 \
    --reload \
    --reload-dir /app/src/backend \
    --loop asyncio &

BACKEND_PID=$!

# Wait a moment for backend to start
echo "   Waiting for backend to initialize..."
sleep 5

# Test if backend is up
if curl -s http://localhost:7860/health > /dev/null 2>&1; then
    echo "   ✅ Backend is running on port 7860"
else
    echo "   ⚠️  Backend may still be starting..."
fi

# Start frontend (in foreground - this keeps the container running)
echo ""
echo "🎨 Starting frontend dev server (port 3000) with HMR..."
echo ""
echo "   ┌─────────────────────────────────────────────────────────────┐"
echo "   │  Frontend: http://localhost:3001 (Vite + HMR)              │"
echo "   │  Backend:  http://localhost:7860 (internal, via proxy)     │"
echo "   │                                                             │"
echo "   │  Frontend changes: Instant HMR (no refresh needed)         │"
echo "   │  Backend changes:  Auto-reload (may take a few seconds)    │"
echo "   └─────────────────────────────────────────────────────────────┘"
echo ""

cd /app/src/frontend
npm install
exec npm run dev:docker
