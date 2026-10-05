FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY voltra_local /app/voltra_local

RUN mkdir -p /app/data

EXPOSE 8086 10086

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8086/health', timeout=2).read()" || exit 1

CMD ["python", "-m", "voltra_local.app"]
