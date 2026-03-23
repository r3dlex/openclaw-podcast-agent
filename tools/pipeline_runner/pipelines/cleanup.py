"""Audio cleanup pipeline — raw audio to clean, normalized audio.

Steps: AudioCleanupStep -> LoudnessNormStep
"""

from __future__ import annotations

from pipeline_runner.runner import Pipeline
from pipeline_runner.steps.cleanup import AudioCleanupStep
from pipeline_runner.steps.loudness import LoudnessNormStep


def build_cleanup_pipeline() -> Pipeline:
    """Build the audio cleanup pipeline."""
    pipeline = Pipeline("audio_cleanup")
    pipeline.add_step(AudioCleanupStep())
    pipeline.add_step(LoudnessNormStep())
    return pipeline
