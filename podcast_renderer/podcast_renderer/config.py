"""Podcast configuration loaded from podcast.json.

Provides the PodcastConfig class that reads rendering-related settings
(languages, TTS, audio, loudness) from a JSON config file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)


class PodcastConfig:
    """Podcast configuration loaded from podcast.json."""

    def __init__(self, config_path: Path) -> None:
        self._path = config_path
        self._data: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        """Reload configuration from disk."""
        with open(self._path) as f:
            self._data = json.load(f)

    @property
    def languages(self) -> list[dict[str, str]]:
        """Return configured languages with voice references."""
        result: list[dict[str, str]] = self._data.get("languages", [])
        return result

    @property
    def language_codes(self) -> list[str]:
        """Return list of configured language codes."""
        return [lang["code"] for lang in self.languages]

    def language_config(self, code: str) -> dict[str, str] | None:
        """Return config for a specific language code."""
        for lang in self.languages:
            if lang["code"] == code:
                return lang
        return None

    @property
    def tts(self) -> dict[str, Any]:
        """Return TTS configuration."""
        result: dict[str, Any] = self._data.get("tts", {})
        return result

    @property
    def audio(self) -> dict[str, Any]:
        """Return audio configuration."""
        result: dict[str, Any] = self._data.get("audio", {})
        return result

    @property
    def llm(self) -> dict[str, Any]:
        """Return LLM configuration."""
        result: dict[str, Any] = self._data.get("llm", {})
        return result

    @property
    def podcast_metadata(self) -> dict[str, Any]:
        """Return podcast metadata."""
        result: dict[str, Any] = self._data.get("podcast", {})
        return result

    @property
    def distribution(self) -> dict[str, Any]:
        """Return distribution configuration."""
        result: dict[str, Any] = self._data.get("distribution", {})
        return result

    @property
    def schedule(self) -> dict[str, str]:
        """Return schedule configuration."""
        result: dict[str, str] = self._data.get("schedule", {})
        return result

    @property
    def settings(self) -> dict[str, Any]:
        """Return general settings."""
        result: dict[str, Any] = self._data.get("settings", {})
        return result

    @property
    def max_segment_chars(self) -> int:
        return int(self.tts.get("max_segment_chars", 200))

    @property
    def loudness_target_lufs(self) -> float:
        return float(self.audio.get("loudness_target_lufs", -16))

    @property
    def true_peak_dbtp(self) -> float:
        return float(self.audio.get("true_peak_dbtp", -1.0))

    @property
    def sample_rate(self) -> int:
        return int(self.audio.get("sample_rate", 24000))

    @property
    def mp3_bitrate(self) -> int:
        return int(self.audio.get("mp3_bitrate", 192))

    @property
    def reference_duration_seconds(self) -> int:
        return int(self.audio.get("reference_duration_seconds", 15))

    @property
    def crossfade_ms(self) -> int:
        return int(self.settings.get("crossfade_ms", 500))

    @property
    def intro_audio(self) -> str:
        return str(self.settings.get("intro_audio", ""))

    @property
    def outro_audio(self) -> str:
        return str(self.settings.get("outro_audio", ""))
