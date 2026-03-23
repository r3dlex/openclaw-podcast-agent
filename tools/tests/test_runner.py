"""Tests for the core pipeline execution engine."""

from __future__ import annotations

from typing import Any

import pytest

from pipeline_runner.runner import Pipeline, PipelineResult, StepStatus


class PassStep:
    """A step that always succeeds and adds a marker to context."""

    name = "pass_step"

    def should_run(self, context: dict[str, Any]) -> bool:
        return True

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        context["pass_step_ran"] = True
        return context


class FailStep:
    """A step that always raises an exception."""

    name = "fail_step"

    def should_run(self, context: dict[str, Any]) -> bool:
        return True

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        msg = "intentional failure"
        raise RuntimeError(msg)


class SkipStep:
    """A step that always skips."""

    name = "skip_step"

    def should_run(self, context: dict[str, Any]) -> bool:
        return False

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        context["skip_step_ran"] = True
        return context


class ContextStep:
    """A step that reads and writes context values."""

    name = "context_step"

    def should_run(self, context: dict[str, Any]) -> bool:
        return True

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        # Read input and write output
        counter = context.get("counter", 0)
        context["counter"] = counter + 1
        return context


class TestPipeline:
    """Test the Pipeline class."""

    def test_empty_pipeline_succeeds(self) -> None:
        pipeline = Pipeline("empty")
        result = pipeline.run()
        assert result.success
        assert result.pipeline_name == "empty"
        assert len(result.steps) == 0
        assert result.total_duration_ms == 0.0

    def test_single_step_success(self) -> None:
        pipeline = Pipeline("single")
        pipeline.add_step(PassStep())
        result = pipeline.run()
        assert result.success
        assert len(result.steps) == 1
        assert result.steps[0].status == StepStatus.SUCCESS
        assert result.steps[0].name == "pass_step"
        assert result.context.get("pass_step_ran") is True

    def test_multiple_steps_success(self) -> None:
        pipeline = Pipeline("multi")
        pipeline.add_step(PassStep())
        pipeline.add_step(ContextStep())
        result = pipeline.run({"counter": 0})
        assert result.success
        assert len(result.steps) == 2
        assert result.context["counter"] == 1
        assert result.context["pass_step_ran"] is True

    def test_step_skip(self) -> None:
        pipeline = Pipeline("skip")
        pipeline.add_step(SkipStep())
        pipeline.add_step(PassStep())
        result = pipeline.run()
        assert result.success
        assert result.steps[0].status == StepStatus.SKIPPED
        assert result.steps[1].status == StepStatus.SUCCESS
        assert "skip_step_ran" not in result.context

    def test_fail_fast_stops_pipeline(self) -> None:
        pipeline = Pipeline("fail_fast", fail_fast=True)
        pipeline.add_step(FailStep())
        pipeline.add_step(PassStep())
        result = pipeline.run()
        assert not result.success
        assert len(result.steps) == 1  # Second step never ran
        assert result.steps[0].status == StepStatus.FAILED
        assert "RuntimeError" in (result.steps[0].error or "")

    def test_no_fail_fast_continues(self) -> None:
        pipeline = Pipeline("no_fail_fast", fail_fast=False)
        pipeline.add_step(FailStep())
        pipeline.add_step(PassStep())
        result = pipeline.run()
        assert not result.success
        assert len(result.steps) == 2
        assert result.steps[0].status == StepStatus.FAILED
        assert result.steps[1].status == StepStatus.SUCCESS

    def test_context_passes_through(self) -> None:
        pipeline = Pipeline("context")
        pipeline.add_step(ContextStep())
        pipeline.add_step(ContextStep())
        pipeline.add_step(ContextStep())
        result = pipeline.run({"counter": 0})
        assert result.context["counter"] == 3

    def test_add_step_returns_self(self) -> None:
        pipeline = Pipeline("chain")
        result = pipeline.add_step(PassStep())
        assert result is pipeline

    def test_chained_add_step(self) -> None:
        pipeline = Pipeline("chain")
        pipeline.add_step(PassStep()).add_step(ContextStep())
        result = pipeline.run()
        assert result.success
        assert len(result.steps) == 2

    def test_duration_is_positive(self) -> None:
        pipeline = Pipeline("duration")
        pipeline.add_step(PassStep())
        result = pipeline.run()
        assert result.steps[0].duration_ms >= 0

    def test_none_context_defaults_to_empty(self) -> None:
        pipeline = Pipeline("none_ctx")
        pipeline.add_step(PassStep())
        result = pipeline.run(None)
        assert result.success


class TestPipelineResult:
    """Test the PipelineResult class."""

    def test_summary_format(self) -> None:
        pipeline = Pipeline("summary_test")
        pipeline.add_step(PassStep())
        pipeline.add_step(SkipStep())
        result = pipeline.run()
        summary = result.summary()
        assert "Pipeline: summary_test" in summary
        assert "SUCCESS" in summary
        assert "[OK] pass_step" in summary
        assert "[SKIP] skip_step" in summary

    def test_failed_steps_property(self) -> None:
        pipeline = Pipeline("failed", fail_fast=False)
        pipeline.add_step(FailStep())
        pipeline.add_step(PassStep())
        result = pipeline.run()
        assert len(result.failed_steps) == 1
        assert result.failed_steps[0].name == "fail_step"
