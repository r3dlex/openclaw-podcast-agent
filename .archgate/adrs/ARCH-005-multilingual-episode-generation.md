---
id: ARCH-005
title: Multilingual Episode Generation
domain: architecture
rules: false
---

# ARCH-005: Multilingual Episode Generation

## Context

The podcast needs to support multiple languages. Each language requires:

- A separate voice reference audio file with matching transcript.
- Language-specific script generation (or translation).
- Separate output files and potentially different RSS feeds.
- Different TTS behavior (voice characteristics, pacing).

A single monolithic pipeline that handles all languages internally would be complex and hard to debug.

## Decision

Use a config-driven language list with per-language pipeline loops:

**Configuration** (`config/podcast.json`):
```json
{
  "languages": [
    {
      "code": "en",
      "label": "English",
      "voice_reference": "references/en_voice.wav",
      "voice_transcript": "Hello, this is a sample of my voice."
    }
  ]
}
```

**Episode pipeline behavior:**
1. Read the language list from config.
2. For each language, run the full five-stage pipeline with language-specific context.
3. Each language produces its own output directory: `output/episodes/YYYY-MM-DD-{lang}/`.
4. RSS feed and metadata are per-language (or combined, configurable).

**CLI override:** `--lang en` restricts to a single language for ad-hoc runs.

## Consequences

**Positive:**
- Adding a language requires only a config entry and a voice reference file.
- Per-language isolation: a failure in one language does not block others.
- Each language can be tested and previewed independently.
- Output directories are cleanly separated.

**Negative:**
- Total production time scales linearly with the number of languages.
- Script generation may need per-language prompting or translation step.
- Voice references must be sourced and validated for each language.

## Compliance and Enforcement

- New languages are added via `config/podcast.json` only — no code changes required.
- Each language entry must include `code`, `label`, `voice_reference`, and `voice_transcript`.
- Voice reference files must exist at the configured path before running the voice pipeline.
- The `list-voices` CLI command validates configured references.
