# syntax=docker/dockerfile:1

# Python stage for API service
FROM python:3.12-slim as python-api

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install poetry with pip - separate layer for package manager
RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false

# Copy dependency files only
COPY pyproject.toml poetry.lock ./

# Install dependencies - will be cached unless poetry files change
RUN poetry install --no-interaction --no-ansi --no-root --no-cache

COPY bin/wait-for-it.sh /app/bin/
RUN chmod +x /app/bin/wait-for-it.sh

# # Copy project code - this layer changes most frequently
# COPY yubarta ./yubarta

# Commented temporarily because this command only would start one of the 3 containers
# that requires a start up command. We need to create a target in the Make file to start
# the orchestrator and worker and this target has to be invoked here.
# CMD ["uvicorn", "yubarta.main:app", "--host", "0.0.0.0", "--port", "8080"]

# Rust stage for director service
FROM rust:1.75-slim as rust-director

WORKDIR /app

# Install system dependencies for rdkafka
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    libssl-dev \
    librdkafka-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy Rust project files
COPY yubarta/director/Cargo.toml yubarta/director/Cargo.lock* ./
COPY yubarta/director/src ./src

# Build the Rust application
RUN cargo build --release

# Copy the built binary to a location in PATH
RUN cp target/release/yubarta-director /usr/local/bin/

# Set the default command for Rust container
CMD ["yubarta-director"]
