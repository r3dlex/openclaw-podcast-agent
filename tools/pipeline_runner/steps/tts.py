"""TTS generation step — synthesize speech from script chunks.

Uses the configured TTS engine (mlx-audio or f5-tts-mlx) to generate
audio for each text chunk. Writes each segment to disk immediately
to minimize memory usage.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pipeline_runner.config import PodcastSettings
from pipeline_runner.tts.base import get_engine

logger = logging.getLogger(__name__)


class TTSGenerationStep:
    """Generate audio from script chunks using the configured TTS engine.

    Context in:  script (with chunks), reference_audio_path, reference_text, settings
    Context out: raw_audio_segments (list[Path])
    """

    name = "tts_generation"

    def should_run(self, context: dict[str, Any]) -> bool:
        return (
            "script" in context
            and "reference_audio_path" in context
            and "reference_text" in context
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        settings: PodcastSettings = context.get("settings", PodcastSettings())
        script = context["script"]
        ref_audio = Path(context["reference_audio_path"])
        ref_text = context["reference_text"]

        # Get TTS engine
        engine_name = settings.tts_engine
        engine = get_engine(engine_name)
        logger.info("Using TTS engine: %s", engine.name)

        # Create temp directory for segments
        episode_id = context.get("episode_id", "episode")
        segments_dir = settings.output_dir / "tmp" / episode_id
        segments_dir.mkdir(parents=True, exist_ok=True)

        raw_segments: list[Path] = []
        chunk_index = 0

        for segment in script.get("segments", []):
            chunks = segment.get("chunks", [segment.get("text", "")])
            for chunk_text in chunks:
                if not chunk_text.strip():
                    continue

                output_path = segments_dir / f"segment_{chunk_index:04d}.wav"
                try:
                    engine.generate(
                        text=chunk_text,
                        reference_audio=ref_audio,
                        reference_text=ref_text,
                        output_path=output_path,
                        quantization=settings.tts_quantization,
                    )
                    raw_segments.append(output_path)
                    logger.debug("Generated segment %d: %s", chunk_index, output_path)
                except Exception:
                    logger.error("Failed to generate segment %d", chunk_index, exc_info=True)
                    raise

                chunk_index += 1

        context["raw_audio_segments"] = raw_segments
        logger.info("Generated %d audio segments in %s", len(raw_segments), segments_dir)
        return context
