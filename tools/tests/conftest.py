"""Shared test fixtures for the podcast pipeline runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipeline_runner.config import PodcastConfig, PodcastSettings


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory with log/ and output/ subdirs."""
    (tmp_path / "log").mkdir()
    (tmp_path / "output").mkdir()
    return tmp_path


@pytest.fixture
def sample_podcast_config_data() -> dict[str, Any]:
    """Return a minimal valid podcast config dict."""
    return {
        "languages": [
            {
                "code": "en",
                "label": "English",
                "voice_reference": "references/en_voice.wav",
                "voice_transcript": "Hello, this is a sample of my voice.",
            },
            {
                "code": "pt",
                "label": "Portuguese",
                "voice_reference": "references/pt_voice.wav",
                "voice_transcript": "Ola, esta e uma amostra da minha voz.",
            },
        ],
        "tts": {
            "engine": "mlx-audio",
            "quantization": 4,
            "max_segment_chars": 200,
            "model": "mlx-community/Qwen3-TTS-0.6B-4bit",
        },
        "audio": {
            "sample_rate": 24000,
            "channels": 1,
            "bit_depth": 16,
            "loudness_target_lufs": -16,
            "true_peak_dbtp": -1.0,
            "output_format": "mp3",
            "mp3_bitrate": 192,
            "reference_duration_seconds": 15,
        },
        "llm": {
            "provider": "minimax",
            "model": "MiniMax-M2.7",
            "base_url": "https://api.minimax.io/anthropic",
        },
        "podcast": {
            "title": "Test Podcast",
            "description": "A test podcast",
            "author": "Test Author",
        },
        "distribution": {
            "type": "static",
            "output_dir": "output/episodes",
            "rss_file": "output/feed.xml",
        },
        "schedule": {
            "generate_episode": "0 6 * * 1",
        },
        "settings": {
            "intro_audio": "",
            "outro_audio": "",
            "crossfade_ms": 500,
        },
    }


@pytest.fixture
def podcast_config_file(tmp_path: Path, sample_podcast_config_data: dict[str, Any]) -> Path:
    """Write a sample podcast.json to a temp dir and return its path."""
    config_path = tmp_path / "podcast.json"
    config_path.write_text(json.dumps(sample_podcast_config_data), encoding="utf-8")
    return config_path


@pytest.fixture
def podcast_config(podcast_config_file: Path) -> PodcastConfig:
    """Return a PodcastConfig loaded from the test config file."""
    return PodcastConfig(podcast_config_file)


@pytest.fixture
def test_settings(tmp_data_dir: Path, podcast_config_file: Path) -> PodcastSettings:
    """Return PodcastSettings configured for testing."""
    return PodcastSettings(
        PODCAST_DATA_DIR=str(tmp_data_dir),
        PODCAST_WORKSPACE_DIR=str(tmp_data_dir),
        PODCAST_CONFIG_FILE=str(podcast_config_file),
        IAMQ_HTTP_URL="http://127.0.0.1:18790",
        IAMQ_AGENT_ID="podcast_agent",
        LLM_BASE_URL="https://api.minimax.io/anthropic",
        LLM_API_KEY="test-key",
        LLM_MODEL="MiniMax-M2.7",
        TTS_ENGINE="mlx-audio",
    )
