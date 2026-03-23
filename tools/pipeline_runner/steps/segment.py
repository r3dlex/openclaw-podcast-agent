"""Text segmentation step — split script segments into TTS-friendly chunks.

TTS engines work best with short text chunks (100-200 characters).
This step splits each script segment's text into chunks at sentence
boundaries, respecting the configured max_segment_chars limit.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pipeline_runner.config import PodcastConfig, PodcastSettings

logger = logging.getLogger(__name__)

# Sentence-ending patterns
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_text_into_chunks(text: str, max_chars: int = 200) -> list[str]:
    """Split text into chunks at sentence boundaries.

    Args:
        text: The text to split.
        max_chars: Maximum characters per chunk.

    Returns:
        List of text chunks, each at most max_chars long.
    """
    if len(text) <= max_chars:
        return [text]

    sentences = _SENTENCE_END.split(text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # If adding this sentence would exceed the limit
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence

    if current.strip():
        chunks.append(current.strip())

    # Handle any chunks that are still too long (no sentence boundaries found)
    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            final_chunks.append(chunk)
        else:
            # Force split at word boundaries
            final_chunks.extend(_force_split(chunk, max_chars))

    return final_chunks


def _force_split(text: str, max_chars: int) -> list[str]:
    """Force split text at word boundaries when no sentence boundaries exist."""
    words = text.split()
    chunks: list[str] = []
    current = ""

    for word in words:
        if current and len(current) + len(word) + 1 > max_chars:
            chunks.append(current.strip())
            current = word
        else:
            current = f"{current} {word}" if current else word

    if current.strip():
        chunks.append(current.strip())

    return chunks


class TextSegmentationStep:
    """Split script segments into TTS-friendly chunks.

    Context in:  script (dict with segments), settings
    Context out: script (updated with chunks per segment)
    """

    name = "text_segmentation"

    def should_run(self, context: dict[str, Any]) -> bool:
        return "script" in context

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        settings: PodcastSettings = context.get("settings", PodcastSettings())
        script = context["script"]

        # Get max chars from podcast config if available
        try:
            config = PodcastConfig(settings.podcast_config_file)
            max_chars = config.max_segment_chars
        except Exception:
            max_chars = 200

        segments = script.get("segments", [])
        total_chunks = 0

        for segment in segments:
            text = segment.get("text", "")
            chunks = split_text_into_chunks(text, max_chars)
            segment["chunks"] = chunks
            total_chunks += len(chunks)

        context["script"] = script
        logger.info(
            "Segmented %d script segments into %d TTS chunks (max %d chars)",
            len(segments),
            total_chunks,
            max_chars,
        )
        return context
