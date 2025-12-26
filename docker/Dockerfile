# STAGE 1: Build Docs, Coverage, and Artifacts
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

# 1. Run Tests
# 2. Build Docs
# 3. Build Library (creates /app/dist containing .whl and .tar.gz)
RUN uv run pytest --cov=src --cov-report=html && \
    uv run mkdocs build && \
    uv build

# STAGE 2: Serve with Nginx
FROM nginx:alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Copy Doc Site
COPY --from=builder /app/site /usr/share/nginx/html
# Copy Coverage Report
COPY --from=builder /app/htmlcov /usr/share/nginx/html/coverage
# Copy Build Artifacts (Wheels/Tarballs)
COPY --from=builder /app/dist /usr/share/nginx/html/dist

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
