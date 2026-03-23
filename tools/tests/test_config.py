"""Tests for configuration management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pipeline_runner.config import PodcastConfig, PodcastSettings


class TestPodcastSettings:
    """Test PodcastSettings environment variable loading."""

    def test_defaults(self) -> None:
        settings = PodcastSettings(
            PODCAST_DATA_DIR=".",
            IAMQ_HTTP_URL="http://127.0.0.1:18790",
        )
        assert settings.iamq_http_url == "http://127.0.0.1:18790"
        assert settings.iamq_agent_id == "podcast_agent"
        assert settings.tts_engine == "mlx-audio"
        assert settings.tts_quantization == 4
        assert settings.ollama_model == "llama3.2"

    def test_custom_values(self) -> None:
        settings = PodcastSettings(
            PODCAST_DATA_DIR="/tmp/test",
            IAMQ_HTTP_URL="http://custom:9999",
            TTS_ENGINE="f5-tts-mlx",
            OLLAMA_MODEL="qwen3:8b",
        )
        assert settings.iamq_http_url == "http://custom:9999"
        assert settings.tts_engine == "f5-tts-mlx"
        assert settings.ollama_model == "qwen3:8b"

    def test_log_dir_creation(self, tmp_path: Path) -> None:
        settings = PodcastSettings(PODCAST_DATA_DIR=str(tmp_path))
        log_dir = settings.log_dir
        assert log_dir.exists()
        assert log_dir == tmp_path / "log"

    def test_output_dir_creation(self, tmp_path: Path) -> None:
        settings = PodcastSettings(PODCAST_DATA_DIR=str(tmp_path))
        output_dir = settings.output_dir
        assert output_dir.exists()
        assert output_dir == tmp_path / "output"


class TestPodcastConfig:
    """Test PodcastConfig JSON loading."""

    def test_load_languages(self, podcast_config: PodcastConfig) -> None:
        langs = podcast_config.languages
        assert len(langs) == 2
        assert langs[0]["code"] == "en"
        assert langs[1]["code"] == "pt"

    def test_language_codes(self, podcast_config: PodcastConfig) -> None:
        codes = podcast_config.language_codes
        assert codes == ["en", "pt"]

    def test_language_config_lookup(self, podcast_config: PodcastConfig) -> None:
        en = podcast_config.language_config("en")
        assert en is not None
        assert en["label"] == "English"
        assert "voice_reference" in en

    def test_language_config_missing(self, podcast_config: PodcastConfig) -> None:
        result = podcast_config.language_config("xx")
        assert result is None

    def test_tts_config(self, podcast_config: PodcastConfig) -> None:
        tts = podcast_config.tts
        assert tts["engine"] == "mlx-audio"
        assert tts["quantization"] == 4

    def test_audio_config(self, podcast_config: PodcastConfig) -> None:
        audio = podcast_config.audio
        assert audio["sample_rate"] == 24000
        assert audio["loudness_target_lufs"] == -16

    def test_max_segment_chars(self, podcast_config: PodcastConfig) -> None:
        assert podcast_config.max_segment_chars == 200

    def test_loudness_target(self, podcast_config: PodcastConfig) -> None:
        assert podcast_config.loudness_target_lufs == -16.0
        assert podcast_config.true_peak_dbtp == -1.0

    def test_sample_rate(self, podcast_config: PodcastConfig) -> None:
        assert podcast_config.sample_rate == 24000

    def test_mp3_bitrate(self, podcast_config: PodcastConfig) -> None:
        assert podcast_config.mp3_bitrate == 192

    def test_reference_duration(self, podcast_config: PodcastConfig) -> None:
        assert podcast_config.reference_duration_seconds == 15

    def test_crossfade(self, podcast_config: PodcastConfig) -> None:
        assert podcast_config.crossfade_ms == 500

    def test_llm_config(self, podcast_config: PodcastConfig) -> None:
        llm = podcast_config.llm
        assert llm["provider"] == "ollama"
        assert llm["model"] == "llama3.2"

    def test_distribution_config(self, podcast_config: PodcastConfig) -> None:
        dist = podcast_config.distribution
        assert dist["type"] == "static"

    def test_schedule_config(self, podcast_config: PodcastConfig) -> None:
        sched = podcast_config.schedule
        assert "generate_episode" in sched

    def test_podcast_metadata(self, podcast_config: PodcastConfig) -> None:
        meta = podcast_config.podcast_metadata
        assert meta["title"] == "Test Podcast"

    def test_reload(self, podcast_config_file: Path, podcast_config: PodcastConfig) -> None:
        # Modify the file
        data = json.loads(podcast_config_file.read_text())
        data["tts"]["engine"] = "f5-tts-mlx"
        podcast_config_file.write_text(json.dumps(data))

        # Reload and verify
        podcast_config.reload()
        assert podcast_config.tts["engine"] == "f5-tts-mlx"

    def test_invalid_config_file_raises(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        with pytest.raises(json.JSONDecodeError):
            PodcastConfig(bad_file)

    def test_missing_config_file_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.json"
        with pytest.raises(FileNotFoundError):
            PodcastConfig(missing)
