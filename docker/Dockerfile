# STAGE 1: Build Docs and Coverage
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock .python-version ./

# 1. Install dependencies ONLY (Ignore the project for now)
#    This prevents the error because it won't look for src/ yet.
RUN uv sync --frozen --no-install-project

# Copy source code and tests
COPY . .

# 2. NOW install the project itself
#    The src/ folder exists now, so this will succeed.
RUN uv sync --frozen

# 3. Run Tests and Build Docs
RUN uv run pytest --cov=src --cov-report=html && \
    uv run mkdocs build

# STAGE 2: Serve with Nginx
FROM nginx:alpine

# Copy custom nginx config
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built artifacts from builder stage
COPY --from=builder /app/site /usr/share/nginx/html
COPY --from=builder /app/htmlcov /usr/share/nginx/html/coverage

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
