<p align="center">
  <img src="assets/banner.svg" alt="openclaw-podcast-agent" width="600">
</p>

# Podcaster

Autonomous podcast production agent for the Openclaw ecosystem. Generates podcast episodes from topics or scripts using Apple Silicon MLX-based TTS, with audio cleanup, transcription, and RSS distribution.

## Features

- **Script generation** via MiniMax LLM (Anthropic-compatible API) or manual input
- **Dual TTS engines**: mlx-audio (Qwen3-TTS) and f5-tts-mlx, switchable via config
- **Configurable multilingual** episode production with per-language voice references
- **Audio cleanup** and loudness normalization (-16 LUFS / -1.0 dBTP)
- **Transcription** via mlx-whisper with chapter markers and show notes
- **RSS distribution** with Podcast 2.0 support
- **IAMQ integration** for inter-agent communication (sidecar-based)
- **Zero-install** Docker containers for all non-MLX processing

## Skills

| Skill | Description |
|-------|-------------|
| `audio_synthesis_prepare` | Prepare an audio synthesis job for a text segment with optional voice selection |

Workspace skills also available: `iamq_message_send`, `log_learning`, `improve_skill`

Skills auto-improve via post-execution hooks and nightly batch review.

## Architecture

- **Language**: Python
- **IAMQ ID**: `podcast_agent`
- **Runtime**: Docker (pipeline engine, ffmpeg, scheduling) + Apple Silicon host (MLX TTS, transcription)

Five-stage composable pipeline: **Script** → **Voice** → **Cleanup** → **Assembly** → **Distribute**

Two independent Python packages:

| Package | Location | Purpose |
|---------|----------|---------|
| **podcast-renderer** | `podcast_renderer/` | TTS engines, audio processing, LLM, transcription |
| **pipeline-runner** | `tools/` | Pipeline orchestration, CLI, scheduler, IAMQ/handoff steps |

## Setup

```bash
cp .env.example .env
# Set LLM_API_KEY (MiniMax) and place a 10-15s WAV in references/en_voice.wav
docker compose up -d scheduler
docker compose exec scheduler pipeline generate-episode --topics "AI news" --lang en
```

## Development

```bash
# Run tests
docker compose run --rm --profile test pipeline-test

# Lint and type-check
ruff check pipeline_runner/ podcast_renderer/
mypy pipeline_runner/ podcast_renderer/
```

### Docker Volume Mounts

```yaml
- ../skills-cli:/skills-cli:ro
- ../skills:/workspace/skills:rw
- ./skills:/agent/skills:rw
```

Environment: `EMBEDDINGS_URL=http://host.docker.internal:18795`

See `CLAUDE.md` for the full developer guide and `spec/ARCHITECTURE.md` for system design.

## Related

- [openclaw-inter-agent-message-queue](https://github.com/r3dlex/openclaw-inter-agent-message-queue) — IAMQ message bus and agent registry
- [openclaw-main-agent](https://github.com/r3dlex/openclaw-main-agent) — Cross-agent pipeline orchestrator

## License

MIT
