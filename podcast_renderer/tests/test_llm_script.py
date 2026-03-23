"""Tests for the MiniMax script generation step."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from podcast_renderer.llm.script import ScriptGenerationStep


@pytest.fixture
def settings() -> SimpleNamespace:
    """Mock settings object with LLM config attributes."""
    return SimpleNamespace(
        llm_base_url="https://api.minimax.io/anthropic",
        llm_api_key="test-key",
        llm_model="MiniMax-M2.7",
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


class TestScriptGenerationStep:
    """Test ScriptGenerationStep."""

    def test_should_run_with_topics(self) -> None:
        step = ScriptGenerationStep()
        assert step.should_run({"topics": "AI news"})

    def test_should_run_with_manual_script(self) -> None:
        step = ScriptGenerationStep()
        assert step.should_run({"manual_script": "Hello world"})

    def test_should_not_run_without_input(self) -> None:
        step = ScriptGenerationStep()
        assert not step.should_run({})

    def test_manual_script_json_passthrough(self, settings: SimpleNamespace) -> None:
        script_json = json.dumps({
            "title": "Manual Episode",
            "description": "A manual script",
            "segments": [
                {"speaker": "host", "text": "Hello listeners.", "notes": ""},
            ],
            "language": "en",
        })

        step = ScriptGenerationStep()
        context: dict[str, Any] = {
            "settings": settings,
            "manual_script": script_json,
        }
        result = step.execute(context)

        assert "script" in result
        assert result["script"]["title"] == "Manual Episode"
        assert len(result["script"]["segments"]) == 1

    def test_manual_script_plain_text(self, settings: SimpleNamespace) -> None:
        plain_text = "Welcome to the show.\n\nToday we discuss AI.\n\nThanks for listening."

        step = ScriptGenerationStep()
        context: dict[str, Any] = {
            "settings": settings,
            "manual_script": plain_text,
        }
        result = step.execute(context)

        assert "script" in result
        assert len(result["script"]["segments"]) == 3
        assert result["script"]["segments"][0]["text"] == "Welcome to the show."

    @patch("podcast_renderer.llm.script.anthropic")
    def test_minimax_success(
        self,
        mock_anthropic: MagicMock,
        settings: SimpleNamespace,
        sample_script_json: str,
    ) -> None:
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = sample_script_json

        mock_message = MagicMock()
        mock_message.content = [mock_text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        step = ScriptGenerationStep()
        context: dict[str, Any] = {
            "settings": settings,
            "topics": "AI news",
            "language": "en",
        }
        result = step.execute(context)

        assert "script" in result
        assert result["script"]["title"] == "AI News This Week"
        assert len(result["script"]["segments"]) == 3

        mock_anthropic.Anthropic.assert_called_once_with(
            base_url="https://api.minimax.io/anthropic",
            api_key="test-key",
        )

    @patch("podcast_renderer.llm.script.anthropic")
    def test_minimax_error_fallback(
        self, mock_anthropic: MagicMock, settings: SimpleNamespace
    ) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic.Anthropic.return_value = mock_client

        step = ScriptGenerationStep()
        context: dict[str, Any] = {
            "settings": settings,
            "topics": "AI safety",
            "language": "en",
        }
        result = step.execute(context)

        assert "script" in result
        assert result["script"]["segments"][0]["text"] == "AI safety"

    @patch("podcast_renderer.llm.script.anthropic")
    def test_minimax_invalid_json_fallback(
        self, mock_anthropic: MagicMock, settings: SimpleNamespace
    ) -> None:
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "not valid json at all"

        mock_message = MagicMock()
        mock_message.content = [mock_text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        step = ScriptGenerationStep()
        context: dict[str, Any] = {
            "settings": settings,
            "topics": "test",
        }
        result = step.execute(context)

        assert "script" in result
        assert len(result["script"]["segments"]) >= 1

    def test_name(self) -> None:
        assert ScriptGenerationStep().name == "script_generation"

    def test_manual_script_takes_precedence(self, settings: SimpleNamespace) -> None:
        step = ScriptGenerationStep()
        context: dict[str, Any] = {
            "settings": settings,
            "topics": "AI news",
            "manual_script": json.dumps({
                "title": "Manual",
                "segments": [{"speaker": "host", "text": "Manual text.", "notes": ""}],
                "language": "en",
            }),
        }
        result = step.execute(context)
        assert result["script"]["title"] == "Manual"
