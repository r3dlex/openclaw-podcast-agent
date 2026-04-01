"""Tests for podcast_renderer.audio.ffmpeg helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from podcast_renderer.audio.ffmpeg import (
    convert_reference_audio,
    get_audio_duration,
    run_ffmpeg,
    run_ffprobe,
)


class TestRunFfmpeg:
    """Tests for run_ffmpeg."""

    @patch("podcast_renderer.audio.ffmpeg.subprocess.run")
    def test_prepends_ffmpeg_dash_y(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        run_ffmpeg(["-i", "input.wav", "output.wav"])
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ffmpeg"
        assert call_args[1] == "-y"

    @patch("podcast_renderer.audio.ffmpeg.subprocess.run")
    def test_returns_completed_process(self, mock_run: MagicMock) -> None:
        proc = MagicMock(returncode=0, stdout="out", stderr="err")
        mock_run.return_value = proc
        result = run_ffmpeg(["-version"])
        assert result is proc

    @patch("podcast_renderer.audio.ffmpeg.subprocess.run")
    def test_check_true_raises_on_nonzero(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="fail")
        with pytest.raises(subprocess.CalledProcessError):
            run_ffmpeg(["-i", "bad.wav", "out.wav"], check=True)

    @patch("podcast_renderer.audio.ffmpeg.subprocess.run")
    def test_file_not_found_raises(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")
        with pytest.raises(FileNotFoundError):
            run_ffmpeg(["-version"])

    @patch("podcast_renderer.audio.ffmpeg.subprocess.run")
    def test_timeout_raises(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 300)
        with pytest.raises(subprocess.TimeoutExpired):
            run_ffmpeg(["-i", "long.wav", "out.wav"], timeout=300)

    @patch("podcast_renderer.audio.ffmpeg.subprocess.run")
    def test_custom_timeout_passed(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        run_ffmpeg(["-version"], timeout=60)
        kwargs = mock_run.call_args[1]
        assert kwargs["timeout"] == 60


class TestRunFfprobe:
    """Tests for run_ffprobe."""

    @patch("podcast_renderer.audio.ffmpeg.subprocess.run")
    def test_prepends_ffprobe(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="42.5\n", stderr="")
        run_ffprobe(["-show_entries", "format=duration", "file.wav"])
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ffprobe"

    @patch("podcast_renderer.audio.ffmpeg.subprocess.run")
    def test_returns_result(self, mock_run: MagicMock) -> None:
        proc = MagicMock(returncode=0, stdout="10.0\n", stderr="")
        mock_run.return_value = proc
        result = run_ffprobe(["-v", "quiet", "file.wav"])
        assert result is proc


class TestGetAudioDuration:
    """Tests for get_audio_duration."""

    @patch("podcast_renderer.audio.ffmpeg.run_ffprobe")
    def test_parses_float_from_stdout(self, mock_ffprobe: MagicMock) -> None:
        mock_ffprobe.return_value = MagicMock(stdout="123.456\n")
        duration = get_audio_duration(Path("episode.mp3"))
        assert duration == pytest.approx(123.456)

    @patch("podcast_renderer.audio.ffmpeg.run_ffprobe")
    def test_passes_path_as_string(self, mock_ffprobe: MagicMock) -> None:
        mock_ffprobe.return_value = MagicMock(stdout="60.0\n")
        get_audio_duration(Path("/tmp/test.wav"))
        args = mock_ffprobe.call_args[0][0]
        assert "/tmp/test.wav" in args


class TestConvertReferenceAudio:
    """Tests for convert_reference_audio."""

    @patch("podcast_renderer.audio.ffmpeg.run_ffmpeg")
    def test_returns_output_path(self, mock_ffmpeg: MagicMock) -> None:
        mock_ffmpeg.return_value = MagicMock(returncode=0)
        result = convert_reference_audio(Path("in.mp3"), Path("out.wav"))
        assert result == Path("out.wav")

    @patch("podcast_renderer.audio.ffmpeg.run_ffmpeg")
    def test_uses_sample_rate_param(self, mock_ffmpeg: MagicMock) -> None:
        mock_ffmpeg.return_value = MagicMock(returncode=0)
        convert_reference_audio(
            Path("in.mp3"), Path("out.wav"), sample_rate=16000, max_duration=10
        )
        args = mock_ffmpeg.call_args[0][0]
        assert "16000" in args
        assert "10" in args

    @patch("podcast_renderer.audio.ffmpeg.run_ffmpeg")
    def test_includes_mono_and_s16_flags(self, mock_ffmpeg: MagicMock) -> None:
        mock_ffmpeg.return_value = MagicMock(returncode=0)
        convert_reference_audio(Path("in.mp3"), Path("out.wav"))
        args = mock_ffmpeg.call_args[0][0]
        assert "-ac" in args
        assert "1" in args
        assert "s16" in args
