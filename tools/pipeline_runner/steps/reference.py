"""Reference audio preparation step.

Converts voice reference audio to TTS-compatible format using ffmpeg:
mono, 24kHz, 16-bit signed PCM WAV, trimmed to configured duration.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pipeline_runner.config import PodcastConfig, PodcastSettings
from pipeline_runner.utils.ffmpeg import convert_reference_audio

logger = logging.getLogger(__name__)


class PrepareReferenceStep:
    """Prepare voice reference audio for TTS.

    Context in:  language_config (dict with voice_reference, voice_transcript), settings
    Context out: reference_audio_path (Path), reference_text (str)
    """

    name = "prepare_reference"

    def should_run(self, context: dict[str, Any]) -> bool:
        return "language_config" in context

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        settings: PodcastSettings = context.get("settings", PodcastSettings())
        lang_config = context["language_config"]

        ref_path = Path(lang_config.get("voice_reference", ""))
        ref_text = lang_config.get("voice_transcript", "")

        if not ref_path.exists():
            msg = f"Voice reference not found: {ref_path}"
            raise FileNotFoundError(msg)

        # Get audio params from config
        try:
            config = PodcastConfig(settings.podcast_config_file)
            sample_rate = config.sample_rate
            max_duration = config.reference_duration_seconds
        except Exception:
            sample_rate = 24000
            max_duration = 15

        # Convert to TTS format
        output_dir = settings.log_dir
        converted_path = output_dir / f"reference_{lang_config.get('code', 'xx')}.wav"

        convert_reference_audio(
            ref_path,
            converted_path,
            sample_rate=sample_rate,
            max_duration=max_duration,
        )

        context["reference_audio_path"] = converted_path
        context["reference_text"] = ref_text
        logger.info(
            "Prepared reference audio: %s (%dHz, max %ds)",
            converted_path,
            sample_rate,
            max_duration,
        )
        return context
