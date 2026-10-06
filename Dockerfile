FROM node:22-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html ./
COPY frontend/src ./src

RUN npm install --no-audit --no-fund \
    && npm run build


FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY voltra_local /app/voltra_local
COPY --from=frontend-build /frontend/dist /app/voltra_local/web

RUN mkdir -p /app/data

EXPOSE 8086 10086

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8086/health', timeout=2).read()" || exit 1

CMD ["python", "-m", "voltra_local.app"]
