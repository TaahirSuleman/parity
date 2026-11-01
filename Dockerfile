# syntax=docker/dockerfile:1
# Two stages (spec §12): Node builds the workbench; the Playwright image runs the API with Chromium already installed.
# Cloud Build builds this; Docker is not needed on a laptop.

FROM node:26-bookworm-slim AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build   # vite writes ../parity/static

FROM mcr.microsoft.com/playwright/python:v1.64.1-noble
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PARITY_INDEX_PATH=/tmp/index.db PARITY_CACHE_DIR=/tmp/cache PARITY_DEFAULT_MODE=replay PARITY_TRUST_PROXY=1
WORKDIR /app
COPY pyproject.toml README.md HACKATHON_SCOPE.md ./
COPY parity/ parity/
COPY store/ store/
COPY fixtures/replay/ fixtures/replay/
COPY eval/results/ eval/results/
COPY --from=web /src/parity/static parity/static
COPY --from=web /src/web/node_modules/axe-core/axe.min.js parity/vendor/axe.min.js
# Editable install: the app resolves store/, fixtures/ and eval/ relative to its own source tree.
RUN pip install -e . && python -c "import parity, playwright; print('parity', parity.__version__)"
EXPOSE 8080
CMD ["sh", "-c", "uvicorn parity.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8080}"]
