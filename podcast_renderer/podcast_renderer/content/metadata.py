"""Episode metadata step — generate episode metadata.

Collects all episode metadata: title, description, language, duration,
file size, publication date.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from podcast_renderer.audio.ffmpeg import get_audio_duration

logger = logging.getLogger(__name__)


class MetadataStep:
    """Generate episode metadata.

    Context in:  episode_mp3 (Path), script (dict), settings
    Context out: episode_metadata (dict)
    """

    name = "metadata"

    def should_run(self, context: dict[str, Any]) -> bool:
        return "episode_mp3" in context

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        mp3_path = Path(context["episode_mp3"])
        script = context.get("script", {})

        # Get duration
        try:
            duration = get_audio_duration(mp3_path)
        except Exception:
            duration = 0.0
            logger.warning("Could not determine audio duration")

        # Get file size
        file_size = mp3_path.stat().st_size if mp3_path.exists() else 0

        metadata = {
            "title": script.get("title", "Untitled Episode"),
            "description": script.get("description", ""),
            "language": context.get("language", script.get("language", "en")),
            "duration_seconds": duration,
            "file_size_bytes": file_size,
            "file_path": str(mp3_path),
            "publication_date": datetime.now(tz=UTC).isoformat(),
            "format": "audio/mpeg",
        }

        # Include show notes if available
        if "show_notes" in context:
            metadata["show_notes"] = context["show_notes"]

        # Include chapters if available
        if "chapters" in context:
            metadata["chapters"] = context["chapters"]

        context["episode_metadata"] = metadata
        logger.info(
            "Episode metadata: %s (%.0fs, %d bytes)",
            metadata["title"],
            duration,
            file_size,
        )
        return context
