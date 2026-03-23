"""Assembly pipeline — normalized audio to final episode files.

Steps: EpisodeAssemblyStep
"""

from __future__ import annotations

from pipeline_runner.runner import Pipeline
from podcast_renderer.audio.assemble import EpisodeAssemblyStep


def build_assembly_pipeline() -> Pipeline:
    """Build the episode assembly pipeline."""
    pipeline = Pipeline("episode_assembly")
    pipeline.add_step(EpisodeAssemblyStep())
    return pipeline
