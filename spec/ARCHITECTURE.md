# Architecture Overview

The Openclaw Podcast Agent is an autonomous podcast production system that turns topics and scripts into polished audio episodes. Everything runs locally — no cloud APIs required.

## Five-Stage Pipeline

```
Topics/Script
     |
     v
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Script   │───>│  Voice   │───>│ Cleanup  │───>│ Assembly │───>│Distribute│
│Generation │    │Synthesis │    │  & Norm   │    │  & Meta  │    │  & RSS   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
   Ollama        MLX TTS         ffmpeg         ffmpeg+whisper   File/RSS
  (Docker)      (host macOS)    (Docker)         (hybrid)        (Docker)
```

| Stage | What It Does | Runs Where |
|-------|-------------|------------|
| **Script** | Generate or accept a podcast script from topics via Ollama | Docker |
| **Voice** | Synthesize speech from script using MLX TTS (mlx-audio or f5-tts-mlx) | Host macOS (Apple Silicon) |
| **Cleanup** | Normalize loudness (-16 LUFS), trim silence, apply EQ via ffmpeg | Docker |
| **Assembly** | Combine intro/voice/outro, crossfade, generate transcript and show notes | Hybrid |
| **Distribute** | Write episode files, update RSS feed, announce to IAMQ, hand off to Librarian | Docker |

Each stage is a composable pipeline step. See `spec/PIPELINES.md` for the step protocol and how to combine them.

## Hybrid Docker + Host Architecture

MLX packages (mlx-audio, f5-tts-mlx, mlx-whisper) require Apple Silicon Metal and cannot run inside standard Docker containers. See [ARCH-002](/.archgate/adrs/ARCH-002-zero-install-containerization.md).

```
┌─────────────────────────────────────┐
│           Host macOS (Apple Silicon) │
│                                      │
│  ┌──────────┐    ┌───────────────┐  │
│  │ MLX TTS  │    │ mlx-whisper   │  │
│  │(mlx-audio│    │(transcription)│  │
│  │ /f5-tts) │    │               │  │
│  └──────────┘    └───────────────┘  │
│                                      │
│  ┌──────────────────────────────┐   │
│  │      Docker Engine            │   │
│  │                               │   │
│  │  ┌─────────┐  ┌───────────┐  │   │
│  │  │scheduler│  │  Ollama   │  │   │
│  │  │(pipeline│  │ (LLM for  │  │   │
│  │  │ engine) │  │  scripts) │  │   │
│  │  └─────────┘  └───────────┘  │   │
│  │  ┌─────────┐  ┌───────────┐  │   │
│  │  │ ffmpeg  │  │   IAMQ    │  │   │
│  │  │ (audio) │  │  client   │  │   │
│  │  └─────────┘  └───────────┘  │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

**In Docker:** Pipeline engine, ffmpeg processing, Ollama calls, scheduling, IAMQ heartbeats.
**On host macOS:** TTS voice synthesis, mlx-whisper transcription.

The CLI detects the environment and routes accordingly.

## IAMQ Integration

The agent registers as `podcast_agent` on the Inter-Agent Message Queue (IAMQ) at `$IAMQ_HTTP_URL`. The scheduler sends heartbeats every 2 minutes. Every pipeline announces completion to the Librarian agent for archival. See `spec/COMMUNICATION.md` for protocol details.

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `pipeline_runner/runner.py` | Pipeline engine | Generic step executor (from journalist pattern) |
| `pipeline_runner/config.py` | Config loader | PodcastSettings + PodcastConfig from `config/podcast.json` |
| `pipeline_runner/cli.py` | CLI entry point | Commands: generate-script, generate-episode, voice-preview, etc. |
| `pipeline_runner/scheduler.py` | Scheduler | Long-running service with cron + IAMQ heartbeat |
| `pipeline_runner/tts/base.py` | TTS protocol | Abstract engine interface |
| `pipeline_runner/tts/mlx_audio_engine.py` | mlx-audio TTS | Qwen3-TTS via mlx-audio |
| `pipeline_runner/tts/f5_tts_engine.py` | f5-tts-mlx TTS | F5-TTS engine (maintenance mode) |
| `pipeline_runner/utils/ffmpeg.py` | ffmpeg helper | Shared audio processing utilities |
| `pipeline_runner/pipelines/` | Pre-built pipelines | Script, voice, cleanup, assembly, distribute, episode |
| `pipeline_runner/steps/` | Pipeline steps | Individual composable steps |
| `config/podcast.json` | Config | Languages, TTS engine, audio params, schedule |
| `config/rss_template.xml` | RSS template | Feed template for distribution |

## ADR Index

| ADR | Title | Status |
|-----|-------|--------|
| [ARCH-001](/.archgate/adrs/ARCH-001-podcast-production-pipeline.md) | Podcast Production Pipeline | Accepted |
| [ARCH-002](/.archgate/adrs/ARCH-002-zero-install-containerization.md) | Zero-Install Containerization | Accepted |
| [ARCH-003](/.archgate/adrs/ARCH-003-dual-tts-engine-architecture.md) | Dual TTS Engine Architecture | Accepted |
| [ARCH-004](/.archgate/adrs/ARCH-004-inter-agent-collaboration.md) | Inter-Agent Collaboration | Accepted |
| [ARCH-005](/.archgate/adrs/ARCH-005-multilingual-episode-generation.md) | Multilingual Episode Generation | Accepted |
