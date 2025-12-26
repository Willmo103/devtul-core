# STAGE 1: Build Docs and Coverage
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock .python-version ./

# Install dependencies
RUN uv sync --frozen

# Copy source code and tests
COPY . .

# 1. Run Tests to generate htmlcov/
# 2. Build MkDocs to generate site/
RUN uv run pytest --cov=src --cov-report=html && \
    uv run mkdocs build

# STAGE 2: Serve with Nginx
FROM nginx:alpine

# Copy custom nginx config
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built artifacts from builder stage
# Docs go to root /, Coverage goes to /coverage
COPY --from=builder /app/site /usr/share/nginx/html
COPY --from=builder /app/htmlcov /usr/share/nginx/html/coverage

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
