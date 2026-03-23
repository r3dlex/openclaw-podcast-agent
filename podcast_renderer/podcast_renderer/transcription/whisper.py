"""Transcription step — transcribe audio using mlx-whisper.

Uses mlx-whisper for local, fast transcription on Apple Silicon.
Supports 97+ languages with automatic detection.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TranscribeStep:
    """Transcribe episode audio using mlx-whisper.

    Context in:  episode_mp3 or episode_wav or input_audio (Path)
    Context out: transcript (dict with text, segments, language)
    """

    name = "transcribe"

    def should_run(self, context: dict[str, Any]) -> bool:
        return (
            "episode_mp3" in context
            or "episode_wav" in context
            or "input_audio" in context
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        audio_path = Path(
            context.get("episode_mp3")
            or context.get("episode_wav")
            or context["input_audio"]
        )

        try:
            import mlx_whisper

            logger.info("Transcribing: %s", audio_path)
            result = mlx_whisper.transcribe(
                str(audio_path),
                path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
            )

            context["transcript"] = {
                "text": result.get("text", ""),
                "segments": result.get("segments", []),
                "language": result.get("language", "en"),
            }
            logger.info(
                "Transcription complete: %d chars, language=%s",
                len(context["transcript"]["text"]),
                context["transcript"]["language"],
            )

        except ImportError:
            logger.warning("mlx-whisper not installed, skipping transcription")
            context["transcript"] = {
                "text": "",
                "segments": [],
                "language": context.get("language", "en"),
            }

        return context
