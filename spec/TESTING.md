# Test Strategy

## Unit Tests

Framework: **pytest** with mocked MLX packages (since CI runs on Linux).

```bash
# Run locally
cd tools && pytest tests/ -v

# Run via Docker
docker compose run --rm --profile test pipeline-test
```

### Mocking Strategy

MLX packages (mlx-audio, f5-tts-mlx, mlx-whisper) are unavailable on Linux CI runners. Tests mock these at the import level:

- `pipeline_runner/tts/mlx_audio_engine.py` — Mock `mlx_audio` and model loading.
- `pipeline_runner/tts/f5_tts_engine.py` — Mock `f5_tts_mlx` inference.
- Transcription steps — Mock `mlx_whisper.transcribe`.

Tests validate logic, context flow, and error handling without requiring Apple Silicon.

### Key Test Areas

- Step protocol compliance (`should_run`, `execute`, context passing)
- Pipeline orchestration (ordering, skip logic, error propagation)
- Config loading and validation (`podcast.json` parsing)
- ffmpeg command construction (loudness normalization, crossfade, format conversion)
- TTS engine abstraction (engine selection, fallback behavior)
- RSS feed generation (template rendering, episode metadata)
- IAMQ client (registration, heartbeat, message sending)
- CLI argument parsing and command routing

## Pipeline Integration Tests

Test full pipeline execution with mocked external dependencies (Ollama, TTS, ffmpeg).

- Script pipeline: mock Ollama response, verify script output.
- Voice pipeline: mock TTS engine, verify audio file creation.
- Cleanup pipeline: mock ffmpeg, verify normalization commands.
- Assembly pipeline: mock ffmpeg + whisper, verify episode structure.
- Distribute pipeline: mock file I/O, verify RSS update and IAMQ announcement.
- Episode pipeline: end-to-end with all mocks, verify per-language loop.

## CI Matrix

GitHub Actions (`.github/workflows/ci.yml`):

| Job | Python | What |
|-----|--------|------|
| test-3.12 | 3.12 | pytest + lint + type check |
| test-3.13 | 3.13 | pytest + lint + type check |
| docker-build | N/A | Build all Dockerfile targets (base, test, production) |
| secrets-scan | N/A | Block hardcoded credentials and local paths |

### Lint and Type Check

```bash
ruff check pipeline_runner/
ruff format --check pipeline_runner/
mypy pipeline_runner/
```

## Docker Build Validation

CI builds all three Dockerfile stages to catch build regressions:

- `base` — Python + ffmpeg + dependencies
- `test` — base + dev dependencies + pytest
- `production` — base + entrypoint

## Smoke Test Checklist

Manual verification before deploying changes:

- [ ] `docker compose build` succeeds for all targets
- [ ] `docker compose up -d scheduler` starts without errors
- [ ] `docker compose exec scheduler pipeline validate` passes
- [ ] `docker compose exec scheduler pipeline generate-script --topics "test"` produces a script
- [ ] `pipeline list-voices` shows configured voice references
- [ ] `pipeline voice-preview --text "Hello" --lang en` generates audio (Apple Silicon only)
- [ ] IAMQ heartbeat visible: `curl http://127.0.0.1:18790/agents` shows `podcast_agent`
- [ ] Generated episode appears in `output/episodes/`
- [ ] RSS feed updates at `output/feed.xml`
