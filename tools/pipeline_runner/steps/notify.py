"""IAMQ notification step — announce pipeline results to other agents.

User-facing notifications (Telegram, WhatsApp) are handled by the OpenClaw
gateway. This step sends pipeline results to the IAMQ so sibling agents
(Librarian, Main) are informed. Gracefully degrades when IAMQ is down.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from pipeline_runner.config import PodcastSettings

logger = logging.getLogger(__name__)


class IAMQNotifyStep:
    """Announce pipeline completion via IAMQ.

    Context in:  episode_summary or content (str), pipeline_name
    Context out: iamq_notified (bool), iamq_message_id (str | None)
    """

    name = "iamq_notify"

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
            context["iamq_notified"] = False
            context["iamq_message_id"] = None
            return context

        payload = {
            "from": settings.iamq_agent_id,
            "to": "librarian_agent",
            "type": "info",
            "priority": "NORMAL",
            "subject": f"Podcast episode: {pipeline_name}",
            "body": content,
        }

        try:
            url = f"{settings.iamq_http_url}/send"
            resp = requests.post(url, json=payload, timeout=settings.request_timeout)
            resp.raise_for_status()
            data = resp.json()
            msg_id = data.get("id", data.get("message_id"))
            context["iamq_notified"] = True
            context["iamq_message_id"] = msg_id
            logger.info("IAMQ: announced '%s' (id=%s)", pipeline_name, msg_id)
        except requests.ConnectionError:
            logger.warning("IAMQ: service unreachable at %s — skipping", settings.iamq_http_url)
            context["iamq_notified"] = False
            context["iamq_message_id"] = None
        except Exception:
            logger.warning("IAMQ: announce failed", exc_info=True)
            context["iamq_notified"] = False
            context["iamq_message_id"] = None

        return context
