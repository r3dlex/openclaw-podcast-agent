# Recurring Task Schedule

Tasks the Podcaster agent runs on a recurring schedule. The scheduler service (`docker compose up -d scheduler`) executes these automatically. Times are in Europe/Berlin (CET/CEST).

## Active Schedule

| Schedule | Task | Description |
|----------|------|-------------|
| Monday 06:00 | Weekly episode generation | Full episode pipeline for all configured languages |

## Weekly Episode Generation

**Cron:** `0 6 * * 1` (Monday at 06:00)

Runs the full episode pipeline:
1. Generate script from configured topics/sources via MiniMax LLM
2. Synthesize voice per language (delegates to host macOS for MLX)
3. Normalize and clean audio via ffmpeg
4. Assemble episode with intro/outro, transcript, show notes
5. Update RSS feed and distribute
6. Announce completion to IAMQ and hand off to Librarian

Source: `config/podcast.json` field `schedule.generate_episode`.

## IAMQ Heartbeat

IAMQ registration and heartbeats are handled by a **sidecar container**, not by the
Python scheduler. The sidecar sends heartbeats every 2 minutes automatically.
No cron entry is needed in the pipeline runner for this.

## Notes

- The agent owns this file and keeps it current.
- Add new recurring tasks here with schedule, description, and source.
- For one-shot tasks, use `spec/TASK.md` instead.

## References

- [IAMQ Cron Subsystem](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/CRON.md) — how cron schedules are stored and fired
- [IAMQ API — Cron endpoints](https://github.com/r3dlex/openclaw-inter-agent-message-queue/blob/main/spec/API.md#cron-scheduling)
- [IamqSidecar.MqClient.register_cron/3](https://github.com/r3dlex/openclaw-inter-agent-message-queue/tree/main/sidecar) — Elixir sidecar helper
- [openclaw-main-agent](https://github.com/r3dlex/openclaw-main-agent) — orchestrates cron-triggered pipelines
