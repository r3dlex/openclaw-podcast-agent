"""Voice generation pipeline — script to raw audio segments.

Steps: PrepareReferenceStep -> TTSGenerationStep -> ConcatenateStep
"""

from __future__ import annotations

from typing import Any

from podcast_renderer.audio.concat import ConcatenateStep
from podcast_renderer.audio.reference import PrepareReferenceStep
from podcast_renderer.audio.tts_step import TTSGenerationStep

from pipeline_runner.config import PodcastConfig, PodcastSettings
from pipeline_runner.runner import Pipeline


def build_voice_pipeline() -> Pipeline:
    """Build the voice generation pipeline."""
    pipeline = Pipeline("voice_generation")
    pipeline.add_step(PrepareReferenceStep())
    pipeline.add_step(TTSGenerationStep())
    pipeline.add_step(ConcatenateStep())
    return pipeline


def run_voice_preview(
    settings: PodcastSettings,
    *,
    text: str,
    lang: str = "en",
) -> str:
    """Generate a short audio preview from text.

    Returns a human-readable summary.
    """
    config = PodcastConfig(settings.podcast_config_file)
    lang_config = config.language_config(lang)

    if not lang_config:
        return f"Language '{lang}' not configured in podcast.json"

    context: dict[str, Any] = {
        "settings": settings,
        "pipeline_name": "voice_preview",
        "language": lang,
        "language_config": lang_config,
        "episode_id": "preview",
        "script": {
            "segments": [{"speaker": "host", "text": text, "chunks": [text]}],
        },
    }

    pipeline = build_voice_pipeline()
    result = pipeline.run(context)
    return result.summary()
