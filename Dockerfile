FROM python:3.12-slim
WORKDIR /app
COPY voltra_local /app/voltra_local
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "voltra_local.app"]
