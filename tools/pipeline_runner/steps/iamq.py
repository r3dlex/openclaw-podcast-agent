"""Inter-Agent Message Queue (IAMQ) step — announce pipeline results to other agents.

Integrates with the OpenClaw IAMQ service (Elixir/OTP) for agent-to-agent
communication. Sends pipeline completion announcements and checks the
podcast agent's inbox for pending tasks from other agents.

The IAMQ runs at IAMQ_HTTP_URL (default: http://127.0.0.1:18790).
See openclaw-inter-agent-message-queue/spec/API.md for the full protocol.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from pipeline_runner.config import PodcastSettings

logger = logging.getLogger(__name__)

AGENT_ID = "podcast_agent"

# Registration metadata — sent to IAMQ on startup for agent discovery
AGENT_METADATA: dict[str, Any] = {
    "agent_id": AGENT_ID,
    "name": "Podcaster",
    "emoji": "\U0001f399",
    "description": "Podcast production: script generation, TTS synthesis, audio processing, distribution",
    "capabilities": [
        "script_generation",
        "voice_synthesis",
        "audio_cleanup",
        "episode_assembly",
        "transcription",
        "rss_distribution",
        "multilingual",
        "voice_cloning",
    ],
}


class IAMQAnnounceStep:
    """Announce pipeline completion to the IAMQ.

    Sends the episode summary to the Librarian agent for archival.
    Gracefully degrades when the IAMQ service is unreachable —
    a pipeline should never fail because the message queue is down.

    Context in:  episode_summary | content (str), pipeline_name
    Context out: iamq_announced (bool), iamq_message_id (str | None)
    """

    name = "iamq_announce"

    def should_run(self, context: dict[str, Any]) -> bool:
        settings: PodcastSettings = context.get("settings", PodcastSettings())
        if not settings.iamq_http_url:
            return False
        return "episode_summary" in context or "content" in context

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        settings: PodcastSettings = context.get("settings", PodcastSettings())
        pipeline_name = context.get("pipeline_name", "unknown")
        content = context.get("episode_summary") or context.get("content", "")

        if not content:
            context["iamq_announced"] = False
            context["iamq_message_id"] = None
            return context

        payload = {
            "from": AGENT_ID,
            "to": "librarian_agent",
            "type": "info",
            "priority": "NORMAL",
            "subject": f"Episode Produced: {pipeline_name}",
            "body": content,
        }

        try:
            url = f"{settings.iamq_http_url}/send"
            resp = requests.post(url, json=payload, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            msg_id = data.get("id", data.get("message_id"))
            context["iamq_announced"] = True
            context["iamq_message_id"] = msg_id
            logger.info("IAMQ: announced '%s' (id=%s)", pipeline_name, msg_id)
        except requests.ConnectionError:
            logger.warning("IAMQ: service unreachable at %s — skipping", settings.iamq_http_url)
            context["iamq_announced"] = False
            context["iamq_message_id"] = None
        except Exception:
            logger.warning("IAMQ: announce failed", exc_info=True)
            context["iamq_announced"] = False
            context["iamq_message_id"] = None

        return context


def iamq_register(settings: PodcastSettings) -> bool:
    """Register the podcast agent with the IAMQ service (with metadata)."""
    if not settings.iamq_http_url:
        return False
    try:
        url = f"{settings.iamq_http_url}/register"
        payload = {**AGENT_METADATA}
        payload["workspace"] = str(settings.podcast_workspace_dir.resolve())
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        logger.info("IAMQ: registered as '%s' with metadata", AGENT_ID)
        return True
    except Exception:
        logger.warning("IAMQ: registration failed", exc_info=True)
        return False


def iamq_heartbeat(settings: PodcastSettings) -> bool:
    """Send a heartbeat to the IAMQ service."""
    if not settings.iamq_http_url:
        return False
    try:
        url = f"{settings.iamq_http_url}/heartbeat"
        resp = requests.post(url, json={"agent_id": AGENT_ID}, timeout=5)
        resp.raise_for_status()
        return True
    except Exception:
        logger.debug("IAMQ: heartbeat failed", exc_info=True)
        return False


def iamq_check_inbox(settings: PodcastSettings) -> list[dict[str, Any]]:
    """Fetch unread messages from the podcast agent's IAMQ inbox."""
    if not settings.iamq_http_url:
        return []
    try:
        url = f"{settings.iamq_http_url}/inbox/{AGENT_ID}?status=unread"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        messages: list[dict[str, Any]] = resp.json().get("messages", resp.json())
        if isinstance(messages, list):
            return messages
        return []
    except Exception:
        logger.debug("IAMQ: inbox check failed", exc_info=True)
        return []


def iamq_send_message(
    settings: PodcastSettings,
    *,
    to: str,
    subject: str,
    body: str,
    priority: str = "NORMAL",
    msg_type: str = "info",
    reply_to: str | None = None,
) -> str | None:
    """Send a direct message to another agent via IAMQ. Returns message ID."""
    if not settings.iamq_http_url:
        return None
    try:
        url = f"{settings.iamq_http_url}/send"
        payload: dict[str, Any] = {
            "from": AGENT_ID,
            "to": to,
            "type": msg_type,
            "priority": priority,
            "subject": subject,
            "body": body,
        }
        if reply_to:
            payload["replyTo"] = reply_to
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        msg_id: str | None = data.get("id", data.get("message_id"))
        logger.info("IAMQ: sent message to '%s' (id=%s)", to, msg_id)
        return msg_id
    except Exception:
        logger.warning("IAMQ: send to '%s' failed", to, exc_info=True)
        return None


def iamq_mark_message(
    settings: PodcastSettings,
    message_id: str,
    status: str = "acted",
) -> bool:
    """Update a message's status (read, acted, archived)."""
    if not settings.iamq_http_url:
        return False
    try:
        url = f"{settings.iamq_http_url}/messages/{message_id}"
        resp = requests.patch(url, json={"status": status}, timeout=5)
        resp.raise_for_status()
        logger.info("IAMQ: marked message %s as %s", message_id, status)
        return True
    except Exception:
        logger.warning("IAMQ: mark message %s failed", message_id, exc_info=True)
        return False
