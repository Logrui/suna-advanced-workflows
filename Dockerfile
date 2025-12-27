# syntax=docker/dockerfile:1
################################
# STAGE 1: Frontend Builder
################################
FROM node:18-slim AS frontend-builder
WORKDIR /build

# Build arguments for Vite environment variables
# These must be passed during `docker build` or via docker-compose build args
# CRITICAL: These get BAKED INTO the JavaScript bundle at build time
ARG VITE_EXTERNAL_COMPOSIO_PROFILES_BACKEND_URL=""
ARG BACKEND_URL="http://localhost:7860"
ARG LANGFLOW_AUTO_LOGIN="false"
ARG LANGFLOW_MCP_COMPOSER_ENABLED="true"

# Expose as environment variables for Vite to pick up during build
# vite.config.mts reads these via dotenv or process.env
ENV VITE_EXTERNAL_COMPOSIO_PROFILES_BACKEND_URL=${VITE_EXTERNAL_COMPOSIO_PROFILES_BACKEND_URL}
ENV BACKEND_URL=${BACKEND_URL}
ENV LANGFLOW_AUTO_LOGIN=${LANGFLOW_AUTO_LOGIN}
ENV LANGFLOW_MCP_COMPOSER_ENABLED=${LANGFLOW_MCP_COMPOSER_ENABLED}

COPY src/frontend/package*.json ./
RUN npm ci
COPY src/frontend/ ./

# ═══════════════════════════════════════════════════════════════════════════════
# BUILD-TIME VARIABLE AUDIT
# These values are BAKED INTO the JavaScript bundle - visible in build output
# ═══════════════════════════════════════════════════════════════════════════════
RUN echo "╔══════════════════════════════════════════════════════════════════════╗" && \
    echo "║ 🔍 BUILD-TIME ENVIRONMENT VARIABLES AUDIT                          ║" && \
    echo "╠══════════════════════════════════════════════════════════════════════╣" && \
    echo "║ VITE_EXTERNAL_COMPOSIO_PROFILES_BACKEND_URL: ${VITE_EXTERNAL_COMPOSIO_PROFILES_BACKEND_URL:-[NOT SET]}" && \
    echo "║ BACKEND_URL: ${BACKEND_URL:-[NOT SET]}" && \
    echo "║ LANGFLOW_AUTO_LOGIN: ${LANGFLOW_AUTO_LOGIN:-[NOT SET]}" && \
    echo "║ LANGFLOW_MCP_COMPOSER_ENABLED: ${LANGFLOW_MCP_COMPOSER_ENABLED:-[NOT SET]}" && \
    echo "╚══════════════════════════════════════════════════════════════════════╝"

# Build the production or staging assets (Vite will bake env vars into the bundle via define:{})
RUN npm run build

################################
# STAGE 2: Backend & Environment Builder
################################
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY pyproject.toml uv.lock README.md ./
COPY src/backend/base/pyproject.toml src/backend/base/
COPY src/backend/base/uv.lock src/backend/base/
COPY src/backend/base/README.md src/backend/base/
COPY src/lfx/pyproject.toml src/lfx/
COPY src/lfx/README.md src/lfx/

# Sync dependencies (including LFX and local backend base)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-editable --extra postgresql

# Copy the source code
COPY ./src ./src
COPY ./scripts ./scripts

# Bundle the Frontend Assets into the correct Backend location
COPY --from=frontend-builder /build/build /app/src/backend/base/langflow/frontend

# Install the project into the virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --extra postgresql

# Build the Component Index (Crucial for Kortix components to show up)
RUN uv run python scripts/build_component_index.py

################################
# STAGE 3: Final Runtime
################################
FROM python:3.12-slim AS runtime
WORKDIR /app

# Install runtime dependencies (libpq for postgres)
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"

# Copy startup script
COPY docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Environment configuration
ENV LANGFLOW_HOST=0.0.0.0
ENV LANGFLOW_PORT=7860
ENV LANGFLOW_DATABASE_URL=sqlite:////app/data/langflow.db
ENV LANGFLOW_FRONTEND_PATH=/app/src/backend/base/langflow/frontend

EXPOSE 7860

# Run using the startup script
CMD ["/app/start.sh"]