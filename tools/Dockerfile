FROM python:3.12-slim AS base

WORKDIR /app

# Install ffmpeg (required for audio processing) and Poetry
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir poetry==1.8.* && \
    poetry config virtualenvs.create false

# Install podcast_renderer first (dependency)
COPY podcast_renderer/pyproject.toml /app/podcast_renderer/pyproject.toml
COPY podcast_renderer/podcast_renderer/ /app/podcast_renderer/podcast_renderer/
COPY podcast_renderer/README.md /app/podcast_renderer/README.md
RUN cd /app/podcast_renderer && poetry install --only main --no-interaction

# Copy pipeline_runner dependency files (Docker cache layer)
COPY tools/pyproject.toml ./

# Install production dependencies
RUN poetry install --only main --no-root --no-interaction

# Copy source
COPY tools/pipeline_runner/ pipeline_runner/

# Install the package itself
RUN poetry install --only main --no-interaction

# --- Test stage ---
FROM base AS test

RUN poetry install --no-interaction

COPY tools/tests/ tests/

CMD ["sh", "-c", "python -m pytest tests/ -v --tb=short && python -m ruff check pipeline_runner/"]

# --- Production stage ---
FROM base AS production

ENTRYPOINT ["python", "-m", "pipeline_runner.cli"]
CMD ["--help"]
