"""Tests for pipeline_runner.pipelines.episode — run_episode_pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pipeline_runner.config import PodcastSettings
from pipeline_runner.pipelines.episode import run_episode_pipeline


@pytest.fixture
def episode_settings(test_settings: PodcastSettings) -> PodcastSettings:
    return test_settings


class TestRunEpisodePipeline:
    def test_script_failure_returns_early(
        self, episode_settings: PodcastSettings
    ) -> None:
        """When script generation fails, pipeline returns immediately."""
        with patch("pipeline_runner.pipelines.episode.build_script_pipeline") as mock_build:
            mock_pipeline = MagicMock()
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.summary.return_value = "Pipeline: script_generation\nStatus: FAILED"
            mock_result.context = {}
            mock_pipeline.run.return_value = mock_result
            mock_build.return_value = mock_pipeline

            result = run_episode_pipeline(episode_settings, topics="AI")
        assert "FAILED" in result

    def test_missing_language_is_skipped(
        self, episode_settings: PodcastSettings
    ) -> None:
        """Languages not in config are logged and skipped."""
        with patch("pipeline_runner.pipelines.episode.build_script_pipeline") as mock_script:
            mock_script_pipeline = MagicMock()
            script_result = MagicMock()
            script_result.success = True
            script_result.summary.return_value = "Pipeline: script_generation\nStatus: SUCCESS"
            script_result.context = {
                "script": {
                    "title": "Test",
                    "segments": [{"speaker": "host", "text": "Hello.", "notes": ""}],
                }
            }
            mock_script_pipeline.run.return_value = script_result
            mock_script.return_value = mock_script_pipeline

            # Request a language not in config
            result = run_episode_pipeline(episode_settings, topics="AI", langs="zz")
        assert "script_generation" in result

    @patch("pipeline_runner.pipelines.episode.build_voice_pipeline")
    @patch("pipeline_runner.pipelines.episode.build_script_pipeline")
    def test_voice_failure_skips_remaining_steps(
        self,
        mock_script_build: MagicMock,
        mock_voice_build: MagicMock,
        episode_settings: PodcastSettings,
    ) -> None:
        """When voice pipeline fails, cleanup/assembly/distribute are skipped."""
        # Script succeeds
        mock_script_pipeline = MagicMock()
        script_result = MagicMock()
        script_result.success = True
        script_result.summary.return_value = "Pipeline: script_generation\nStatus: SUCCESS"
        script_result.context = {
            "script": {"title": "T", "segments": [{"speaker": "host", "text": "Hi.", "notes": ""}]}
        }
        mock_script_pipeline.run.return_value = script_result
        mock_script_build.return_value = mock_script_pipeline

        # Voice fails
        mock_voice_pipeline = MagicMock()
        voice_result = MagicMock()
        voice_result.success = False
        voice_result.summary.return_value = "Pipeline: voice_generation\nStatus: FAILED"
        voice_result.context = {}
        mock_voice_pipeline.run.return_value = voice_result
        mock_voice_build.return_value = mock_voice_pipeline

        result = run_episode_pipeline(episode_settings, topics="AI", langs="en")
        assert "voice_generation" in result

    @patch("pipeline_runner.pipelines.episode.build_distribute_pipeline")
    @patch("pipeline_runner.pipelines.episode.build_assembly_pipeline")
    @patch("pipeline_runner.pipelines.episode.build_cleanup_pipeline")
    @patch("pipeline_runner.pipelines.episode.build_voice_pipeline")
    @patch("pipeline_runner.pipelines.episode.build_script_pipeline")
    def test_full_pipeline_success(
        self,
        mock_script_build: MagicMock,
        mock_voice_build: MagicMock,
        mock_cleanup_build: MagicMock,
        mock_assembly_build: MagicMock,
        mock_dist_build: MagicMock,
        episode_settings: PodcastSettings,
    ) -> None:
        """When all sub-pipelines succeed, all summaries are included."""
        def _make_success_pipeline(name: str, extra_ctx: dict | None = None) -> MagicMock:
            pipeline = MagicMock()
            result = MagicMock()
            result.success = True
            result.summary.return_value = f"Pipeline: {name}\nStatus: SUCCESS"
            result.context = extra_ctx or {}
            pipeline.run.return_value = result
            return pipeline

        mock_script_build.return_value = _make_success_pipeline(
            "script_generation",
            {
                "script": {
                    "title": "T",
                    "segments": [{"speaker": "host", "text": "Hello.", "notes": ""}],
                }
            },
        )
        mock_voice_build.return_value = _make_success_pipeline("voice_generation")
        mock_cleanup_build.return_value = _make_success_pipeline("audio_cleanup")
        mock_assembly_build.return_value = _make_success_pipeline(
            "episode_assembly",
            {"episode_mp3": Path("/tmp/ep.mp3")},
        )
        mock_dist_build.return_value = _make_success_pipeline("distribution")

        result = run_episode_pipeline(episode_settings, topics="AI", langs="en")
        assert "script_generation" in result
        assert "voice_generation" in result

    @patch("pipeline_runner.pipelines.episode.build_distribute_pipeline")
    @patch("pipeline_runner.pipelines.episode.build_assembly_pipeline")
    @patch("pipeline_runner.pipelines.episode.build_cleanup_pipeline")
    @patch("pipeline_runner.pipelines.episode.build_voice_pipeline")
    @patch("pipeline_runner.pipelines.episode.build_script_pipeline")
    def test_skip_cleanup_flag(
        self,
        mock_script_build: MagicMock,
        mock_voice_build: MagicMock,
        mock_cleanup_build: MagicMock,
        mock_assembly_build: MagicMock,
        mock_dist_build: MagicMock,
        episode_settings: PodcastSettings,
    ) -> None:
        """When skip_cleanup=True, cleanup pipeline is not built or run."""
        def _success_pipeline(name: str, ctx: dict | None = None) -> MagicMock:
            p = MagicMock()
            r = MagicMock()
            r.success = True
            r.summary.return_value = f"Pipeline: {name}\nStatus: SUCCESS"
            r.context = ctx or {}
            p.run.return_value = r
            return p

        mock_script_build.return_value = _success_pipeline(
            "script_generation",
            {"script": {"title": "T", "segments": [{"speaker": "host", "text": "Hi.", "notes": ""}]}}
        )
        mock_voice_build.return_value = _success_pipeline("voice_generation")
        mock_assembly_build.return_value = _success_pipeline("episode_assembly")
        mock_dist_build.return_value = _success_pipeline("distribution")

        run_episode_pipeline(episode_settings, topics="AI", langs="en", skip_cleanup=True)
        # Cleanup was NOT called
        mock_cleanup_build.assert_not_called()

    def test_with_script_file(
        self, episode_settings: PodcastSettings, tmp_path: Path
    ) -> None:
        """Episode pipeline can accept a script_file argument."""
        script_content = json.dumps({
            "title": "Manual",
            "description": "",
            "segments": [{"speaker": "host", "text": "Hello.", "notes": ""}],
            "language": "en",
        })
        script_file = tmp_path / "script.json"
        script_file.write_text(script_content)

        with patch("pipeline_runner.pipelines.episode.build_voice_pipeline") as mock_vp:
            voice_result = MagicMock()
            voice_result.success = False
            voice_result.summary.return_value = "Pipeline: voice_generation\nStatus: FAILED"
            voice_result.context = {}
            mock_vp.return_value.run.return_value = voice_result

            result = run_episode_pipeline(
                episode_settings,
                script_file=str(script_file),
                langs="en",
            )
        assert "script_generation" in result
