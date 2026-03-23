FROM python:3.12-slim AS base

WORKDIR /app

# Install ffmpeg (required for audio processing) and Poetry
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir poetry==1.8.* && \
    poetry config virtualenvs.create false

# Copy dependency files first (Docker cache layer)
COPY pyproject.toml ./

# Install production dependencies
RUN poetry install --only main --no-root --no-interaction

# Copy source
COPY pipeline_runner/ pipeline_runner/

# Install the package itself
RUN poetry install --only main --no-interaction

# --- Test stage ---
FROM base AS test

# Install dev dependencies
RUN poetry install --no-interaction

COPY tests/ tests/

# Run tests and lint
CMD ["sh", "-c", "python -m pytest tests/ -v --tb=short && python -m ruff check pipeline_runner/"]

# --- Production stage ---
FROM base AS production

ENTRYPOINT ["python", "-m", "pipeline_runner.cli"]
CMD ["--help"]
