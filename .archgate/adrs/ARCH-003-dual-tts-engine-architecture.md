---
id: ARCH-003
title: Dual TTS Engine Architecture
domain: architecture
rules: false
---

# ARCH-003: Dual TTS Engine Architecture

## Context

Two MLX-based TTS engines are available for voice synthesis on Apple Silicon:

- **mlx-audio** with Qwen3-TTS: More capable, actively developed, supports quantization (4-bit), better voice cloning quality. Newer and less battle-tested.
- **f5-tts-mlx**: Simpler API, established, but in maintenance mode with no active development.

Committing to a single engine risks being stuck if it becomes unmaintained or if a better option emerges. Both engines have the same fundamental interface: text + voice reference in, audio out.

## Decision

Abstract TTS behind a protocol (`TTSEngine` in `pipeline_runner/tts/base.py`) and support both engines, switchable via `config/podcast.json`:

```python
class TTSEngine(Protocol):
    def synthesize(self, text: str, voice_ref: Path, output: Path, **kwargs) -> Path: ...
```

Implementations:
- `mlx_audio_engine.py` — mlx-audio with Qwen3-TTS (default)
- `f5_tts_engine.py` — f5-tts-mlx (fallback)

Engine selection is driven by `config/podcast.json` field `tts.engine`, overridable by the `TTS_ENGINE` environment variable.

## Consequences

**Positive:**
- Can switch engines without code changes (config or env var).
- Easy to add new engines (e.g., if a better MLX TTS appears).
- Pipeline steps are decoupled from TTS implementation.
- Can A/B test quality between engines.

**Negative:**
- Must maintain two engine implementations.
- Subtle differences in output quality/format between engines require per-engine testing.
- f5-tts-mlx is in maintenance mode and may eventually break with MLX updates.

## Compliance and Enforcement

- New TTS engines must implement the `TTSEngine` protocol.
- The default engine is configured in `config/podcast.json` and documented.
- Both engines are covered by unit tests (with mocked MLX).
