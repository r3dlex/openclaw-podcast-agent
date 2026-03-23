"""Audio cleanup pipeline — raw audio to clean, normalized audio.

Steps: AudioCleanupStep -> LoudnessNormStep
"""

from __future__ import annotations

from podcast_renderer.audio.cleanup import AudioCleanupStep
from podcast_renderer.audio.loudness import LoudnessNormStep

from pipeline_runner.runner import Pipeline


def build_cleanup_pipeline() -> Pipeline:
    """Build the audio cleanup pipeline."""
    pipeline = Pipeline("audio_cleanup")
    pipeline.add_step(AudioCleanupStep())
    pipeline.add_step(LoudnessNormStep())
    return pipeline
