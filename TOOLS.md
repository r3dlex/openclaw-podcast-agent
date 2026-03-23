# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics.

## Skills (from agent.yaml)

| Skill | Command | Cost Tier |
|-------|---------|-----------|
| `generate_script` | `docker compose exec scheduler pipeline generate-script --topics "..."` | Tier 1 (local LLM) |
| `generate_episode` | `docker compose exec scheduler pipeline generate-episode --topics "..."` | Tier 2 (compute) |
| `voice_preview` | `pipeline voice-preview --text "..." --lang en` | Tier 2 (compute) |
| `list_voices` | `pipeline list-voices` | Tier 1 (free) |
| `transcribe` | `pipeline transcribe --input audio.mp3` | Tier 2 (compute) |

The **scheduler service** must be running: `docker compose up -d scheduler`.
All skill commands execute instantly via `docker compose exec` (no container startup).
One-shot fallback: `docker compose run --rm --profile cli pipeline <cmd>`.

**Note:** TTS and transcription steps use MLX and must run on the Apple Silicon host,
not inside Docker containers. The scheduler handles ffmpeg processing and Ollama calls
in Docker; voice synthesis runs natively.

## Production Config

- Languages and voice references: `config/podcast.json`
- TTS engine selection: `config/podcast.json` (mlx-audio or f5-tts-mlx)
- Audio standards: 24 kHz, -16 LUFS, -1.0 dBTP, MP3 192 kbps
- Script generation: Ollama at `$OLLAMA_BASE_URL` (default `http://host.docker.internal:11434`)

## Inter-Agent Message Queue (IAMQ)

The IAMQ service at `$IAMQ_HTTP_URL` (default `http://127.0.0.1:18790`) connects
all OpenClaw agents. The scheduler auto-registers on startup and sends heartbeats
every 2 minutes. Every pipeline announces its completion to the queue.

```bash
# Check your inbox
curl http://127.0.0.1:18790/inbox/podcast_agent?status=unread

# List online agents
curl http://127.0.0.1:18790/agents

# Send a message to another agent
curl -X POST http://127.0.0.1:18790/send \
  -H "Content-Type: application/json" \
  -d '{"from":"podcast_agent","to":"librarian_agent","type":"request","priority":"NORMAL","subject":"...","body":"..."}'
```

## Environment-Specific Notes

_(Add local setup details here: voice references, Ollama models, preferred styles, etc.)_

---

Keep shared skills and local setup separate. This is your cheat sheet.
For deeper details: `spec/PIPELINES.md`, `spec/ARCHITECTURE.md`, `spec/TROUBLESHOOTING.md`.
