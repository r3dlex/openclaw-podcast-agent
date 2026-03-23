# Recurring Task Schedule

Tasks the Podcaster agent runs on a recurring schedule. The scheduler service (`docker compose up -d scheduler`) executes these automatically. Times are in Europe/Berlin (CET/CEST).

## Active Schedule

| Schedule | Task | Description |
|----------|------|-------------|
| Monday 06:00 | Weekly episode generation | Full episode pipeline for all configured languages |
| Every 2 min | IAMQ heartbeat | Keep `podcast_agent` visible to peer agents |

## Weekly Episode Generation

**Cron:** `0 6 * * 1` (Monday at 06:00)

Runs the full episode pipeline:
1. Generate script from configured topics/sources via Ollama
2. Synthesize voice per language (delegates to host macOS for MLX)
3. Normalize and clean audio via ffmpeg
4. Assemble episode with intro/outro, transcript, show notes
5. Update RSS feed and distribute
6. Announce completion to IAMQ and hand off to Librarian

Source: `config/podcast.json` field `schedule.generate_episode`.

## IAMQ Heartbeat

**Interval:** Every 2 minutes

Sends `POST $IAMQ_HTTP_URL/heartbeat {"agent_id": "podcast_agent"}` to maintain presence on the inter-agent message queue. Also checks inbox for pending requests from peer agents.

Handled by `pipeline_runner/scheduler.py`.

## Notes

- The agent owns this file and keeps it current.
- Add new recurring tasks here with schedule, description, and source.
- For one-shot tasks, use `spec/TASK.md` instead.
