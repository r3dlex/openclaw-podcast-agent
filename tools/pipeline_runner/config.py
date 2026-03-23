"""Configuration management for podcast pipelines.

Loads settings from environment variables and config files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings

_log = logging.getLogger(__name__)


class PodcastSettings(BaseSettings):
    """Pipeline configuration loaded from environment variables."""

    # Paths
    podcast_data_dir: Path = Field(default=Path("."), alias="PODCAST_DATA_DIR")
    podcast_workspace_dir: Path = Field(default=Path("."), alias="PODCAST_WORKSPACE_DIR")
    podcast_config_file: Path = Field(
        default=Path("config/podcast.json"), alias="PODCAST_CONFIG_FILE"
    )
    librarian_agent_workspace: Path = Field(default=Path(""), alias="LIBRARIAN_AGENT_WORKSPACE")

    # Inter-Agent Message Queue (IAMQ)
    iamq_http_url: str = Field(default="http://127.0.0.1:18790", alias="IAMQ_HTTP_URL")
    iamq_agent_id: str = Field(default="podcast_agent", alias="IAMQ_AGENT_ID")

    # LLM (Ollama)
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL")

    # TTS
    tts_engine: str = Field(default="mlx-audio", alias="TTS_ENGINE")
    tts_quantization: int = Field(default=4, alias="TTS_QUANTIZATION")

    # Network
    request_timeout: int = Field(default=30, alias="REQUEST_TIMEOUT")

    # Mounted path for librarian workspace (when running in Docker)
    librarian_workspace_mount: Path = Field(default=Path(""), alias="LIBRARIAN_WORKSPACE_MOUNT")

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def log_dir(self) -> Path:
        """Return the log directory, creating it if necessary."""
        path = self.podcast_data_dir / "log"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def output_dir(self) -> Path:
        """Return the output directory, creating it if necessary."""
        path = self.podcast_data_dir / "output"
        path.mkdir(parents=True, exist_ok=True)
        return path


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
