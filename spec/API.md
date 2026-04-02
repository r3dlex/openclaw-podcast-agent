# API — openclaw-podcast-agent

## Overview

The Podcast agent does not expose an HTTP server. Cross-agent interaction uses
IAMQ. The agent also provides a CLI via the pipeline runner for operators who
want to trigger episode checks or rendering manually.

---

## IAMQ Message Interface

### Incoming messages accepted by `podcast_agent`

| Subject | Purpose | Body fields |
|---------|---------|-------------|
| `podcast.check` | Trigger an immediate RSS feed check for new episodes | `feeds?: string[]` (optional filter) |
| `podcast.render` | Render a specific episode (download + TTS + packaging) | `feed_url: string`, `episode_guid: string` |
| `podcast.status` | Return last check timestamp and episode queue length | — |
| `podcast.list` | List recently downloaded episodes | `limit?: number` |
| `podcast.subscribe` | Add a new RSS feed to the subscription list | `feed_url: string`, `title?: string` |
| `status` | Return agent health | — |

#### Example: check for new episodes

```json
{
  "from": "agent_claude",
  "to": "podcast_agent",
  "type": "request",
  "priority": "NORMAL",
  "subject": "podcast.check",
  "body": {}
}
```

#### Example response

```json
{
  "from": "podcast_agent",
  "to": "agent_claude",
  "type": "response",
  "priority": "NORMAL",
  "subject": "podcast.check.result",
  "body": {
    "feeds_checked": 8,
    "new_episodes": 2,
    "episodes": [
      {"title": "Episode 42 — AI in 2026", "feed": "My Favourite Podcast", "duration_min": 52},
      {"title": "Deep Dive: Rust Async",    "feed": "Dev Talks Weekly",      "duration_min": 38}
    ],
    "timestamp": "2026-04-02T06:01:00Z"
  }
}
```

---

## CLI Interface (Pipeline Runner)

```bash
# Check for new episodes
docker compose exec scheduler pipeline check_episodes

# Render a specific episode (TTS processing)
docker compose exec scheduler pipeline render --guid <episode_guid>

# One-shot without scheduler
docker compose run --rm --profile cli pipeline check_episodes
```

---

## Handoff to Librarian

New episode notifications are archived via the Librarian agent:

```json
{
  "from": "podcast_agent",
  "to": "librarian_agent",
  "type": "request",
  "subject": "librarian.file",
  "body": {
    "source_path": "/data/podcast/new_episodes_2026-04-02.md",
    "category": "podcast_logs",
    "date": "2026-04-02"
  }
}
```

---

## RSS Feed Configuration

Subscribed feeds are stored in `config/podcast.json` under the `feeds` key.
New feeds can be added via IAMQ `podcast.subscribe` or by editing the config
directly (a restart is not required — feeds are re-read on each check run).

---

**Related:** `spec/COMMUNICATION.md`, `spec/CRON.md`, `spec/PIPELINES.md`
