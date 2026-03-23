# Troubleshooting

Common issues and their fixes.

## MLX Not Available

**Symptom:** `ModuleNotFoundError: No module named 'mlx'` or TTS/transcription commands fail.

**Cause:** MLX packages require Apple Silicon (M1/M2/M3/M4) with macOS. They cannot run inside Docker or on Intel Macs.

**Fix:**
- Run TTS and transcription commands directly on the host macOS, not via Docker.
- Use `pipeline voice-preview` and `pipeline transcribe` from the host shell.
- Docker-based commands (`docker compose exec scheduler pipeline ...`) handle non-MLX steps only.
- In CI, all MLX-dependent tests are mocked — see `spec/TESTING.md`.

## MiniMax API Errors

**Symptom:** Script generation fails with connection or authentication errors.

**Cause:** MiniMax API is unreachable, API key is invalid, or the model is misconfigured.

**Fix:**
1. Verify the API key is set: check `MINIMAX_API_KEY` in `.env`.
2. Test connectivity: `curl -H "Authorization: Bearer $MINIMAX_API_KEY" $MINIMAX_BASE_URL/models`
3. Confirm the model name: `MINIMAX_MODEL` should be `MiniMax-M2.7` (or as configured).
4. Check `config/podcast.json` field `llm.model` matches the expected model.
5. MiniMax uses an Anthropic-compatible API — ensure `MINIMAX_BASE_URL` points to the correct endpoint.
6. Check rate limits: MiniMax may throttle requests if you exceed your plan quota.

## ffmpeg Not Found

**Symptom:** Audio cleanup or assembly steps fail with `ffmpeg: command not found`.

**Cause:** ffmpeg is not installed in the execution environment.

**Fix:**
- **In Docker:** ffmpeg is included in the base image. If missing, rebuild: `docker compose build`.
- **On host:** Install via Homebrew: `brew install ffmpeg`.
- Verify: `ffmpeg -version`.

## Voice Reference Format Issues

**Symptom:** TTS produces garbled audio, errors about unsupported format, or silence.

**Cause:** Voice reference files must meet specific requirements.

**Fix:**
1. Reference audio should be WAV format, mono, 24 kHz sample rate.
2. Duration: 10-15 seconds of clean speech (no music, no background noise).
3. The `voice_transcript` field in `config/podcast.json` must exactly match what is spoken in the reference.
4. Check path: `references/en_voice.wav` (or per-language path in config).
5. Validate with: `ffprobe -i references/en_voice.wav`
6. Convert if needed: `ffmpeg -i input.mp3 -ar 24000 -ac 1 references/en_voice.wav`

## Memory Issues During TTS

**Symptom:** Process killed, `MemoryError`, or macOS becomes unresponsive during voice synthesis.

**Cause:** MLX TTS models consume significant memory, especially for long scripts.

**Fix:**
1. Use the 4-bit quantized model (default): `mlx-community/Qwen3-TTS-0.6B-4bit`.
2. Reduce `tts.max_segment_chars` in `config/podcast.json` (default 200) to process smaller chunks.
3. Close other memory-intensive applications during synthesis.
4. Monitor with: `sudo powermetrics --samplers gpu_power -i 1000`.
5. For very long episodes, consider splitting the script and synthesizing in batches.

## IAMQ Connection Failed

**Symptom:** Heartbeat or inbox check fails with connection refused.

**Cause:** The IAMQ service is not running.

**Fix:**
1. Check if IAMQ is up: `curl http://127.0.0.1:18790/status`
2. The IAMQ service runs separately from the podcast agent — start it if needed.
3. From Docker, use `http://host.docker.internal:18790` as the URL.
4. Check `IAMQ_HTTP_URL` in `.env` or `docker-compose.yml`.
5. Non-fatal: the scheduler continues without IAMQ, but heartbeats and announcements will fail silently.

## Scheduler Not Starting

**Symptom:** `docker compose up -d scheduler` exits immediately.

**Fix:**
1. Check logs: `docker compose logs scheduler`
2. Verify `.env` file exists (copy from `.env.example` if missing).
3. Rebuild: `docker compose build scheduler`
4. Check `config/podcast.json` is valid JSON: `python -m json.tool config/podcast.json`
