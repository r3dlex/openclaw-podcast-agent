"""Chapter marker generation step.

Generates chapter markers from the script structure and transcript timestamps.
Output format is compatible with podcast RSS and MP3 ID3 tags.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ChapterMarkerStep:
    """Generate chapter markers from script segments and transcript.

    Context in:  script (dict with segments), transcript (optional)
    Context out: chapters (list of {start_time, title})
    """

    name = "chapter_markers"

    def should_run(self, context: dict[str, Any]) -> bool:
        return "script" in context

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        script = context["script"]
        transcript = context.get("transcript", {})
        transcript_segments = transcript.get("segments", [])

        chapters: list[dict[str, Any]] = []
        current_time = 0.0

        for i, segment in enumerate(script.get("segments", [])):
            notes = segment.get("notes", "")
            text = segment.get("text", "")

            # Use notes as chapter title, or first ~50 chars of text
            if notes:
                title = notes.capitalize()
            else:
                title = text[:50] + "..." if len(text) > 50 else text

            # Try to get timestamp from transcript if available
            if transcript_segments and i < len(transcript_segments):
                current_time = float(transcript_segments[i].get("start", current_time))

            chapters.append({
                "start_time": current_time,
                "title": title,
            })

            # Estimate duration from transcript or fallback
            if transcript_segments and i < len(transcript_segments):
                end = float(transcript_segments[i].get("end", current_time + 10))
                current_time = end
            else:
                # Rough estimate: ~150 WPM, 5 chars per word
                estimated_duration = len(text) / 5 / 150 * 60
                current_time += estimated_duration

        context["chapters"] = chapters
        logger.info("Generated %d chapter markers", len(chapters))
        return context
