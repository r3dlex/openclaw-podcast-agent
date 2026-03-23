"""Audio concatenation step — join segments into a single audio file.

Uses ffmpeg's concat demuxer to join audio segments without re-encoding.
This is file-based (no memory accumulation).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from podcast_renderer.audio.ffmpeg import run_ffmpeg

logger = logging.getLogger(__name__)


class ConcatenateStep:
    """Concatenate raw audio segments into a single file.

    Context in:  raw_audio_segments (list[Path]), settings
    Context out: raw_episode_audio (Path)
    """

    name = "concatenate"

    def should_run(self, context: dict[str, Any]) -> bool:
        segments = context.get("raw_audio_segments", [])
        return len(segments) > 0

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        settings = context.get("settings")
        segments: list[Path] = context["raw_audio_segments"]

        if len(segments) == 1:
            # Single segment, no concatenation needed
            context["raw_episode_audio"] = segments[0]
            return context

        # Write concat file list
        episode_id = context.get("episode_id", "episode")
        output_dir = settings.output_dir / "tmp" / episode_id
        list_file = output_dir / "concat_list.txt"

        with open(list_file, "w", encoding="utf-8") as f:
            for seg_path in segments:
                # ffmpeg concat requires 'file' directive with escaped paths
                escaped = str(seg_path).replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        # Concatenate using ffmpeg concat demuxer
        output_path = output_dir / "raw_episode.wav"
        run_ffmpeg([
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path),
        ])

        context["raw_episode_audio"] = output_path
        logger.info(
            "Concatenated %d segments into %s",
            len(segments),
            output_path,
        )
        return context
