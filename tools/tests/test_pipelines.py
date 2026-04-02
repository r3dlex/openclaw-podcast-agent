"""Tests for pipeline_runner.pipelines — build functions and run_* helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pipeline_runner.config import PodcastSettings
from pipeline_runner.pipelines.assembly import build_assembly_pipeline
from pipeline_runner.pipelines.cleanup import build_cleanup_pipeline
from pipeline_runner.pipelines.distribute import build_distribute_pipeline, run_transcribe_pipeline
from pipeline_runner.pipelines.script import build_script_pipeline, run_script_pipeline
from pipeline_runner.pipelines.voice import build_voice_pipeline, run_voice_preview
from pipeline_runner.runner import Pipeline


# ---------------------------------------------------------------------------
# Pipeline builders (smoke-tests that the pipelines can be constructed)
# ---------------------------------------------------------------------------

class TestBuildFunctions:
    def test_build_script_pipeline(self) -> None:
        p = build_script_pipeline()
        assert isinstance(p, Pipeline)
        assert p.name == "script_generation"

    def test_build_voice_pipeline(self) -> None:
        p = build_voice_pipeline()
        assert isinstance(p, Pipeline)
        assert p.name == "voice_generation"

    def test_build_cleanup_pipeline(self) -> None:
        p = build_cleanup_pipeline()
        assert isinstance(p, Pipeline)
        assert p.name == "audio_cleanup"

    def test_build_assembly_pipeline(self) -> None:
        p = build_assembly_pipeline()
        assert isinstance(p, Pipeline)
        assert p.name == "episode_assembly"

    def test_build_distribute_pipeline(self) -> None:
        p = build_distribute_pipeline()
        assert isinstance(p, Pipeline)
        assert p.name == "distribution"


# ---------------------------------------------------------------------------
# run_script_pipeline
# ---------------------------------------------------------------------------

class TestRunScriptPipeline:
    @patch("podcast_renderer.llm.script.anthropic")
    def test_run_with_topics(
        self, mock_anthropic: MagicMock, test_settings: PodcastSettings
    ) -> None:
        script_json = json.dumps({
            "title": "AI News",
            "description": "Weekly update",
            "segments": [
                {"speaker": "host", "text": "Hello world.", "notes": ""},
            ],
            "language": "en",
        })
        mock_text = MagicMock(type="text", text=script_json)
        mock_msg = MagicMock(content=[mock_text])
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_anthropic.Anthropic.return_value = mock_client

        summary = run_script_pipeline(test_settings, topics="AI news", lang="en")
        assert "script_generation" in summary

    def test_run_with_manual_script_file(
        self, test_settings: PodcastSettings, tmp_path: Path
    ) -> None:
        script_content = json.dumps({
            "title": "Manual Episode",
            "description": "",
            "segments": [{"speaker": "host", "text": "Manual text.", "notes": ""}],
            "language": "en",
        })
        script_file = tmp_path / "script.json"
        script_file.write_text(script_content)

        summary = run_script_pipeline(test_settings, script_file=str(script_file))
        assert "script_generation" in summary

    @patch("podcast_renderer.llm.script.anthropic")
    def test_script_written_to_output_on_success(
        self, mock_anthropic: MagicMock, test_settings: PodcastSettings
    ) -> None:
        script_json = json.dumps({
            "title": "Test",
            "description": "",
            "segments": [{"speaker": "host", "text": "Hello.", "notes": ""}],
            "language": "en",
        })
        mock_text = MagicMock(type="text", text=script_json)
        mock_msg = MagicMock(content=[mock_text])
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_anthropic.Anthropic.return_value = mock_client

        run_script_pipeline(test_settings, topics="test")
        script_path = test_settings.output_dir / "latest_script.json"
        assert script_path.exists()

    def test_run_with_neither_topics_nor_script(
        self, test_settings: PodcastSettings
    ) -> None:
        """With no topics/script, all steps are skipped (should_run returns False)."""
        summary = run_script_pipeline(test_settings)
        assert "script_generation" in summary


# ---------------------------------------------------------------------------
# run_voice_preview
# ---------------------------------------------------------------------------

class TestRunVoicePreview:
    def test_missing_language_returns_message(self, test_settings: PodcastSettings) -> None:
        result = run_voice_preview(test_settings, text="Hello", lang="zz")
        assert "not configured" in result

    @patch("pipeline_runner.pipelines.voice.PrepareReferenceStep.execute")
    def test_existing_language_runs_pipeline(
        self, mock_exec: MagicMock, test_settings: PodcastSettings
    ) -> None:
        mock_exec.side_effect = FileNotFoundError("reference not found")
        result = run_voice_preview(test_settings, text="Hello world", lang="en")
        # Pipeline runs but fails at PrepareReferenceStep — summary still returned
        assert "voice_generation" in result


# ---------------------------------------------------------------------------
# run_transcribe_pipeline
# ---------------------------------------------------------------------------

class TestRunTranscribePipeline:
    def test_transcribe_no_mlx_whisper_creates_summary(
        self, test_settings: PodcastSettings, tmp_path: Path
    ) -> None:
        """When mlx_whisper unavailable, TranscribeStep returns empty transcript."""
        import sys
        audio = tmp_path / "episode.mp3"
        audio.touch()

        original = sys.modules.pop("mlx_whisper", None)
        try:
            result = run_transcribe_pipeline(test_settings, input_path=str(audio))
        finally:
            if original is not None:
                sys.modules["mlx_whisper"] = original

        assert "transcribe" in result

    def test_transcribe_writes_text_file_when_transcript_available(
        self, test_settings: PodcastSettings, tmp_path: Path
    ) -> None:
        """Transcript text is written to .txt file alongside audio."""
        import sys
        audio = tmp_path / "episode.mp3"
        audio.touch()

        mock_mlx_whisper = MagicMock()
        mock_mlx_whisper.transcribe.return_value = {
            "text": "Hello listeners.",
            "segments": [],
            "language": "en",
        }

        with patch.dict("sys.modules", {"mlx_whisper": mock_mlx_whisper}):
            result = run_transcribe_pipeline(test_settings, input_path=str(audio))

        txt_file = tmp_path / "episode.txt"
        assert txt_file.exists()
        assert txt_file.read_text() == "Hello listeners."
