"""Script generation pipeline — topics/manual text to structured podcast script.

Steps: OllamaScriptStep -> TextSegmentationStep
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline_runner.config import PodcastSettings
from pipeline_runner.runner import Pipeline
from podcast_renderer.content.segment import TextSegmentationStep
from podcast_renderer.llm.script import ScriptGenerationStep


def build_script_pipeline() -> Pipeline:
    """Build the script generation pipeline."""
    pipeline = Pipeline("script_generation")
    pipeline.add_step(ScriptGenerationStep())
    pipeline.add_step(TextSegmentationStep())
    return pipeline


def run_script_pipeline(
    settings: PodcastSettings,
    *,
    topics: str | None = None,
    script_file: str | None = None,
    lang: str | None = None,
) -> str:
    """Run the script generation pipeline.

    Returns a human-readable summary of the pipeline run.
    """
    context: dict[str, Any] = {
        "settings": settings,
        "pipeline_name": "script_generation",
    }

    if topics:
        context["topics"] = topics

    if script_file:
        path = Path(script_file)
        context["manual_script"] = path.read_text(encoding="utf-8")

    if lang:
        context["language"] = lang

    pipeline = build_script_pipeline()
    result = pipeline.run(context)

    # Write script to output if successful
    if result.success and "script" in result.context:
        script = result.context["script"]
        output_dir = settings.output_dir
        script_path = output_dir / "latest_script.json"
        script_path.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")

    return result.summary()
