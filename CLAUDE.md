# CLAUDE.md - Developer Guide

This file is for **you** (Claude Code / developer agents), NOT the Podcaster agent.
The Podcaster reads `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, `TOOLS.md`, and `HEARTBEAT.md`.

## What Is This Repo?

The **Openclaw Podcast Agent** is an autonomous podcast production system that:
1. Generates podcast scripts from topics (via local LLM) or accepts manual scripts
2. Synthesizes speech using MLX TTS engines (mlx-audio/Qwen3-TTS or f5-tts-mlx)
3. Cleans and normalizes audio (ffmpeg)
4. Assembles episodes with intro/outro and loudness targeting
5. Transcribes, generates show notes, and publishes via RSS

## Repo Layout

```
openclaw-podcast-agent/
├── IDENTITY.md, SOUL.md, AGENTS.md   # Agent reads these (personality, protocols)
├── USER.md, TOOLS.md, HEARTBEAT.md   # Agent reads these (user, tools, heartbeat)
├── CLAUDE.md                          # YOU read this (developer guide)
├── agent.yaml                         # OpenClaw agent config (skills, model)
├── .env.example                       # Environment variable template
├── config/
│   ├── podcast.json                   # Languages, TTS engine, audio params, schedule
│   └── rss_template.xml               # RSS feed template
├── references/                        # Voice reference audio (gitignored)
├── tools/
│   ├── pyproject.toml                 # Poetry deps
│   ├── Dockerfile                     # Multi-stage: base+ffmpeg / test / production
│   ├── pipeline_runner/               # Python package
│   │   ├── runner.py                  # Core pipeline engine (generic, from journalist)
│   │   ├── config.py                  # PodcastSettings + PodcastConfig
│   │   ├── cli.py                     # CLI entry point
│   │   ├── scheduler.py              # Long-running scheduler service
│   │   ├── utils/ffmpeg.py           # Shared ffmpeg helper
│   │   ├── tts/                       # TTS engine abstraction
│   │   │   ├── base.py               # TTSEngine protocol
│   │   │   ├── mlx_audio_engine.py   # mlx-audio / Qwen3-TTS
│   │   │   └── f5_tts_engine.py      # f5-tts-mlx
│   │   ├── pipelines/                # Pre-built pipelines
│   │   └── steps/                    # Composable pipeline steps
│   └── tests/                        # pytest suite
├── spec/                              # Detailed specifications
├── .archgate/adrs/                    # Architecture Decision Records
├── .github/workflows/ci.yml          # CI pipeline
├── output/                            # Generated episodes (gitignored)
├── log/                               # Pipeline logs (gitignored)
└── memory/                            # Agent memory (gitignored)
```

## Two Audiences, Two Sets of Files

| Audience | Files | Purpose |
|----------|-------|---------|
| **Podcaster Agent** | IDENTITY, SOUL, AGENTS, USER, TOOLS, HEARTBEAT, spec/CRON, spec/TASK, memory/ | Runtime behavior, identity, protocols |
| **Developers / Claude Code** | CLAUDE, spec/*, .archgate/adrs/*, tools/, Dockerfile, docker-compose.yml, CI | Build, test, improve, deploy |

## Key Architectural Decision: Hybrid Docker + Host

MLX packages (mlx-audio, f5-tts-mlx, mlx-whisper) require Apple Silicon Metal and
cannot run inside standard Docker containers. See ARCH-002 for the full rationale.

**In Docker:** Pipeline engine, ffmpeg processing, Ollama calls, scheduling, IAMQ
**On host macOS:** TTS voice synthesis, mlx-whisper transcription

The CLI detects the environment and routes accordingly.

## Environment Variables

See `.env.example` for the complete list. Key variables:

| Variable | Purpose |
|----------|---------|
| `PODCAST_DATA_DIR` | Base directory for output, logs, reports |
| `PODCAST_WORKSPACE_DIR` | Agent workspace directory |
| `PODCAST_CONFIG_FILE` | Path to podcast.json |
| `LIBRARIAN_AGENT_WORKSPACE` | Librarian handoff directory |
| `IAMQ_HTTP_URL` | IAMQ service URL |
| `IAMQ_AGENT_ID` | Agent ID (default: podcast_agent) |
| `OLLAMA_BASE_URL` | Ollama API URL |
| `OLLAMA_MODEL` | LLM model for script generation |
| `TTS_ENGINE` | TTS engine override (mlx-audio or f5-tts-mlx) |

## Commands

```bash
# Start scheduler (recommended)
docker compose up -d scheduler

# Ad-hoc via scheduler
docker compose exec scheduler pipeline generate-script --topics "AI news"
docker compose exec scheduler pipeline validate

# One-shot (cli profile)
docker compose run --rm --profile cli pipeline generate-episode --topics "AI" --lang en

# TTS/transcription (host only, requires Apple Silicon)
pipeline voice-preview --text "Hello world" --lang en
pipeline transcribe --input episode.mp3

# Tests
docker compose run --rm --profile test pipeline-test
```

## Testing & CI

- **Unit tests:** `pytest tests/ -v`
- **Lint:** `ruff check pipeline_runner/ && ruff format --check pipeline_runner/`
- **Type check:** `mypy pipeline_runner/`
- **CI matrix:** Python 3.12, 3.13
- **Docker build validation:** All profiles
- **Secrets scan:** Blocks hardcoded credentials and local paths

TTS and transcription tests mock the MLX packages since CI runs on Linux.

## Architecture Decision Records

ADRs live in `.archgate/adrs/ARCH-{NNN}-slug.md`. Create one before major refactors.

| ADR | Topic |
|-----|-------|
| ARCH-001 | Podcast production pipeline design |
| ARCH-002 | Zero-install containerization (hybrid Docker + host) |
| ARCH-003 | Dual TTS engine architecture |
| ARCH-004 | Inter-agent collaboration |
| ARCH-005 | Multilingual episode generation |

## Sensitive Data Policy

**NEVER commit:** `.env`, credentials, API keys, PII, voice reference audio.
- User profile via environment variables (not git)
- `.gitignore`: `.env`, `references/`, `output/`, `memory/`, `.openclaw/`
- `log/` tracked via `.gitkeep`, contents gitignored
- CI blocks if secrets or hardcoded paths detected

## Contributing

1. Read this file + `spec/ARCHITECTURE.md`
2. Copy `.env.example` to `.env`, configure
3. Use `docker compose` for all execution (except TTS/transcription)
4. Run tests before committing
5. Keep the agent autonomous — don't break its protocols
6. Document decisions as ADRs
7. Capture learnings in `spec/LEARNINGS.md`
