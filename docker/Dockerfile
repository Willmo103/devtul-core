# STAGE 1: Build Docs, Coverage, and Artifacts
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

# Build everything
# Note: We build mkdocs, but Nginx will move it to /docs later
RUN uv run pytest --cov=src --cov-report=html && \
    uv run mkdocs build && \
    uv build

# STAGE 2: Serve with Nginx
FROM nginx:alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# 1. Landing Page
COPY docker/index.html /usr/share/nginx/html/index.html

# 2. Docs (Move site to /docs folder)
COPY --from=builder /app/site /usr/share/nginx/html/docs

# 3. Coverage
COPY --from=builder /app/htmlcov /usr/share/nginx/html/coverage

# 4. Artifacts
COPY --from=builder /app/dist /usr/share/nginx/html/dist

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
