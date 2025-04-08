# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Install build dependencies first - these change less frequently
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install poetry with pip - separate layer for package manager
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false

# Copy dependency files only
COPY pyproject.toml poetry.lock* ./

# Install dependencies - will be cached unless poetry files change
RUN poetry install --no-interaction --no-ansi --no-root --no-cache

# Copy project code - this layer changes most frequently
COPY yubarta ./yubarta

# Commented temporarily because this command only would start one of the 3 containers
# that requires a start up command. We need to create a target in the Make file to start
# the orchestrator and worker and this target has to be invoked here.
# CMD ["uvicorn", "yubarta.main:app", "--host", "0.0.0.0", "--port", "8080"]
