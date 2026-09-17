# syntax=docker/dockerfile:1

FROM python:3.12-slim AS python-api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Package manager in its own layer so dependency installs stay cached.
RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-interaction --no-ansi --no-root --no-cache

# Project code last: it changes on every build, dependencies do not.
COPY alembic.ini inventory.yaml ./
COPY yubarta ./yubarta
COPY dev ./dev

CMD ["uvicorn", "yubarta.main:app", "--host", "0.0.0.0", "--port", "8080"]
