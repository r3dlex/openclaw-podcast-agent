"""Configuration management for podcast pipelines.

Loads settings from environment variables and config files.
PodcastConfig has moved to podcast_renderer.config and is re-exported
here for backward compatibility.
"""

from __future__ import annotations

import logging
from pathlib import Path

# Re-export PodcastConfig from its new canonical location
from podcast_renderer.config import PodcastConfig
from pydantic import Field
from pydantic_settings import BaseSettings

_log = logging.getLogger(__name__)

__all__ = ["PodcastConfig", "PodcastSettings"]


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

    # LLM (MiniMax via Anthropic-compatible API)
    llm_base_url: str = Field(default="https://api.minimax.io/anthropic", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="MiniMax-M2.7", alias="LLM_MODEL")

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
