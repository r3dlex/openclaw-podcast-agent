---
id: ARCH-001
title: Podcast Production Pipeline
domain: architecture
rules: false
---

# ARCH-001: Podcast Production Pipeline

## Context

The Podcaster agent needs to autonomously produce podcast episodes from topics or scripts. The production process involves multiple distinct stages (script writing, voice synthesis, audio processing, assembly, distribution) that have different runtime requirements and failure modes. We need a system that is composable, resumable, and observable.

The Journalist agent already established a step-based pipeline pattern (`runner.py`) that proved effective for multi-stage content production.

## Decision

Adopt a five-stage composable pipeline architecture:

1. **Script** — Generate or accept a podcast script from topics via local LLM (Ollama).
2. **Voice** — Synthesize speech from the script using MLX TTS engines.
3. **Cleanup** — Normalize loudness, trim silence, apply EQ via ffmpeg.
4. **Assembly** — Combine intro/voice/outro with crossfade, generate transcript and show notes.
5. **Distribute** — Write final files, update RSS feed, announce to IAMQ, hand off to Librarian.

Each stage is implemented as one or more `Step` objects following a common protocol (`name`, `should_run`, `execute`). Steps are composed into `Pipeline` instances that can be run individually or chained into the full episode pipeline. A shared context dictionary flows through all steps.

The pipeline engine is ported from the Journalist agent's `runner.py` to maintain consistency across OpenClaw agents.

## Consequences

**Positive:**
- Each stage can be tested, run, and debugged independently.
- Steps can be skipped (e.g., voice step skips if audio already exists).
- New steps can be added without modifying existing ones.
- The full episode pipeline is just a composition of the individual pipelines.
- Consistent pattern with the Journalist agent reduces learning curve.

**Negative:**
- The context dictionary is loosely typed; requires discipline to maintain key conventions.
- Step ordering matters — incorrect composition can produce invalid state.

## Compliance and Enforcement

- All new pipeline steps must implement the Step protocol.
- Pipeline compositions are defined in `pipeline_runner/pipelines/` with clear documentation.
- Integration tests verify step ordering and context flow for each pre-built pipeline.
