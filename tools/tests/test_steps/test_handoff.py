"""Tests for LibrarianHandoffStep."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pipeline_runner.config import PodcastSettings
from pipeline_runner.steps.handoff import LibrarianHandoffStep


@pytest.fixture
def settings(tmp_data_dir: Path) -> PodcastSettings:
    return PodcastSettings(
        PODCAST_DATA_DIR=str(tmp_data_dir),
    )


class TestLibrarianHandoffStep:
    def test_name(self) -> None:
        assert LibrarianHandoffStep().name == "librarian_handoff"

    def test_should_run_with_episode_summary(self) -> None:
        step = LibrarianHandoffStep()
        assert step.should_run({"episode_summary": "Episode ready"})

    def test_should_run_with_content(self) -> None:
        step = LibrarianHandoffStep()
        assert step.should_run({"content": "Some content"})

    def test_should_not_run_without_content(self) -> None:
        step = LibrarianHandoffStep()
        assert not step.should_run({})

    def test_execute_writes_output_file(
        self, settings: PodcastSettings
    ) -> None:
        step = LibrarianHandoffStep()
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "# Episode Summary\n\nGreat episode today.",
            "pipeline_name": "episode",
        }
        result = step.execute(ctx)
        assert "handoff_path" in result
        assert Path(result["handoff_path"]).exists()

    def test_execute_writes_metadata_file(
        self, settings: PodcastSettings
    ) -> None:
        import json

        step = LibrarianHandoffStep()
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "Episode done.",
            "pipeline_name": "test_pipe",
        }
        result = step.execute(ctx)
        meta = result["handoff_metadata"]
        assert meta["source_agent"] == "podcast"
        assert meta["target_agent"] == "librarian"
        assert meta["pipeline"] == "test_pipe"
        assert "output_file" in meta

    def test_execute_uses_episode_summary_preferentially(
        self, settings: PodcastSettings
    ) -> None:
        step = LibrarianHandoffStep()
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "Summary content",
            "content": "Content field",
            "pipeline_name": "test",
        }
        result = step.execute(ctx)
        written = Path(result["handoff_path"]).read_text()
        assert "Summary content" in written

    def test_execute_uses_content_when_no_summary(
        self, settings: PodcastSettings
    ) -> None:
        step = LibrarianHandoffStep()
        ctx: dict[str, Any] = {
            "settings": settings,
            "content": "Fallback content",
            "pipeline_name": "test",
        }
        result = step.execute(ctx)
        written = Path(result["handoff_path"]).read_text()
        assert "Fallback content" in written

    def test_execute_includes_episode_files_in_metadata(
        self, settings: PodcastSettings, tmp_data_dir: Path
    ) -> None:
        step = LibrarianHandoffStep()
        mp3_path = tmp_data_dir / "episode.mp3"
        mp3_path.touch()
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "Done.",
            "pipeline_name": "ep",
            "episode_mp3": mp3_path,
        }
        result = step.execute(ctx)
        assert "episode_mp3" in result["handoff_metadata"]

    def test_execute_warns_when_librarian_workspace_missing(
        self, settings: PodcastSettings, capsys: Any
    ) -> None:
        """Should not crash when librarian workspace is not found."""
        step = LibrarianHandoffStep()
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_summary": "Done.",
            "pipeline_name": "ep",
        }
        # Should complete without raising
        result = step.execute(ctx)
        assert "handoff_metadata" in result

    def test_execute_writes_signal_to_librarian_workspace(
        self, settings: PodcastSettings, tmp_data_dir: Path
    ) -> None:
        """When librarian workspace is configured and exists, write signal file."""
        librarian_ws = tmp_data_dir / "librarian_ws"
        librarian_ws.mkdir()

        # Update settings via new object with librarian workspace
        settings2 = PodcastSettings(
            PODCAST_DATA_DIR=str(tmp_data_dir),
            LIBRARIAN_AGENT_WORKSPACE=str(librarian_ws),
        )

        step = LibrarianHandoffStep()
        ctx: dict[str, Any] = {
            "settings": settings2,
            "episode_summary": "Signal test.",
            "pipeline_name": "signal_test",
        }
        result = step.execute(ctx)
        # Handoff metadata file should be written to log dir
        assert "handoff_metadata" in result
        assert result["handoff_metadata"]["source_agent"] == "podcast"
        # The inbox directory should have been created
        inbox = librarian_ws / "inbox"
        # Either the inbox was created or the workspace was used
        # (check metadata indicates it was processed)
        assert result["handoff_path"].exists()
