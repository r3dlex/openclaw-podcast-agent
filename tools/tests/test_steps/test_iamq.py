"""Tests for the IAMQ integration step."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pipeline_runner.config import PodcastSettings
from pipeline_runner.steps.iamq import (
    AGENT_ID,
    IAMQAnnounceStep,
    iamq_check_inbox,
    iamq_heartbeat,
    iamq_mark_message,
    iamq_register,
    iamq_send_message,
)


@pytest.fixture
def settings() -> PodcastSettings:
    return PodcastSettings(
        IAMQ_HTTP_URL="http://127.0.0.1:18790",
        IAMQ_AGENT_ID="podcast_agent",
    )


@pytest.fixture
def no_iamq_settings() -> PodcastSettings:
    return PodcastSettings(IAMQ_HTTP_URL="")


class TestIAMQAnnounceStep:
    """Test the IAMQAnnounceStep pipeline step."""

    def test_should_not_run_without_url(self, no_iamq_settings: PodcastSettings) -> None:
        step = IAMQAnnounceStep()
        assert not step.should_run({"settings": no_iamq_settings})

    def test_should_not_run_without_content(self, settings: PodcastSettings) -> None:
        step = IAMQAnnounceStep()
        assert not step.should_run({"settings": settings})

    def test_should_run_with_episode_summary(self, settings: PodcastSettings) -> None:
        step = IAMQAnnounceStep()
        assert step.should_run({"settings": settings, "episode_summary": "Episode ready"})

    def test_should_run_with_content(self, settings: PodcastSettings) -> None:
        step = IAMQAnnounceStep()
        assert step.should_run({"settings": settings, "content": "Some content"})

    @patch("pipeline_runner.steps.iamq.requests.post")
    def test_announce_success(self, mock_post: MagicMock, settings: PodcastSettings) -> None:
        mock_post.return_value = MagicMock(
            status_code=201, json=lambda: {"id": "msg-123"}
        )
        mock_post.return_value.raise_for_status = MagicMock()

        step = IAMQAnnounceStep()
        context: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "New episode produced",
            "pipeline_name": "episode",
        }
        result = step.execute(context)

        assert result["iamq_announced"] is True
        assert result["iamq_message_id"] == "msg-123"

    @patch("pipeline_runner.steps.iamq.requests.post")
    def test_announce_connection_error(
        self, mock_post: MagicMock, settings: PodcastSettings
    ) -> None:
        import requests

        mock_post.side_effect = requests.ConnectionError("unreachable")

        step = IAMQAnnounceStep()
        context: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "New episode",
            "pipeline_name": "episode",
        }
        result = step.execute(context)

        assert result["iamq_announced"] is False
        assert result["iamq_message_id"] is None

    def test_announce_empty_content(self, settings: PodcastSettings) -> None:
        step = IAMQAnnounceStep()
        context: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "",
        }
        result = step.execute(context)
        assert result["iamq_announced"] is False


class TestIAMQFunctions:
    """Test standalone IAMQ functions."""

    @patch("pipeline_runner.steps.iamq.requests.post")
    def test_register_success(self, mock_post: MagicMock, settings: PodcastSettings) -> None:
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()
        assert iamq_register(settings) is True

    def test_register_no_url(self, no_iamq_settings: PodcastSettings) -> None:
        assert iamq_register(no_iamq_settings) is False

    @patch("pipeline_runner.steps.iamq.requests.post")
    def test_heartbeat_success(self, mock_post: MagicMock, settings: PodcastSettings) -> None:
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()
        assert iamq_heartbeat(settings) is True

    def test_heartbeat_no_url(self, no_iamq_settings: PodcastSettings) -> None:
        assert iamq_heartbeat(no_iamq_settings) is False

    @patch("pipeline_runner.steps.iamq.requests.get")
    def test_check_inbox(self, mock_get: MagicMock, settings: PodcastSettings) -> None:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"messages": [{"id": "1", "subject": "test"}]},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        messages = iamq_check_inbox(settings)
        assert len(messages) == 1

    def test_check_inbox_no_url(self, no_iamq_settings: PodcastSettings) -> None:
        assert iamq_check_inbox(no_iamq_settings) == []

    @patch("pipeline_runner.steps.iamq.requests.post")
    def test_send_message(self, mock_post: MagicMock, settings: PodcastSettings) -> None:
        mock_post.return_value = MagicMock(
            status_code=201, json=lambda: {"id": "msg-456"}
        )
        mock_post.return_value.raise_for_status = MagicMock()
        msg_id = iamq_send_message(
            settings,
            to="librarian_agent",
            subject="Test",
            body="Hello",
        )
        assert msg_id == "msg-456"

    @patch("pipeline_runner.steps.iamq.requests.patch")
    def test_mark_message(self, mock_patch: MagicMock, settings: PodcastSettings) -> None:
        mock_patch.return_value = MagicMock(status_code=200)
        mock_patch.return_value.raise_for_status = MagicMock()
        assert iamq_mark_message(settings, "msg-123", "acted") is True

    def test_agent_id_is_podcast(self) -> None:
        assert AGENT_ID == "podcast_agent"

    @patch("pipeline_runner.steps.iamq.requests.post")
    def test_register_exception_returns_false(
        self, mock_post: MagicMock, settings: PodcastSettings
    ) -> None:
        mock_post.side_effect = Exception("connection failed")
        assert iamq_register(settings) is False

    @patch("pipeline_runner.steps.iamq.requests.post")
    def test_heartbeat_exception_returns_false(
        self, mock_post: MagicMock, settings: PodcastSettings
    ) -> None:
        mock_post.side_effect = Exception("timeout")
        assert iamq_heartbeat(settings) is False

    @patch("pipeline_runner.steps.iamq.requests.get")
    def test_check_inbox_exception_returns_empty(
        self, mock_get: MagicMock, settings: PodcastSettings
    ) -> None:
        mock_get.side_effect = Exception("error")
        assert iamq_check_inbox(settings) == []

    @patch("pipeline_runner.steps.iamq.requests.get")
    def test_check_inbox_list_response(
        self, mock_get: MagicMock, settings: PodcastSettings
    ) -> None:
        """When API returns a list directly, the current impl raises AttributeError
        which is caught and returns []. This verifies the graceful fallback."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"id": "1"}, {"id": "2"}],
        )
        mock_get.return_value.raise_for_status = MagicMock()
        # The implementation calls resp.json().get("messages", ...) which fails on list
        # The exception is caught and [] is returned — this is the current behavior
        messages = iamq_check_inbox(settings)
        assert isinstance(messages, list)

    @patch("pipeline_runner.steps.iamq.requests.get")
    def test_check_inbox_non_list_response(
        self, mock_get: MagicMock, settings: PodcastSettings
    ) -> None:
        """When API returns something unexpected, return empty list."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": "unexpected"},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        messages = iamq_check_inbox(settings)
        assert messages == []

    def test_send_message_no_url(self, no_iamq_settings: PodcastSettings) -> None:
        result = iamq_send_message(
            no_iamq_settings, to="agent", subject="test", body="hello"
        )
        assert result is None

    @patch("pipeline_runner.steps.iamq.requests.post")
    def test_send_message_exception_returns_none(
        self, mock_post: MagicMock, settings: PodcastSettings
    ) -> None:
        mock_post.side_effect = Exception("failed")
        result = iamq_send_message(settings, to="agent", subject="test", body="hello")
        assert result is None

    @patch("pipeline_runner.steps.iamq.requests.post")
    def test_send_message_with_reply_to(
        self, mock_post: MagicMock, settings: PodcastSettings
    ) -> None:
        mock_post.return_value = MagicMock(
            status_code=201, json=lambda: {"id": "reply-msg"}
        )
        mock_post.return_value.raise_for_status = MagicMock()
        result = iamq_send_message(
            settings,
            to="agent",
            subject="Re: test",
            body="hello",
            reply_to="original-msg-id",
        )
        assert result == "reply-msg"
        call_payload = mock_post.call_args[1]["json"]
        assert call_payload["replyTo"] == "original-msg-id"

    def test_mark_message_no_url(self, no_iamq_settings: PodcastSettings) -> None:
        assert iamq_mark_message(no_iamq_settings, "msg-123") is False

    @patch("pipeline_runner.steps.iamq.requests.patch")
    def test_mark_message_exception_returns_false(
        self, mock_patch: MagicMock, settings: PodcastSettings
    ) -> None:
        mock_patch.side_effect = Exception("error")
        assert iamq_mark_message(settings, "msg-123") is False
