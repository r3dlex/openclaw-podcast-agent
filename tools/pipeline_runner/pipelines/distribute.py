"""Distribution pipeline — episode to published (transcription, RSS, handoff).

Steps: TranscribeStep -> ChapterMarkerStep -> ShowNotesStep -> MetadataStep ->
       RSSGenerationStep -> LibrarianHandoffStep -> IAMQAnnounceStep
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from podcast_renderer.content.chapters import ChapterMarkerStep
from podcast_renderer.content.metadata import MetadataStep
from podcast_renderer.content.rss import RSSGenerationStep
from podcast_renderer.llm.shownotes import ShowNotesStep
from podcast_renderer.transcription.whisper import TranscribeStep

from pipeline_runner.config import PodcastSettings
from pipeline_runner.runner import Pipeline
from pipeline_runner.steps.handoff import LibrarianHandoffStep
from pipeline_runner.steps.iamq import IAMQAnnounceStep


def build_distribute_pipeline() -> Pipeline:
    """Build the distribution pipeline."""
    pipeline = Pipeline("distribution")
    pipeline.add_step(TranscribeStep())
    pipeline.add_step(ChapterMarkerStep())
    pipeline.add_step(ShowNotesStep())
    pipeline.add_step(MetadataStep())
    pipeline.add_step(RSSGenerationStep())
    pipeline.add_step(LibrarianHandoffStep())
    pipeline.add_step(IAMQAnnounceStep())
    return pipeline


def run_transcribe_pipeline(
    settings: PodcastSettings,
    *,
    input_path: str,
) -> str:
    """Transcribe an audio file.

    Returns a human-readable summary.
    """
    context: dict[str, Any] = {
        "settings": settings,
        "pipeline_name": "transcribe",
        "input_audio": Path(input_path),
    }

    # Only run transcription step
    pipeline = Pipeline("transcribe")
    pipeline.add_step(TranscribeStep())
    result = pipeline.run(context)

    # Output transcript if available
    if result.success and "transcript" in result.context:
        transcript = result.context["transcript"]
        text = transcript.get("text", "")
        if text:
            # Write transcript to file
            output_path = Path(input_path).with_suffix(".txt")
            output_path.write_text(text, encoding="utf-8")

    return result.summary()
