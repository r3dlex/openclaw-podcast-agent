"""Tests for podcast_renderer.transcription.whisper — TranscribeStep."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from podcast_renderer.transcription.whisper import TranscribeStep


class TestTranscribeStep:
    def test_name(self) -> None:
        assert TranscribeStep().name == "transcribe"

    def test_should_run_with_episode_mp3(self, tmp_path: Path) -> None:
        step = TranscribeStep()
        assert step.should_run({"episode_mp3": tmp_path / "ep.mp3"})

    def test_should_run_with_episode_wav(self, tmp_path: Path) -> None:
        step = TranscribeStep()
        assert step.should_run({"episode_wav": tmp_path / "ep.wav"})

    def test_should_run_with_input_audio(self, tmp_path: Path) -> None:
        step = TranscribeStep()
        assert step.should_run({"input_audio": tmp_path / "audio.wav"})

    def test_should_not_run_without_audio(self) -> None:
        step = TranscribeStep()
        assert not step.should_run({})

    def test_execute_with_mlx_whisper(self, tmp_path: Path) -> None:
        """When mlx_whisper is importable, uses it to transcribe."""
        mock_mlx_whisper = MagicMock()
        mock_mlx_whisper.transcribe.return_value = {
            "text": "Hello world",
            "segments": [{"start": 0.0, "end": 2.5, "text": "Hello world"}],
            "language": "en",
        }

        ep = tmp_path / "ep.mp3"
        ep.touch()

        with patch.dict("sys.modules", {"mlx_whisper": mock_mlx_whisper}):
            ctx: dict[str, Any] = {"episode_mp3": ep}
            result = TranscribeStep().execute(ctx)

        transcript = result["transcript"]
        assert transcript["text"] == "Hello world"
        assert transcript["language"] == "en"
        assert len(transcript["segments"]) == 1

    def test_execute_fallback_when_mlx_not_installed(self, tmp_path: Path) -> None:
        """When mlx_whisper is not available, returns empty transcript."""
        import sys

        ep = tmp_path / "ep.wav"
        ep.touch()

        # Ensure mlx_whisper is not importable
        original = sys.modules.pop("mlx_whisper", None)
        try:
            ctx: dict[str, Any] = {"episode_wav": ep, "language": "es"}
            result = TranscribeStep().execute(ctx)
        finally:
            if original is not None:
                sys.modules["mlx_whisper"] = original

        transcript = result["transcript"]
        assert transcript["text"] == ""
        assert transcript["segments"] == []
        assert transcript["language"] == "es"

    def test_execute_uses_episode_wav_when_no_mp3(self, tmp_path: Path) -> None:
        """Uses episode_wav if episode_mp3 is absent."""
        mock_mlx_whisper = MagicMock()
        mock_mlx_whisper.transcribe.return_value = {
            "text": "WAV content",
            "segments": [],
            "language": "en",
        }

        wav = tmp_path / "ep.wav"
        wav.touch()

        with patch.dict("sys.modules", {"mlx_whisper": mock_mlx_whisper}):
            ctx: dict[str, Any] = {"episode_wav": wav}
            result = TranscribeStep().execute(ctx)

        assert result["transcript"]["text"] == "WAV content"

    def test_execute_uses_input_audio_when_no_episode(self, tmp_path: Path) -> None:
        """Uses input_audio key as fallback."""
        mock_mlx_whisper = MagicMock()
        mock_mlx_whisper.transcribe.return_value = {
            "text": "Input audio content",
            "segments": [],
            "language": "en",
        }

        audio = tmp_path / "input.mp3"
        audio.touch()

        with patch.dict("sys.modules", {"mlx_whisper": mock_mlx_whisper}):
            ctx: dict[str, Any] = {"input_audio": audio}
            result = TranscribeStep().execute(ctx)

        assert result["transcript"]["text"] == "Input audio content"

    def test_execute_calls_correct_model(self, tmp_path: Path) -> None:
        mock_mlx_whisper = MagicMock()
        mock_mlx_whisper.transcribe.return_value = {
            "text": "text",
            "segments": [],
            "language": "en",
        }

        ep = tmp_path / "ep.mp3"
        ep.touch()

        with patch.dict("sys.modules", {"mlx_whisper": mock_mlx_whisper}):
            ctx: dict[str, Any] = {"episode_mp3": ep}
            TranscribeStep().execute(ctx)

        call_kwargs = mock_mlx_whisper.transcribe.call_args
        assert "mlx-community/whisper-large-v3-turbo" in str(call_kwargs)

    def test_execute_fallback_language_from_context(self, tmp_path: Path) -> None:
        """Default language in fallback comes from context['language']."""
        import sys
        ep = tmp_path / "ep.wav"
        ep.touch()

        original = sys.modules.pop("mlx_whisper", None)
        try:
            ctx: dict[str, Any] = {"episode_wav": ep, "language": "fr"}
            result = TranscribeStep().execute(ctx)
        finally:
            if original is not None:
                sys.modules["mlx_whisper"] = original

        assert result["transcript"]["language"] == "fr"
