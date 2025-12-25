#!/bin/bash
set -e

echo "🚀 Starting Langflow server..."
# Run uvicorn directly with setup_app (includes frontend static files)
# setup_app uses LANGFLOW_FRONTEND_PATH env var or defaults to bundled frontend
exec python -m uvicorn \
    --factory langflow.main:setup_app \
    --host 0.0.0.0 \
    --port 7860 \
    --workers 1 \
    --loop asyncio
