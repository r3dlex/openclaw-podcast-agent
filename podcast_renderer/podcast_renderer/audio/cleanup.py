"""Audio cleanup step — basic noise reduction and filtering via ffmpeg.

Applies a chain of audio filters:
1. Highpass at 80 Hz (remove rumble)
2. Lowpass at 12 kHz (remove hiss)
3. FFT-based denoising (afftdn)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from podcast_renderer.audio.ffmpeg import run_ffmpeg

logger = logging.getLogger(__name__)


class AudioCleanupStep:
    """Clean up raw audio using ffmpeg filters.

    Context in:  raw_episode_audio (Path), settings
    Context out: clean_episode_audio (Path)
    """

    name = "audio_cleanup"

    def should_run(self, context: dict[str, Any]) -> bool:
        return "raw_episode_audio" in context and not context.get("skip_cleanup", False)

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        input_path = Path(context["raw_episode_audio"])

        output_path = input_path.parent / "clean_episode.wav"

        # Audio filter chain: highpass -> lowpass -> fft denoise
        filter_chain = "highpass=f=80,lowpass=f=12000,afftdn=nf=-20"

        run_ffmpeg(
            [
                "-i",
                str(input_path),
                "-af",
                filter_chain,
                str(output_path),
            ]
        )

        context["clean_episode_audio"] = output_path
        logger.info("Audio cleaned: %s -> %s", input_path.name, output_path.name)
        return context
