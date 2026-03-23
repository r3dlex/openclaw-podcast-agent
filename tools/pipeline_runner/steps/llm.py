"""Ollama LLM step — generate a podcast script from topics or pass through manual scripts.

Uses the Ollama HTTP API for local LLM inference. Supports manual script
passthrough when a pre-written script is provided.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from pipeline_runner.config import PodcastSettings

logger = logging.getLogger(__name__)

# Default system prompt for podcast script generation
SCRIPT_SYSTEM_PROMPT = """You are a podcast scriptwriter. Generate a podcast script as JSON.

Output format (strict JSON, no markdown fences):
{
  "title": "Episode title",
  "description": "Brief episode description",
  "segments": [
    {
      "speaker": "host",
      "text": "The spoken text for this segment.",
      "notes": "Optional production notes"
    }
  ],
  "language": "en"
}

Guidelines:
- Write natural, conversational dialogue suitable for text-to-speech
- Keep segments between 1-3 sentences each
- Use simple punctuation (periods, commas, question marks)
- Avoid abbreviations, URLs, or special characters that TTS handles poorly
- Include a brief intro and outro segment
- Total script should be 5-15 segments for a short episode
"""


class OllamaScriptStep:
    """Generate a podcast script from topics via Ollama, or pass through a manual script.

    Context in:  topics (str) and/or manual_script (str), settings, language (optional)
    Context out: script (dict with title, description, segments, language)
    """

    name = "ollama_script"

    def should_run(self, context: dict[str, Any]) -> bool:
        return "topics" in context or "manual_script" in context

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        # Manual script passthrough
        if "manual_script" in context and context["manual_script"]:
            script = self._parse_manual_script(context["manual_script"], context)
            context["script"] = script
            logger.info("Using manual script: %s", script.get("title", "untitled"))
            return context

        # Generate via Ollama
        settings: PodcastSettings = context.get("settings", PodcastSettings())
        topics = context.get("topics", "")
        language = context.get("language", "en")

        prompt = f"Create a podcast script about: {topics}\nLanguage: {language}"

        script = self._call_ollama(settings, prompt)
        if script:
            context["script"] = script
            logger.info("Generated script: %s (%d segments)", script.get("title", "untitled"), len(script.get("segments", [])))
        else:
            # Fallback: wrap topics as a simple single-segment script
            context["script"] = {
                "title": f"Episode: {topics}",
                "description": topics,
                "segments": [{"speaker": "host", "text": topics, "notes": ""}],
                "language": language,
            }
            logger.warning("Ollama unavailable, using fallback script")

        return context

    def _call_ollama(self, settings: PodcastSettings, prompt: str) -> dict[str, Any] | None:
        """Call Ollama API to generate a script."""
        url = f"{settings.ollama_base_url}/api/generate"
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "system": SCRIPT_SYSTEM_PROMPT,
            "stream": False,
            "format": "json",
        }

        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "")
            return self._parse_json_response(response_text)
        except requests.ConnectionError:
            logger.warning("Ollama unreachable at %s", settings.ollama_base_url)
            return None
        except requests.Timeout:
            logger.warning("Ollama request timed out")
            return None
        except Exception:
            logger.warning("Ollama script generation failed", exc_info=True)
            return None

    def _parse_json_response(self, text: str) -> dict[str, Any] | None:
        """Parse JSON from LLM response, handling common issues."""
        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (fences)
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            result: dict[str, Any] = json.loads(cleaned)
            # Validate required fields
            if "segments" not in result:
                logger.warning("LLM response missing 'segments' field")
                return None
            return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON: %s", text[:200])
            return None

    def _parse_manual_script(
        self, script_text: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Parse a manual script — either JSON or plain text."""
        language = context.get("language", "en")

        # Try JSON first
        try:
            result: dict[str, Any] = json.loads(script_text)
            if "segments" in result:
                return result
        except json.JSONDecodeError:
            pass

        # Plain text: split into paragraphs as segments
        paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]
        segments = [
            {"speaker": "host", "text": para, "notes": ""}
            for para in paragraphs
        ]

        return {
            "title": paragraphs[0][:80] if paragraphs else "Untitled",
            "description": "",
            "segments": segments,
            "language": language,
        }
