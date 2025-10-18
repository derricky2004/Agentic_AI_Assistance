# Dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# dependencies (only requests is needed for LLM mode; safe to install)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt || true

# app code
COPY core /app/core
COPY README.md /app/README.md
COPY docs /app/docs

# default: rule-based mode
ENV USE_LLM=0
CMD ["python", "-m", "core.cli", "--mode", "rule"]
