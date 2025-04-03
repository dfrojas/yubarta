# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Set environment
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Install OS deps
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

# Copy only necessary files for dependency installation
COPY pyproject.toml ./
COPY poetry.lock* ./
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root

# Copy project code
COPY yubarta ./yubarta

# Commented temporarily because this command only would start one of the 3 containers
# that requires a start up command. We need to create a target in the Make file to start
# the orchestrator and worker and this target has to be invoked here.
# CMD ["uvicorn", "yubarta.main:app", "--host", "0.0.0.0", "--port", "8080"]
