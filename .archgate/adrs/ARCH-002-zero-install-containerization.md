---
id: ARCH-002
title: Zero-Install Containerization
domain: architecture
rules: false
---

# ARCH-002: Zero-Install Containerization

## Context

OpenClaw follows a zero-install principle: agents should work with minimal manual setup via Docker. However, MLX packages (mlx-audio, f5-tts-mlx, mlx-whisper) require Apple Silicon Metal GPU access, which is not available inside standard Docker containers on macOS. Docker Desktop for Mac runs containers in a Linux VM that cannot access the Metal GPU.

The pipeline also depends on ffmpeg, Ollama, and the IAMQ service, which work well in Docker.

## Decision

Use a hybrid Docker + host architecture:

**In Docker (via docker-compose.yml):**
- Pipeline engine and scheduler service
- ffmpeg audio processing (cleanup, normalization, assembly)
- Ollama LLM calls for script generation (via `host.docker.internal`)
- IAMQ heartbeat and messaging client
- Cron-based scheduling

**On host macOS (run natively):**
- TTS voice synthesis via mlx-audio or f5-tts-mlx
- Audio transcription via mlx-whisper

The CLI detects whether it is running inside Docker (no MLX available) or on the host (MLX available) and routes commands accordingly. Docker-based pipeline steps that need TTS delegate to the host.

## Consequences

**Positive:**
- Most of the system follows zero-install via Docker.
- MLX models run at full performance on Apple Silicon Metal.
- ffmpeg, scheduling, and IAMQ work cross-platform in Docker.

**Negative:**
- TTS and transcription require a macOS host with Apple Silicon — not portable.
- Two execution environments increase complexity (testing, deployment, debugging).
- CI cannot test MLX-dependent code directly; must use mocks.

## Compliance and Enforcement

- The Dockerfile does not include MLX packages.
- Tests that touch MLX code must mock the imports.
- The CLI clearly documents which commands require host execution vs Docker.
- `docker-compose.yml` separates services by execution environment.
