<p align="center">
  <img src="assets/banner.svg" alt="openclaw-podcast-agent" width="600">
</p>

# openclaw-podcast-agent

Autonomous podcast production agent for the OpenClaw ecosystem. Generates podcast episodes from topics or scripts using Apple Silicon MLX-based TTS, with audio cleanup, transcription, and RSS distribution.

## Features

- **Script generation** via MiniMax LLM (Anthropic-compatible API) or manual input
- **Dual TTS engines**: mlx-audio (Qwen3-TTS) and f5-tts-mlx, switchable via config
- **Configurable multilingual** episode production with per-language voice references
- **Audio cleanup** and loudness normalization (-16 LUFS / -1.0 dBTP)
- **Transcription** via mlx-whisper with chapter markers and show notes
- **RSS distribution** with Podcast 2.0 support
- **IAMQ integration** for inter-agent communication (sidecar-based)
- **Zero-install** Docker containers for all non-MLX processing

## Project Structure

Two independent Python packages:

| Package | Location | Purpose |
|---------|----------|---------|
| **podcast-renderer** | `podcast_renderer/` | TTS engines, audio processing, LLM integration, transcription, content generation |
| **pipeline-runner** | `tools/` | Pipeline orchestration, CLI, scheduler, IAMQ/handoff/notify steps |

`pipeline-runner` depends on `podcast-renderer` as a path dependency. Each has its own `pyproject.toml`, `Dockerfile`, and test suite.

## Quick Start

```bash
# 1. Configure
cp .env.example .env
# Edit .env — set LLM_API_KEY (MiniMax) at minimum

# 2. Add voice reference
# Place a 10-15s WAV recording in references/en_voice.wav

# 3. Start scheduler
docker compose up -d scheduler

# 4. Generate an episode
docker compose exec scheduler pipeline generate-episode --topics "AI news" --lang en

# 5. Or generate a script only
docker compose exec scheduler pipeline generate-script --topics "AI safety"
```

## Architecture

Five-stage composable pipeline:
1. **Script** — Generate podcast script from topics via MiniMax LLM (or manual input)
2. **Voice** — Synthesize speech via MLX TTS with voice cloning
3. **Cleanup** — Denoise, filter, and normalize audio via ffmpeg
4. **Assembly** — Combine intro/voice/outro, export MP3 + WAV
5. **Distribute** — Transcribe, generate show notes, update RSS, notify

See `CLAUDE.md` for the full developer guide and `spec/ARCHITECTURE.md` for system design.

## Requirements

- Docker (for pipeline engine, ffmpeg, scheduling)
- Apple Silicon Mac (for MLX TTS and transcription)
- MiniMax API key (for script and show notes generation)

## Related

- [openclaw-inter-agent-message-queue](https://github.com/r3dlex/openclaw-inter-agent-message-queue) — IAMQ: message bus, agent registry, and cron scheduler
  - [HTTP API reference](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/API.md)
  - [Cron subsystem](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/CRON.md)
  - [Sidecar client](https://github.com/r3dlex/openclaw-inter-agent-message-queue/tree/main/sidecar)
- [openclaw-main-agent](https://github.com/r3dlex/openclaw-main-agent) — Cross-agent pipeline orchestrator

## License

MIT
