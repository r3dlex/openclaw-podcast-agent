"""Tests for podcast_renderer.llm.shownotes — ShowNotesStep."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from podcast_renderer.llm.shownotes import ShowNotesStep


class TestShowNotesStep:
    def test_name(self) -> None:
        assert ShowNotesStep().name == "show_notes"

    def test_should_run_with_transcript_text(self) -> None:
        step = ShowNotesStep()
        assert step.should_run({"transcript": {"text": "Hello world."}})

    def test_should_not_run_with_empty_transcript_text(self) -> None:
        step = ShowNotesStep()
        assert not step.should_run({"transcript": {"text": ""}})

    def test_should_not_run_without_transcript(self) -> None:
        step = ShowNotesStep()
        assert not step.should_run({})

    @patch("podcast_renderer.llm.shownotes.anthropic")
    def test_execute_calls_minimax(self, mock_anthropic: MagicMock) -> None:
        from types import SimpleNamespace

        settings = SimpleNamespace(
            llm_base_url="https://api.minimax.io/anthropic",
            llm_api_key="test-key",
            llm_model="MiniMax-M2.7",
        )

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "## Summary\n\nGreat episode."

        mock_message = MagicMock()
        mock_message.content = [mock_text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        ctx: dict[str, Any] = {
            "settings": settings,
            "transcript": {"text": "Welcome to the podcast. Today we discuss AI."},
        }
        result = ShowNotesStep().execute(ctx)
        assert result["show_notes"] == "## Summary\n\nGreat episode."

    @patch("podcast_renderer.llm.shownotes.anthropic")
    def test_execute_truncates_long_transcript(self, mock_anthropic: MagicMock) -> None:
        from types import SimpleNamespace

        settings = SimpleNamespace(
            llm_base_url="https://api.minimax.io/anthropic",
            llm_api_key="test-key",
            llm_model="MiniMax-M2.7",
        )

        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "## Summary\n\nTruncated."

        mock_message = MagicMock()
        mock_message.content = [mock_text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        # Long transcript (> 8000 chars)
        long_text = "word " * 2000
        ctx: dict[str, Any] = {
            "settings": settings,
            "transcript": {"text": long_text},
        }
        result = ShowNotesStep().execute(ctx)
        # The prompt passed to LLM should be <= 8000 chars + header text
        call_kwargs = mock_client.messages.create.call_args
        message_content = call_kwargs[1]["messages"][0]["content"]
        assert "transcript truncated" in message_content

    @patch("podcast_renderer.llm.shownotes.anthropic")
    def test_execute_fallback_on_api_error(self, mock_anthropic: MagicMock) -> None:
        from types import SimpleNamespace

        settings = SimpleNamespace(
            llm_base_url="https://api.minimax.io/anthropic",
            llm_api_key="test-key",
            llm_model="MiniMax-M2.7",
        )

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic.Anthropic.return_value = mock_client

        ctx: dict[str, Any] = {
            "settings": settings,
            "transcript": {"text": "This is the transcript text."},
        }
        result = ShowNotesStep().execute(ctx)
        assert "show_notes" in result
        # Fallback should include beginning of transcript
        assert "This is the transcript" in result["show_notes"]

    @patch("podcast_renderer.llm.shownotes.anthropic")
    def test_execute_multiple_text_blocks(self, mock_anthropic: MagicMock) -> None:
        from types import SimpleNamespace

        settings = SimpleNamespace(
            llm_base_url="https://api.minimax.io/anthropic",
            llm_api_key="test-key",
            llm_model="MiniMax-M2.7",
        )

        block1 = MagicMock()
        block1.type = "text"
        block1.text = "## Summary\n\n"

        block2 = MagicMock()
        block2.type = "text"
        block2.text = "A great episode."

        mock_message = MagicMock()
        mock_message.content = [block1, block2]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        ctx: dict[str, Any] = {
            "settings": settings,
            "transcript": {"text": "Hello."},
        }
        result = ShowNotesStep().execute(ctx)
        assert result["show_notes"] == "## Summary\n\nA great episode."
