# BOOT.md — Startup Tasks

Run these on every session start, in order.

## 1. Register with IAMQ

```bash
curl -s -X POST http://127.0.0.1:18790/register \
  -H 'Content-Type: application/json' \
  -d '{
    "agent_id": "podcast_agent",
    "name": "Podcaster",
    "emoji": "🎧",
    "description": "Podcast production — script generation, TTS synthesis, episode assembly, RSS publishing",
    "capabilities": ["script_generation", "tts_synthesis", "episode_assembly", "audio_processing", "rss_publishing", "transcription"],
    "workspace": "'"$(pwd)"'"
  }'
```

## 2. Heartbeat

```bash
curl -s -X POST http://127.0.0.1:18790/heartbeat \
  -H 'Content-Type: application/json' \
  -d '{"agent_id": "podcast_agent"}'
```

## 3. Check inbox

```bash
curl -s http://127.0.0.1:18790/inbox/podcast_agent?status=unread
```

Process any pending messages — mark as `read` then `acted`.

## 4. Discover peers

```bash
curl -s http://127.0.0.1:18790/agents
```
