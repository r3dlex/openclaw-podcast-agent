# Pipeline Architecture

The podcast agent uses a composable pipeline system ported from the journalist agent pattern. Pipelines are sequences of steps that execute in order, with each step deciding whether to run based on current state.

## Step Protocol

Every step implements this interface:

```python
class Step(Protocol):
    name: str

    def should_run(self, context: dict) -> bool:
        """Return True if this step should execute given the current context."""
        ...

    def execute(self, context: dict) -> dict:
        """Execute the step, returning updated context."""
        ...
```

- `name` — Human-readable identifier, used in logs and reports.
- `should_run(context)` — Guards execution. Returns `False` to skip (e.g., voice step skips if already synthesized).
- `execute(context)` — Performs work, returns the updated context dict for the next step.

## Pipeline Class

The `Pipeline` class chains steps together:

```python
pipeline = Pipeline(
    name="episode",
    steps=[ScriptStep(), VoiceStep(), CleanupStep(), AssemblyStep(), DistributeStep()],
)

result = pipeline.run(initial_context)
```

The pipeline:
1. Iterates through steps in order.
2. Calls `should_run()` — skips if `False`.
3. Calls `execute()` — passes context forward.
4. Logs each step's status (skipped, success, failure).
5. Stops on first failure unless `continue_on_error=True`.

## Pre-Built Pipelines

### Script Pipeline
Generates a podcast script from topics using the local LLM (Ollama).

```bash
docker compose exec scheduler pipeline generate-script --topics "AI news this week"
```

Steps: `ScriptGenerationStep`

### Voice Pipeline
Synthesizes speech from an existing script using MLX TTS.

```bash
pipeline voice-preview --text "Hello world" --lang en
```

Steps: `VoiceSynthesisStep`

**Note:** Must run on host macOS (Apple Silicon required for MLX).

### Cleanup Pipeline
Normalizes and cleans raw TTS audio output.

```bash
docker compose exec scheduler pipeline cleanup --input raw_voice.wav
```

Steps: `LoudnessNormStep`, `SilenceTrimStep`

### Assembly Pipeline
Combines voice audio with intro/outro, generates transcript and show notes.

```bash
docker compose exec scheduler pipeline assemble --episode-dir output/episodes/2026-03-23-en/
```

Steps: `IntroOutroStep`, `CrossfadeStep`, `TranscriptStep`, `ShowNotesStep`

### Distribute Pipeline
Writes final files and updates RSS feed.

```bash
docker compose exec scheduler pipeline distribute --episode-dir output/episodes/2026-03-23-en/
```

Steps: `FileWriteStep`, `RSSUpdateStep`, `IAMQAnnounceStep`, `LibrarianHandoffStep`

### Episode Pipeline (Full)
End-to-end: script through distribution, looping per configured language.

```bash
# Via scheduler (recommended)
docker compose exec scheduler pipeline generate-episode --topics "AI news" --lang en

# One-shot
docker compose run --rm --profile cli pipeline generate-episode --topics "AI news"
```

Steps: All of the above in sequence, repeated per language.

## Context Dictionary

The context dict flows through all steps. Key fields:

| Key | Set By | Description |
|-----|--------|-------------|
| `topics` | CLI/caller | Input topics string |
| `lang` | Pipeline loop | Current language code |
| `script_text` | ScriptGenerationStep | Generated script content |
| `script_path` | ScriptGenerationStep | Path to saved script file |
| `raw_audio_path` | VoiceSynthesisStep | Path to raw TTS output |
| `cleaned_audio_path` | LoudnessNormStep | Path to normalized audio |
| `assembled_audio_path` | IntroOutroStep | Path to final assembled audio |
| `transcript_path` | TranscriptStep | Path to generated transcript |
| `episode_dir` | Pipeline | Output directory for this episode |
| `config` | Pipeline | PodcastConfig instance |

## Running Pipelines

**Preferred method** — via the long-running scheduler service:

```bash
docker compose up -d scheduler
docker compose exec scheduler pipeline <command> [options]
```

**One-shot fallback** — when the scheduler is not running:

```bash
docker compose run --rm --profile cli pipeline <command> [options]
```

**Host-only commands** — TTS and transcription (require Apple Silicon):

```bash
pipeline voice-preview --text "..." --lang en
pipeline transcribe --input episode.mp3
```
