"""Tests for podcast_renderer.config.PodcastConfig."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from podcast_renderer.config import PodcastConfig


class TestPodcastConfig:
    """Tests for PodcastConfig JSON loading and property access."""

    def test_load_languages(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        langs = cfg.languages
        assert isinstance(langs, list)
        assert langs[0]["code"] == "en"

    def test_language_codes(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.language_codes == ["en"]

    def test_language_config_found(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        en = cfg.language_config("en")
        assert en is not None
        assert en["label"] == "English"

    def test_language_config_not_found(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.language_config("zz") is None

    def test_tts_property(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.tts["engine"] == "mlx-audio"

    def test_audio_property(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.audio["sample_rate"] == 24000

    def test_llm_property(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.llm["provider"] == "minimax"

    def test_podcast_metadata(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.podcast_metadata["title"] == "Test Podcast"

    def test_distribution(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.distribution["type"] == "static"

    def test_schedule_empty(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        # schedule not in sample_podcast_config_data in renderer conftest
        assert isinstance(cfg.schedule, dict)

    def test_settings_property(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.settings["crossfade_ms"] == 500

    def test_max_segment_chars(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.max_segment_chars == 200

    def test_loudness_target_lufs(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.loudness_target_lufs == -16.0

    def test_true_peak_dbtp(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.true_peak_dbtp == -1.0

    def test_sample_rate(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.sample_rate == 24000

    def test_mp3_bitrate(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.mp3_bitrate == 192

    def test_reference_duration_seconds(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.reference_duration_seconds == 15

    def test_crossfade_ms(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert cfg.crossfade_ms == 500

    def test_intro_audio_empty(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        # sample config has no intro_audio key in settings
        assert isinstance(cfg.intro_audio, str)

    def test_outro_audio_empty(self, podcast_config_file: Path) -> None:
        cfg = PodcastConfig(podcast_config_file)
        assert isinstance(cfg.outro_audio, str)

    def test_reload(self, tmp_path: Path, sample_podcast_config_data: dict[str, Any]) -> None:
        cfg_path = tmp_path / "podcast.json"
        cfg_path.write_text(json.dumps(sample_podcast_config_data))
        cfg = PodcastConfig(cfg_path)
        assert cfg.tts["engine"] == "mlx-audio"

        sample_podcast_config_data["tts"]["engine"] = "f5-tts-mlx"
        cfg_path.write_text(json.dumps(sample_podcast_config_data))
        cfg.reload()
        assert cfg.tts["engine"] == "f5-tts-mlx"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            PodcastConfig(tmp_path / "missing.json")

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json")
        with pytest.raises(json.JSONDecodeError):
            PodcastConfig(bad)

    def test_defaults_when_keys_missing(self, tmp_path: Path) -> None:
        """Properties return sensible defaults when keys are absent."""
        minimal: dict[str, Any] = {
            "languages": [],
            "tts": {},
            "audio": {},
            "llm": {},
        }
        cfg_path = tmp_path / "minimal.json"
        cfg_path.write_text(json.dumps(minimal))
        cfg = PodcastConfig(cfg_path)

        assert cfg.max_segment_chars == 200
        assert cfg.loudness_target_lufs == -16.0
        assert cfg.true_peak_dbtp == -1.0
        assert cfg.sample_rate == 24000
        assert cfg.mp3_bitrate == 192
        assert cfg.reference_duration_seconds == 15
        assert cfg.crossfade_ms == 500
        assert cfg.intro_audio == ""
        assert cfg.outro_audio == ""
