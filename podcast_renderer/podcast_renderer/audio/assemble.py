"""Episode assembly step — combine normalized voice with intro/outro.

Uses ffmpeg to assemble the final episode with optional intro and outro
music, crossfades, and export to both MP3 and WAV formats.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from podcast_renderer.audio.ffmpeg import run_ffmpeg
from podcast_renderer.config import PodcastConfig

logger = logging.getLogger(__name__)


class EpisodeAssemblyStep:
    """Assemble the final episode from normalized audio + optional intro/outro.

    Context in:  normalized_audio (Path), settings, episode_id
    Context out: episode_mp3 (Path), episode_wav (Path)
    """

    name = "episode_assembly"

    def should_run(self, context: dict[str, Any]) -> bool:
        return "normalized_audio" in context

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        settings = context.get("settings")
        normalized = Path(context["normalized_audio"])

        # Get config
        try:
            config = PodcastConfig(settings.podcast_config_file)
            mp3_bitrate = config.mp3_bitrate
            intro_audio = config.intro_audio
            outro_audio = config.outro_audio
        except Exception:
            mp3_bitrate = 192
            intro_audio = ""
            outro_audio = ""

        episode_id = context.get("episode_id", "episode")
        lang = context.get("language", "en")
        output_dir = settings.output_dir / "episodes" / episode_id / lang
        output_dir.mkdir(parents=True, exist_ok=True)

        # If intro/outro exist, concatenate them
        if intro_audio and Path(intro_audio).exists():
            assembled = output_dir / "assembled.wav"
            self._assemble_with_parts(normalized, assembled, intro_audio, outro_audio)
            source_wav = assembled
        else:
            source_wav = normalized

        # Export WAV (copy)
        wav_path = output_dir / f"{episode_id}_{lang}.wav"
        run_ffmpeg(["-i", str(source_wav), "-c", "copy", str(wav_path)])

        # Export MP3
        mp3_path = output_dir / f"{episode_id}_{lang}.mp3"
        run_ffmpeg(
            [
                "-i",
                str(source_wav),
                "-codec:a",
                "libmp3lame",
                "-b:a",
                f"{mp3_bitrate}k",
                str(mp3_path),
            ]
        )

        context["episode_wav"] = wav_path
        context["episode_mp3"] = mp3_path
        logger.info("Episode assembled: %s (WAV + MP3)", output_dir)
        return context

    def _assemble_with_parts(
        self,
        voice: Path,
        output: Path,
        intro_audio: str,
        outro_audio: str,
    ) -> None:
        """Concatenate intro + voice + outro."""
        parts = []
        if intro_audio and Path(intro_audio).exists():
            parts.append(intro_audio)
        parts.append(str(voice))
        if outro_audio and Path(outro_audio).exists():
            parts.append(outro_audio)

        if len(parts) == 1:
            # Just copy the voice track
            run_ffmpeg(["-i", str(voice), "-c", "copy", str(output)])
            return

        # Write concat list
        list_file = output.parent / "assembly_list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for part in parts:
                escaped = part.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        run_ffmpeg(
            [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(output),
            ]
        )
