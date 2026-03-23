"""Pipeline scheduler — long-running service that executes pipelines on cron.

Reads the schedule from configuration and runs pipelines at specified times.
Stays running as a Docker service (`docker compose up -d scheduler`).

For ad-hoc commands while the scheduler is running:
    docker compose exec scheduler pipeline generate-script --topics "..."
    docker compose exec scheduler pipeline generate-episode --topics "..."

See spec/CRON.md for the schedule definition.
See ARCH-001 for the architectural decision.

IMPORTANT: The `schedule` library fires "overdue" jobs immediately on the
first `run_pending()` call. To prevent every restart from re-running all
past-time jobs, we track last-run timestamps in a state file and skip
jobs that already ran today.
"""

from __future__ import annotations

import json
import logging
import signal
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import schedule

from pipeline_runner.config import PodcastSettings

logger = logging.getLogger(__name__)

# Sentinel for graceful shutdown
_shutdown = False

# Shared state dict — loaded once at startup, updated on each run
_run_state: dict[str, str] = {}

# State file path — set dynamically from settings in run_scheduler()
_state_file: Path = Path("log/scheduler_state.json")


@dataclass
class ScheduledTask:
    """A task registered with the scheduler."""

    name: str
    schedule_desc: str
    pipeline_fn: str


def _load_state() -> dict[str, str]:
    """Load last-run timestamps from state file."""
    try:
        if _state_file.exists():
            data: dict[str, str] = json.loads(_state_file.read_text(encoding="utf-8"))
            return data
    except Exception:
        logger.warning("Could not load scheduler state, starting fresh")
    return {}


def _save_state(state: dict[str, str]) -> None:
    """Persist last-run timestamps to state file."""
    try:
        _state_file.parent.mkdir(parents=True, exist_ok=True)
        _state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        logger.warning("Could not save scheduler state", exc_info=True)


def _already_ran_today(task_name: str, state: dict[str, str]) -> bool:
    """Check if a task already ran today (by date string comparison)."""
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    last_run = state.get(task_name, "")
    return last_run.startswith(today)


def _mark_ran(task_name: str, state: dict[str, str]) -> None:
    """Record that a task ran now."""
    state[task_name] = datetime.now(tz=UTC).isoformat()
    _save_state(state)


def _handle_signal(signum: int, frame: Any) -> None:
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    global _shutdown
    logger.info("Received signal %d, shutting down gracefully...", signum)
    _shutdown = True


def _run_episode(settings: PodcastSettings) -> None:
    """Run the full episode generation pipeline."""
    logger.info("Scheduled: running episode generation pipeline")
    try:
        from pipeline_runner.pipelines.episode import run_episode_pipeline

        result = run_episode_pipeline(settings)
        logger.info("Episode generation completed: %s", result[:200] if result else "empty")
    except Exception:
        logger.exception("Episode generation pipeline failed")


def _guarded_run(task_name: str, fn: Any, *args: Any) -> None:
    """Run a task only if it hasn't already run today. Tracks state.

    This prevents the schedule library's "overdue job" behavior from
    re-running all past-time tasks on every container restart.
    """
    if _already_ran_today(task_name, _run_state):
        logger.info("Skipping '%s' — already ran today (restart protection)", task_name)
        return
    fn(*args)
    _mark_ran(task_name, _run_state)


def register_schedule(settings: PodcastSettings) -> list[ScheduledTask]:
    """Register all scheduled tasks from config.

    Default schedule (from spec/CRON.md):
        Monday 06:00  Episode generation (all languages)

    Each task is wrapped in _guarded_run to prevent re-execution on
    container restart (the schedule library fires overdue jobs immediately).
    """
    tasks: list[ScheduledTask] = []

    # Monday 06:00 — Weekly episode generation
    schedule.every().monday.at("06:00").do(_guarded_run, "weekly_episode", _run_episode, settings)
    tasks.append(ScheduledTask("Weekly episode", "monday 06:00", "generate_episode"))

    # Note: IAMQ registration and heartbeats are handled by the IAMQ sidecar
    # container in docker-compose.yml — no Python-side heartbeat needed.

    return tasks


def run_scheduler(settings: PodcastSettings | None = None) -> None:
    """Start the scheduler loop. Blocks until SIGTERM/SIGINT."""
    global _shutdown, _run_state, _state_file

    settings = settings or PodcastSettings()

    # Resolve state file relative to PODCAST_DATA_DIR
    _state_file = settings.log_dir / "scheduler_state.json"

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # Load persisted state so we know which tasks already ran today
    _run_state = _load_state()
    logger.info("Loaded scheduler state: %d tasks previously ran", len(_run_state))

    # Note: IAMQ registration handled by sidecar container
    tasks = register_schedule(settings)

    logger.info("Scheduler started with %d tasks:", len(tasks))
    for t in tasks:
        logger.info("  [%s] %s -> %s", t.schedule_desc, t.name, t.pipeline_fn)

    logger.info("Next run: %s", schedule.next_run())

    while not _shutdown:
        schedule.run_pending()
        # Sleep in short intervals so we can respond to signals promptly
        for _ in range(10):
            if _shutdown:
                break
            time.sleep(1)

    logger.info("Scheduler stopped.")
    sys.exit(0)
