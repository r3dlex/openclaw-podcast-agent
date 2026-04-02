"""Tests for pipeline_runner.scheduler."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from pipeline_runner.config import PodcastSettings
from pipeline_runner.scheduler import (
    _already_ran_today,
    _load_state,
    _mark_ran,
    _save_state,
    register_schedule,
)


@pytest.fixture
def settings(tmp_data_dir: Path) -> PodcastSettings:
    return PodcastSettings(PODCAST_DATA_DIR=str(tmp_data_dir))


class TestLoadAndSaveState:
    def test_load_state_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        import pipeline_runner.scheduler as sched
        original = sched._state_file
        sched._state_file = tmp_path / "nonexistent_state.json"
        try:
            state = _load_state()
            assert state == {}
        finally:
            sched._state_file = original

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        import pipeline_runner.scheduler as sched
        original = sched._state_file
        sched._state_file = tmp_path / "state.json"
        try:
            state = {"weekly_episode": "2025-01-13T06:00:00+00:00"}
            _save_state(state)
            loaded = _load_state()
            assert loaded == state
        finally:
            sched._state_file = original

    def test_save_state_creates_parent_dir(self, tmp_path: Path) -> None:
        import pipeline_runner.scheduler as sched
        original = sched._state_file
        sched._state_file = tmp_path / "nested" / "dir" / "state.json"
        try:
            _save_state({"task": "2025-01-01T00:00:00"})
            assert sched._state_file.exists()
        finally:
            sched._state_file = original

    def test_load_state_returns_empty_on_corrupt_file(self, tmp_path: Path) -> None:
        import pipeline_runner.scheduler as sched
        original = sched._state_file
        state_file = tmp_path / "corrupt_state.json"
        state_file.write_text("not valid json {{")
        sched._state_file = state_file
        try:
            state = _load_state()
            assert state == {}
        finally:
            sched._state_file = original


class TestAlreadyRanToday:
    def test_returns_true_when_ran_today(self) -> None:
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        state = {"my_task": f"{today}T10:00:00+00:00"}
        assert _already_ran_today("my_task", state) is True

    def test_returns_false_when_ran_yesterday(self) -> None:
        state = {"my_task": "2020-01-01T10:00:00+00:00"}
        assert _already_ran_today("my_task", state) is False

    def test_returns_false_when_task_not_in_state(self) -> None:
        assert _already_ran_today("unknown_task", {}) is False


class TestMarkRan:
    def test_mark_ran_stores_iso_timestamp(self, tmp_path: Path) -> None:
        import pipeline_runner.scheduler as sched
        original = sched._state_file
        sched._state_file = tmp_path / "state.json"
        try:
            state: dict[str, str] = {}
            _mark_ran("my_task", state)
            assert "my_task" in state
            # Should be parseable ISO timestamp
            dt = datetime.fromisoformat(state["my_task"])
            assert dt.tzinfo is not None
        finally:
            sched._state_file = original


class TestRegisterSchedule:
    def test_registers_weekly_task(self, settings: PodcastSettings) -> None:
        import schedule as sched_lib
        # Clear any existing jobs
        sched_lib.clear()
        tasks = register_schedule(settings)
        assert len(tasks) == 1
        assert tasks[0].name == "Weekly episode"
        sched_lib.clear()

    def test_registered_task_has_correct_pipeline(
        self, settings: PodcastSettings
    ) -> None:
        import schedule as sched_lib
        sched_lib.clear()
        tasks = register_schedule(settings)
        assert tasks[0].pipeline_fn == "generate_episode"
        sched_lib.clear()


class TestRunEpisode:
    def test_run_episode_calls_pipeline(
        self, settings: PodcastSettings
    ) -> None:
        from pipeline_runner.scheduler import _run_episode
        # run_episode_pipeline is imported locally inside _run_episode
        with patch("pipeline_runner.pipelines.episode.run_episode_pipeline") as mock_pipeline:
            mock_pipeline.return_value = "Pipeline: SUCCESS"
            _run_episode(settings)
            mock_pipeline.assert_called_once_with(settings)

    def test_run_episode_handles_exception(
        self, settings: PodcastSettings
    ) -> None:
        from pipeline_runner.scheduler import _run_episode
        with patch("pipeline_runner.pipelines.episode.run_episode_pipeline") as mock_pipeline:
            mock_pipeline.side_effect = RuntimeError("Pipeline failed")
            # Should not propagate the exception
            _run_episode(settings)


class TestGuardedRun:
    def test_guarded_run_calls_fn_when_not_ran(
        self, tmp_path: Path, settings: PodcastSettings
    ) -> None:
        import pipeline_runner.scheduler as sched
        original_state = sched._run_state.copy()
        original_file = sched._state_file
        sched._state_file = tmp_path / "state.json"
        sched._run_state = {}

        try:
            mock_fn = MagicMock()
            from pipeline_runner.scheduler import _guarded_run
            _guarded_run("new_task", mock_fn, settings)
            mock_fn.assert_called_once_with(settings)
        finally:
            sched._run_state = original_state
            sched._state_file = original_file

    def test_guarded_run_skips_when_already_ran(
        self, tmp_path: Path, settings: PodcastSettings
    ) -> None:
        import pipeline_runner.scheduler as sched
        original_state = sched._run_state.copy()
        original_file = sched._state_file
        sched._state_file = tmp_path / "state.json"

        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        sched._run_state = {"old_task": f"{today}T08:00:00+00:00"}

        try:
            mock_fn = MagicMock()
            from pipeline_runner.scheduler import _guarded_run
            _guarded_run("old_task", mock_fn, settings)
            mock_fn.assert_not_called()
        finally:
            sched._run_state = original_state
            sched._state_file = original_file


class TestHandleSignal:
    def test_handle_signal_sets_shutdown_flag(self) -> None:
        import pipeline_runner.scheduler as sched
        original = sched._shutdown
        try:
            from pipeline_runner.scheduler import _handle_signal
            _handle_signal(15, None)
            assert sched._shutdown is True
        finally:
            sched._shutdown = original


class TestRunScheduler:
    def test_run_scheduler_exits_on_shutdown(
        self, tmp_data_dir: Path
    ) -> None:
        """run_scheduler exits (calls sys.exit) when shutdown flag is set."""
        import pipeline_runner.scheduler as sched
        import schedule as sched_lib

        settings = PodcastSettings(PODCAST_DATA_DIR=str(tmp_data_dir))
        sched_lib.clear()

        original_shutdown = sched._shutdown
        original_state = sched._run_state.copy()
        original_state_file = sched._state_file

        # Pre-set shutdown so the loop exits immediately
        sched._shutdown = True
        try:
            with pytest.raises(SystemExit) as exc_info:
                from pipeline_runner.scheduler import run_scheduler
                run_scheduler(settings)
            assert exc_info.value.code == 0
        finally:
            sched._shutdown = original_shutdown
            sched._run_state = original_state
            sched._state_file = original_state_file
            sched_lib.clear()

    def test_run_scheduler_loads_state(self, tmp_data_dir: Path) -> None:
        """run_scheduler loads persisted state at startup."""
        import pipeline_runner.scheduler as sched
        import schedule as sched_lib
        from datetime import UTC, datetime as _dt

        settings = PodcastSettings(PODCAST_DATA_DIR=str(tmp_data_dir))
        sched_lib.clear()

        # Write a state file indicating task ran today
        state_file = settings.log_dir / "scheduler_state.json"
        today = _dt.now(tz=UTC).strftime("%Y-%m-%d")
        state_file.write_text(json.dumps({"weekly_episode": f"{today}T06:00:00+00:00"}))

        original_shutdown = sched._shutdown
        original_state = sched._run_state.copy()
        original_state_file = sched._state_file

        sched._shutdown = True
        try:
            with pytest.raises(SystemExit):
                from pipeline_runner.scheduler import run_scheduler
                run_scheduler(settings)
        finally:
            sched._shutdown = original_shutdown
            sched._run_state = original_state
            sched._state_file = original_state_file
            sched_lib.clear()
