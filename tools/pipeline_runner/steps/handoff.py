"""Librarian handoff step — write outputs and notify the Librarian agent.

Implements the inter-agent collaboration protocol defined in ARCH-004.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from pipeline_runner.config import PodcastSettings

logger = logging.getLogger(__name__)


class LibrarianHandoffStep:
    """Write pipeline output to log directory and prepare handoff metadata.

    Context in:  episode_summary or content (str), pipeline name
    Context out: handoff_path (Path), handoff_metadata (dict)
    """

    name = "librarian_handoff"

    def should_run(self, context: dict[str, Any]) -> bool:
        return "episode_summary" in context or "content" in context

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        settings: PodcastSettings = context.get("settings", PodcastSettings())
        now = datetime.now(tz=UTC)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        pipeline_name = context.get("pipeline_name", "unknown")

        content = context.get("episode_summary") or context.get("content", "")

        # Write to log directory
        log_dir = settings.log_dir
        filename = f"{timestamp}_{pipeline_name}.md"
        output_path = log_dir / filename
        output_path.write_text(content, encoding="utf-8")
        logger.info("Wrote output to %s", output_path)

        # Write handoff metadata
        metadata = {
            "source_agent": "podcast",
            "target_agent": "librarian",
            "pipeline": pipeline_name,
            "timestamp": now.isoformat(),
            "output_file": str(output_path),
            "output_size_bytes": len(content.encode("utf-8")),
        }

        # Include episode file paths if available
        for key in ("episode_mp3", "episode_wav", "transcript_path", "rss_feed_path"):
            if key in context:
                metadata[key] = str(context[key])

        metadata_path = log_dir / f"{timestamp}_{pipeline_name}.meta.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        # If librarian workspace is configured, write a handoff signal
        librarian_ws = settings.librarian_workspace_mount or settings.librarian_agent_workspace
        if librarian_ws and librarian_ws.exists():
            inbox = librarian_ws / "inbox"
            inbox.mkdir(parents=True, exist_ok=True)
            signal_path = inbox / f"podcast_{timestamp}.json"
            signal_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            logger.info("Handoff signal written to %s", signal_path)
        else:
            logger.warning("Librarian workspace not configured or not found: %s", librarian_ws)

        context["handoff_path"] = output_path
        context["handoff_metadata"] = metadata
        return context
