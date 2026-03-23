"""Shared test fixtures for podcast_renderer tests."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


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
        ],
        "tts": {
            "engine": "mlx-audio",
            "quantization": 4,
            "max_segment_chars": 200,
        },
        "audio": {
            "sample_rate": 24000,
            "loudness_target_lufs": -16,
            "true_peak_dbtp": -1.0,
            "mp3_bitrate": 192,
            "reference_duration_seconds": 15,
        },
        "llm": {
            "provider": "minimax",
            "model": "MiniMax-M2.7",
            "base_url": "https://api.minimax.io/anthropic",
        },
        "podcast": {"title": "Test Podcast"},
        "distribution": {"type": "static", "rss_file": "output/feed.xml"},
        "settings": {"crossfade_ms": 500},
    }


@pytest.fixture
def podcast_config_file(
    tmp_path: Path, sample_podcast_config_data: dict[str, Any]
) -> Path:
    config_path = tmp_path / "podcast.json"
    config_path.write_text(json.dumps(sample_podcast_config_data), encoding="utf-8")
    return config_path


@pytest.fixture
def test_settings(tmp_path: Path, podcast_config_file: Path) -> SimpleNamespace:
    """Mock settings object that matches PodcastSettings interface."""
    return SimpleNamespace(
        podcast_config_file=podcast_config_file,
        podcast_data_dir=tmp_path,
        llm_base_url="https://api.minimax.io/anthropic",
        llm_api_key="test-key",
        llm_model="MiniMax-M2.7",
        tts_engine="mlx-audio",
        tts_quantization=4,
        request_timeout=30,
        log_dir=tmp_path / "log",
        output_dir=tmp_path / "output",
    )
