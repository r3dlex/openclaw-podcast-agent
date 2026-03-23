"""Show notes generation step — create episode show notes via Ollama.

Generates structured show notes from the transcript including:
summary, key topics, timestamps, and links.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from pipeline_runner.config import PodcastSettings

logger = logging.getLogger(__name__)

SHOWNOTES_PROMPT = """Generate podcast show notes from this transcript. Output in Markdown:

## Summary
(2-3 sentence summary)

## Key Topics
- Topic 1
- Topic 2

## Timestamps
- 00:00 - Introduction
- (timestamps from content)

Keep it concise and useful for listeners browsing the episode description.

Transcript:
"""


class ShowNotesStep:
    """Generate show notes from transcript via Ollama.

    Context in:  transcript (dict with text), settings
    Context out: show_notes (str, Markdown)
    """

    name = "show_notes"

    def should_run(self, context: dict[str, Any]) -> bool:
        transcript = context.get("transcript", {})
        return bool(transcript.get("text"))

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        settings: PodcastSettings = context.get("settings", PodcastSettings())
        transcript_text = context["transcript"]["text"]

        # Truncate transcript for LLM context limits
        max_chars = 4000
        if len(transcript_text) > max_chars:
            transcript_text = transcript_text[:max_chars] + "\n\n[transcript truncated]"

        prompt = SHOWNOTES_PROMPT + transcript_text

        try:
            url = f"{settings.ollama_base_url}/api/generate"
            payload = {
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
            }
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            context["show_notes"] = data.get("response", "")
            logger.info("Generated show notes (%d chars)", len(context["show_notes"]))
        except Exception:
            logger.warning("Show notes generation failed, using fallback")
            context["show_notes"] = f"## Summary\n\n{transcript_text[:200]}..."

        return context
