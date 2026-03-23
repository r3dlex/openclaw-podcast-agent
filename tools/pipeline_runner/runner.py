"""Core pipeline execution engine.

A pipeline is an ordered sequence of steps. Each step receives a context dict
and returns an updated context dict. Steps can be skipped, retried, or aborted.

See spec/PIPELINES.md and ARCH-001 for the design rationale.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Outcome of a pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class StepResult:
    """Result of executing a single pipeline step."""

    name: str
    status: StepStatus
    duration_ms: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PipelineStep(Protocol):
    """Protocol for pipeline steps.

    Each step is a callable that receives context and returns updated context.
    Steps should be idempotent where possible.
    """

    @property
    def name(self) -> str: ...

    def should_run(self, context: dict[str, Any]) -> bool:
        """Return True if this step should execute given the current context."""
        ...

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the step and return updated context."""
        ...


@dataclass
class PipelineResult:
    """Result of a full pipeline execution."""

    pipeline_name: str
    steps: list[StepResult] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return all(s.status in (StepStatus.SUCCESS, StepStatus.SKIPPED) for s in self.steps)

    @property
    def total_duration_ms(self) -> float:
        return sum(s.duration_ms for s in self.steps)

    @property
    def failed_steps(self) -> list[StepResult]:
        return [s for s in self.steps if s.status == StepStatus.FAILED]

    def summary(self) -> str:
        """Return a human-readable summary of the pipeline run."""
        lines = [f"Pipeline: {self.pipeline_name}"]
        lines.append(f"Status: {'SUCCESS' if self.success else 'FAILED'}")
        lines.append(f"Duration: {self.total_duration_ms:.0f}ms")
        lines.append(f"Steps: {len(self.steps)}")
        for step in self.steps:
            marker = {
                StepStatus.SUCCESS: "OK",
                StepStatus.SKIPPED: "SKIP",
                StepStatus.FAILED: "FAIL",
            }.get(step.status, "?")
            line = f"  [{marker}] {step.name} ({step.duration_ms:.0f}ms)"
            if step.error:
                line += f" — {step.error}"
            lines.append(line)
        return "\n".join(lines)


class Pipeline:
    """Executes a sequence of steps with context passing.

    Usage:
        pipeline = Pipeline("episode_production")
        pipeline.add_step(ScriptStep())
        pipeline.add_step(TTSStep())
        pipeline.add_step(CleanupStep())
        result = pipeline.run(initial_context)
    """

    def __init__(self, name: str, *, fail_fast: bool = True) -> None:
        self.name = name
        self.fail_fast = fail_fast
        self._steps: list[PipelineStep] = []

    def add_step(self, step: PipelineStep) -> Pipeline:
        """Add a step to the pipeline. Returns self for chaining."""
        self._steps.append(step)
        return self

    def run(self, context: dict[str, Any] | None = None) -> PipelineResult:
        """Execute all steps in order."""
        ctx = dict(context or {})
        result = PipelineResult(pipeline_name=self.name, context=ctx)

        logger.info("Pipeline '%s' starting with %d steps", self.name, len(self._steps))

        for step in self._steps:
            if not step.should_run(ctx):
                result.steps.append(StepResult(name=step.name, status=StepStatus.SKIPPED))
                logger.info("Step '%s' skipped", step.name)
                continue

            start = time.monotonic()
            try:
                logger.info("Step '%s' starting", step.name)
                ctx = step.execute(ctx)
                duration = (time.monotonic() - start) * 1000
                result.steps.append(
                    StepResult(name=step.name, status=StepStatus.SUCCESS, duration_ms=duration)
                )
                logger.info("Step '%s' completed in %.0fms", step.name, duration)
            except Exception as exc:
                duration = (time.monotonic() - start) * 1000
                error_msg = f"{type(exc).__name__}: {exc}"
                result.steps.append(
                    StepResult(
                        name=step.name,
                        status=StepStatus.FAILED,
                        duration_ms=duration,
                        error=error_msg,
                    )
                )
                logger.error("Step '%s' failed after %.0fms: %s", step.name, duration, error_msg)
                if self.fail_fast:
                    break

        result.context = ctx
        logger.info(
            "Pipeline '%s' %s in %.0fms",
            self.name,
            "completed" if result.success else "failed",
            result.total_duration_ms,
        )
        return result
