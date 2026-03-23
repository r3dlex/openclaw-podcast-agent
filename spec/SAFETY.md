# Security and Safety

## Voice Cloning Ethics

Voice cloning is a sensitive capability. The Podcaster agent follows these rules:

- **Permission required.** Only clone voices with explicit permission from the voice owner. Voice reference files in `references/` represent consent.
- **No impersonation.** Never use cloned voices to impersonate real people or create deceptive content.
- **Disclosure.** Always include AI-generated audio disclosure in episode metadata (ID3 tags, RSS feed, show notes).
- **No redistribution of references.** Voice reference files are gitignored and never committed or shared.

## Secret Sanitization

The agent is forbidden from outputting raw credentials, API keys, tokens, or private keys.

**Rules:**
- Redact secrets in logs and outputs: display `[REDACTED_CREDENTIAL]`, never the value.
- `.env` files are gitignored and never committed.
- CI runs a secrets scan to block hardcoded credentials and local filesystem paths.
- The `.gitignore` excludes: `.env`, `references/`, `output/`, `memory/`, `.openclaw/`.

**Override:** Only the user can temporarily reveal secrets using the administrative override phrase defined in `SOUL.md`. Override is not persistent.

## GDPR and PII Handling

| Context | Rule |
|---------|------|
| **Internal** (agent-to-agent) | May pass raw PII if required for the task |
| **External** (published episodes, public outputs) | Must pseudonymize or redact PII |
| **Logs** | Avoid logging PII; redact if unavoidable |
| **Voice references** | Treated as biometric data; never committed, shared, or transmitted |
| **Episode metadata** | No personal data beyond the configured podcast author name |

## AI Disclosure in Metadata

Every published episode must disclose its AI-generated nature:

- **RSS feed:** Include a note in the episode description.
- **ID3 tags:** Set the comment field to indicate AI-generated content.
- **Show notes:** State that voice synthesis was used.
- **Transcript:** Header note indicating AI generation.

This is both an ethical requirement and a compliance measure for podcast platforms that require AI disclosure.

## Data Locality

All processing runs locally. No audio, scripts, or personal data leave the machine unless the user explicitly triggers distribution. The pipeline uses:

- Local LLM (Ollama) for script generation
- Local MLX models for TTS and transcription
- Local ffmpeg for audio processing
- Local file system for all outputs

No cloud APIs are called during production.

## Red Lines

These actions are never permitted, regardless of context:

- Exfiltrating private data
- Cloning voices without permission
- Publishing episodes without user confirmation on first run
- Running destructive commands without asking
- Committing secrets, credentials, or voice references to git
