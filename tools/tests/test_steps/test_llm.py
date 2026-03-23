"""Tests for the Ollama LLM script generation step."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pipeline_runner.config import PodcastSettings
from pipeline_runner.steps.llm import OllamaScriptStep


@pytest.fixture
def settings() -> PodcastSettings:
    return PodcastSettings(
        OLLAMA_BASE_URL="http://127.0.0.1:11434",
        OLLAMA_MODEL="llama3.2",
    )


@pytest.fixture
def sample_script_json() -> str:
    return json.dumps({
        "title": "AI News This Week",
        "description": "Weekly AI roundup",
        "segments": [
            {"speaker": "host", "text": "Welcome to the show.", "notes": "intro"},
            {"speaker": "host", "text": "Today we cover AI news.", "notes": ""},
            {"speaker": "host", "text": "Thanks for listening.", "notes": "outro"},
        ],
        "language": "en",
    })


class TestOllamaScriptStep:
    """Test OllamaScriptStep."""

    def test_should_run_with_topics(self) -> None:
        step = OllamaScriptStep()
        assert step.should_run({"topics": "AI news"})

    def test_should_run_with_manual_script(self) -> None:
        step = OllamaScriptStep()
        assert step.should_run({"manual_script": "Hello world"})

    def test_should_not_run_without_input(self) -> None:
        step = OllamaScriptStep()
        assert not step.should_run({})

    def test_manual_script_json_passthrough(self, settings: PodcastSettings) -> None:
        script_json = json.dumps({
            "title": "Manual Episode",
            "description": "A manual script",
            "segments": [
                {"speaker": "host", "text": "Hello listeners.", "notes": ""},
            ],
            "language": "en",
        })

        step = OllamaScriptStep()
        context: dict[str, Any] = {
            "settings": settings,
            "manual_script": script_json,
        }
        result = step.execute(context)

        assert "script" in result
        assert result["script"]["title"] == "Manual Episode"
        assert len(result["script"]["segments"]) == 1

    def test_manual_script_plain_text(self, settings: PodcastSettings) -> None:
        plain_text = "Welcome to the show.\n\nToday we discuss AI.\n\nThanks for listening."

        step = OllamaScriptStep()
        context: dict[str, Any] = {
            "settings": settings,
            "manual_script": plain_text,
        }
        result = step.execute(context)

        assert "script" in result
        assert len(result["script"]["segments"]) == 3
        assert result["script"]["segments"][0]["text"] == "Welcome to the show."

    @patch("pipeline_runner.steps.llm.requests.post")
    def test_ollama_success(
        self,
        mock_post: MagicMock,
        settings: PodcastSettings,
        sample_script_json: str,
    ) -> None:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": sample_script_json},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        step = OllamaScriptStep()
        context: dict[str, Any] = {
            "settings": settings,
            "topics": "AI news",
            "language": "en",
        }
        result = step.execute(context)

        assert "script" in result
        assert result["script"]["title"] == "AI News This Week"
        assert len(result["script"]["segments"]) == 3

    @patch("pipeline_runner.steps.llm.requests.post")
    def test_ollama_connection_error_fallback(
        self, mock_post: MagicMock, settings: PodcastSettings
    ) -> None:
        import requests

        mock_post.side_effect = requests.ConnectionError("unreachable")

        step = OllamaScriptStep()
        context: dict[str, Any] = {
            "settings": settings,
            "topics": "AI safety",
            "language": "en",
        }
        result = step.execute(context)

        # Should produce a fallback script
        assert "script" in result
        assert result["script"]["segments"][0]["text"] == "AI safety"

    @patch("pipeline_runner.steps.llm.requests.post")
    def test_ollama_invalid_json_fallback(
        self, mock_post: MagicMock, settings: PodcastSettings
    ) -> None:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": "not valid json at all"},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        step = OllamaScriptStep()
        context: dict[str, Any] = {
            "settings": settings,
            "topics": "test",
        }
        result = step.execute(context)

        # Should produce a fallback script
        assert "script" in result
        assert len(result["script"]["segments"]) >= 1

    def test_name(self) -> None:
        assert OllamaScriptStep().name == "ollama_script"

    def test_manual_script_takes_precedence(self, settings: PodcastSettings) -> None:
        """Manual script should be used even if topics are also provided."""
        step = OllamaScriptStep()
        context: dict[str, Any] = {
            "settings": settings,
            "topics": "AI news",
            "manual_script": json.dumps({
                "title": "Manual",
                "segments": [{"speaker": "host", "text": "Manual text.", "notes": ""}],
                "language": "en",
            }),
        }
        # No HTTP calls should be made
        result = step.execute(context)
        assert result["script"]["title"] == "Manual"
