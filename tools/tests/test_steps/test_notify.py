"""Tests for IAMQNotifyStep."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from pipeline_runner.config import PodcastSettings
from pipeline_runner.steps.notify import IAMQNotifyStep


@pytest.fixture
def settings() -> PodcastSettings:
    return PodcastSettings(
        IAMQ_HTTP_URL="http://127.0.0.1:18790",
        IAMQ_AGENT_ID="podcast_agent",
    )


@pytest.fixture
def no_iamq_settings() -> PodcastSettings:
    return PodcastSettings(IAMQ_HTTP_URL="")


class TestIAMQNotifyStep:
    def test_name(self) -> None:
        assert IAMQNotifyStep().name == "iamq_notify"

    def test_should_not_run_without_url(self, no_iamq_settings: PodcastSettings) -> None:
        step = IAMQNotifyStep()
        assert not step.should_run({"settings": no_iamq_settings, "episode_summary": "x"})

    def test_should_not_run_without_content(self, settings: PodcastSettings) -> None:
        step = IAMQNotifyStep()
        assert not step.should_run({"settings": settings})

    def test_should_run_with_episode_summary(self, settings: PodcastSettings) -> None:
        step = IAMQNotifyStep()
        assert step.should_run({"settings": settings, "episode_summary": "Done"})

    def test_should_run_with_content(self, settings: PodcastSettings) -> None:
        step = IAMQNotifyStep()
        assert step.should_run({"settings": settings, "content": "Done"})

    @patch("pipeline_runner.steps.notify.requests.post")
    def test_execute_success(self, mock_post: MagicMock, settings: PodcastSettings) -> None:
        mock_post.return_value = MagicMock(
            status_code=201, json=lambda: {"id": "msg-789"}
        )
        mock_post.return_value.raise_for_status = MagicMock()

        step = IAMQNotifyStep()
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "Episode is ready!",
            "pipeline_name": "episode",
        }
        result = step.execute(ctx)
        assert result["iamq_notified"] is True
        assert result["iamq_message_id"] == "msg-789"

    @patch("pipeline_runner.steps.notify.requests.post")
    def test_execute_connection_error(
        self, mock_post: MagicMock, settings: PodcastSettings
    ) -> None:
        mock_post.side_effect = requests.ConnectionError("unreachable")

        step = IAMQNotifyStep()
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "Episode done",
            "pipeline_name": "episode",
        }
        result = step.execute(ctx)
        assert result["iamq_notified"] is False
        assert result["iamq_message_id"] is None

    @patch("pipeline_runner.steps.notify.requests.post")
    def test_execute_generic_exception(
        self, mock_post: MagicMock, settings: PodcastSettings
    ) -> None:
        mock_post.side_effect = Exception("unexpected error")

        step = IAMQNotifyStep()
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "Episode done",
            "pipeline_name": "episode",
        }
        result = step.execute(ctx)
        assert result["iamq_notified"] is False

    def test_execute_empty_content(self, settings: PodcastSettings) -> None:
        step = IAMQNotifyStep()
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "",
            "pipeline_name": "episode",
        }
        result = step.execute(ctx)
        assert result["iamq_notified"] is False
        assert result["iamq_message_id"] is None

    @patch("pipeline_runner.steps.notify.requests.post")
    def test_execute_uses_content_key_as_fallback(
        self, mock_post: MagicMock, settings: PodcastSettings
    ) -> None:
        mock_post.return_value = MagicMock(
            status_code=201, json=lambda: {"id": "msg-abc"}
        )
        mock_post.return_value.raise_for_status = MagicMock()

        step = IAMQNotifyStep()
        ctx: dict[str, Any] = {
            "settings": settings,
            "content": "Script generated",
            "pipeline_name": "script",
        }
        result = step.execute(ctx)
        assert result["iamq_notified"] is True
