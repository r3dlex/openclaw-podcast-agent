"""Show notes generation step — create episode show notes via MiniMax.

Uses MiniMax's Anthropic-compatible API to generate structured show notes
from the transcript including: summary, key topics, timestamps, and links.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

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
    """Generate show notes from transcript via MiniMax.

    Context in:  transcript (dict with text), settings
    Context out: show_notes (str, Markdown)
    """

    name = "show_notes"

    def should_run(self, context: dict[str, Any]) -> bool:
        transcript = context.get("transcript", {})
        return bool(transcript.get("text"))

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        settings = context.get("settings")
        transcript_text = context["transcript"]["text"]

        # Truncate transcript for context limits
        max_chars = 8000
        if len(transcript_text) > max_chars:
            transcript_text = transcript_text[:max_chars] + "\n\n[transcript truncated]"

        prompt = SHOWNOTES_PROMPT + transcript_text

        try:
            client = anthropic.Anthropic(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
            )

            message = client.messages.create(
                model=settings.llm_model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text

            context["show_notes"] = response_text
            logger.info("Generated show notes (%d chars)", len(context["show_notes"]))

        except Exception:
            logger.warning("Show notes generation failed, using fallback")
            context["show_notes"] = f"## Summary\n\n{transcript_text[:200]}..."

        return context
