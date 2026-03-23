"""Full episode pipeline — orchestrates all sub-pipelines per language.

Runs: script -> voice -> cleanup -> assembly -> distribute for each language.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pipeline_runner.config import PodcastConfig, PodcastSettings
from pipeline_runner.pipelines.assembly import build_assembly_pipeline
from pipeline_runner.pipelines.cleanup import build_cleanup_pipeline
from pipeline_runner.pipelines.distribute import build_distribute_pipeline
from pipeline_runner.pipelines.script import build_script_pipeline
from pipeline_runner.pipelines.voice import build_voice_pipeline
from pipeline_runner.runner import PipelineResult

logger = logging.getLogger(__name__)


def run_episode_pipeline(
    settings: PodcastSettings,
    *,
    topics: str | None = None,
    script_file: str | None = None,
    langs: str | None = None,
    skip_cleanup: bool = False,
) -> str:
    """Run the full episode production pipeline.

    Orchestrates all sub-pipelines for each configured language:
    1. Script generation (once, shared across languages)
    2. Voice generation (per language)
    3. Audio cleanup (per language)
    4. Episode assembly (per language)
    5. Distribution (per language)

    Args:
        settings: Pipeline settings.
        topics: Comma-separated topics for script generation.
        script_file: Path to manual script file.
        langs: Comma-separated language codes (default: all configured).
        skip_cleanup: Skip audio cleanup step.

    Returns a human-readable summary of all pipeline runs.
    """
    config = PodcastConfig(settings.podcast_config_file)
    episode_id = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")

    # Determine languages to process
    if langs:
        language_codes = [l.strip() for l in langs.split(",")]
    else:
        language_codes = config.language_codes

    summaries: list[str] = []

    # Step 1: Generate script (shared)
    script_context: dict[str, Any] = {
        "settings": settings,
        "pipeline_name": "script_generation",
    }
    if topics:
        script_context["topics"] = topics
    if script_file:
        script_context["manual_script"] = Path(script_file).read_text(encoding="utf-8")

    script_pipeline = build_script_pipeline()
    script_result = script_pipeline.run(script_context)
    summaries.append(script_result.summary())

    if not script_result.success:
        return "\n\n".join(summaries)

    script = script_result.context.get("script", {})

    # Steps 2-5: Per language
    for lang_code in language_codes:
        lang_config = config.language_config(lang_code)
        if not lang_config:
            logger.warning("Language '%s' not configured, skipping", lang_code)
            continue

        logger.info("Processing language: %s (%s)", lang_code, lang_config.get("label"))

        # Build shared context for this language
        lang_context: dict[str, Any] = {
            "settings": settings,
            "pipeline_name": f"episode_{lang_code}",
            "episode_id": episode_id,
            "language": lang_code,
            "language_config": lang_config,
            "script": script,
            "skip_cleanup": skip_cleanup,
        }

        # Step 2: Voice generation
        voice_pipeline = build_voice_pipeline()
        voice_result = voice_pipeline.run(lang_context)
        summaries.append(voice_result.summary())
        if not voice_result.success:
            continue
        lang_context.update(voice_result.context)

        # Step 3: Audio cleanup (optional)
        if not skip_cleanup:
            cleanup_pipeline = build_cleanup_pipeline()
            cleanup_result = cleanup_pipeline.run(lang_context)
            summaries.append(cleanup_result.summary())
            if not cleanup_result.success:
                continue
            lang_context.update(cleanup_result.context)

        # Step 4: Episode assembly
        assembly_pipeline = build_assembly_pipeline()
        assembly_result = assembly_pipeline.run(lang_context)
        summaries.append(assembly_result.summary())
        if not assembly_result.success:
            continue
        lang_context.update(assembly_result.context)

        # Step 5: Distribution
        # Build episode summary for notifications
        lang_context["episode_summary"] = (
            f"Episode produced: {script.get('title', 'Untitled')}\n"
            f"Language: {lang_code}\n"
            f"File: {lang_context.get('episode_mp3', 'N/A')}"
        )
        lang_context["content"] = lang_context["episode_summary"]

        distribute_pipeline = build_distribute_pipeline()
        dist_result = distribute_pipeline.run(lang_context)
        summaries.append(dist_result.summary())

    return "\n\n".join(summaries)
