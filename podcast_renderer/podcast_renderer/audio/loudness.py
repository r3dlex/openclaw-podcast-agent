"""Loudness normalization step — two-pass EBU R128 loudnorm via ffmpeg.

Pass 1: Measure integrated loudness, true peak, LRA
Pass 2: Apply loudnorm with measured values for precise targeting

Default target: -16 LUFS, -1.0 dBTP (podcast standard).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from podcast_renderer.audio.ffmpeg import run_ffmpeg
from podcast_renderer.config import PodcastConfig

logger = logging.getLogger(__name__)


class LoudnessNormStep:
    """Normalize audio loudness using two-pass ffmpeg loudnorm.

    Context in:  clean_episode_audio (Path) or raw_episode_audio (Path), settings
    Context out: normalized_audio (Path)
    """

    name = "loudness_norm"

    def should_run(self, context: dict[str, Any]) -> bool:
        return "clean_episode_audio" in context or "raw_episode_audio" in context

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        settings = context.get("settings")
        input_path = Path(
            context.get("clean_episode_audio") or context["raw_episode_audio"]
        )

        # Get loudness targets from config
        try:
            config = PodcastConfig(settings.podcast_config_file)
            target_lufs = config.loudness_target_lufs
            target_tp = config.true_peak_dbtp
        except Exception:
            target_lufs = -16.0
            target_tp = -1.0

        output_path = input_path.parent / "normalized_episode.wav"

        # Pass 1: Measure
        measured = self._measure_loudness(input_path, target_lufs, target_tp)

        # Pass 2: Apply
        self._apply_loudness(input_path, output_path, target_lufs, target_tp, measured)

        context["normalized_audio"] = output_path
        logger.info(
            "Loudness normalized to %.1f LUFS / %.1f dBTP: %s",
            target_lufs,
            target_tp,
            output_path.name,
        )
        return context

    def _measure_loudness(
        self, input_path: Path, target_lufs: float, target_tp: float
    ) -> dict[str, str]:
        """Pass 1: Measure loudness statistics."""
        result = run_ffmpeg(
            [
                "-i", str(input_path),
                "-af", f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11:print_format=json",
                "-f", "null",
                "-",
            ],
            check=True,
        )

        # Parse the JSON output from stderr
        stderr = result.stderr
        # Find the JSON block in stderr
        json_match = re.search(r"\{[^{}]*\}", stderr, re.DOTALL)
        if json_match:
            try:
                measured: dict[str, str] = json.loads(json_match.group())
                return measured
            except json.JSONDecodeError:
                pass

        logger.warning("Could not parse loudnorm measurement, using single-pass")
        return {}

    def _apply_loudness(
        self,
        input_path: Path,
        output_path: Path,
        target_lufs: float,
        target_tp: float,
        measured: dict[str, str],
    ) -> None:
        """Pass 2: Apply loudness normalization with measured values."""
        if measured:
            filter_str = (
                f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11"
                f":measured_I={measured.get('input_i', '-24')}"
                f":measured_TP={measured.get('input_tp', '-2')}"
                f":measured_LRA={measured.get('input_lra', '7')}"
                f":measured_thresh={measured.get('input_thresh', '-34')}"
            )
        else:
            # Single-pass fallback
            filter_str = f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11"

        run_ffmpeg([
            "-i", str(input_path),
            "-af", filter_str,
            str(output_path),
        ])
