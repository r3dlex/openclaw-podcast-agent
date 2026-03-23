"""f5-tts-mlx TTS engine — F5-TTS voice cloning on Apple Silicon.

Uses f5-tts-mlx (github.com/lucasnewman/f5-tts-mlx) for zero-shot
voice cloning. Simpler API but in maintenance mode.

See ARCH-003 for the engine selection rationale.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class F5TTSEngine:
    """TTS engine using f5-tts-mlx.

    This engine provides:
    - Zero-shot voice cloning from 10-15s reference audio
    - 4-bit and 8-bit quantization
    - Simple Python API
    """

    @property
    def name(self) -> str:
        return "f5-tts-mlx"

    def is_available(self) -> bool:
        """Check if f5-tts-mlx is installed."""
        try:
            import f5_tts_mlx  # noqa: F401

            return True
        except ImportError:
            logger.debug("f5-tts-mlx not installed")
            return False

    def generate(
        self,
        text: str,
        reference_audio: Path,
        reference_text: str,
        output_path: Path,
        *,
        quantization: int = 4,
        **kwargs: object,
    ) -> Path:
        """Generate speech using f5-tts-mlx.

        Args:
            text: Text to synthesize.
            reference_audio: Reference voice audio (mono, 24kHz, 16-bit WAV).
            reference_text: Transcript of reference audio.
            output_path: Where to write the generated WAV.
            quantization: Model quantization bits (4 or 8).

        Returns:
            Path to the generated audio file.
        """
        try:
            from f5_tts_mlx import generate as f5_generate

            logger.info(
                "Generating audio with f5-tts-mlx (q=%d, text=%d chars)",
                quantization,
                len(text),
            )

            f5_generate(
                text=text,
                ref_audio_path=str(reference_audio),
                ref_audio_text=reference_text,
                output_path=str(output_path),
                q=quantization,
            )

            if not output_path.exists():
                msg = f"f5-tts-mlx did not produce output at {output_path}"
                raise RuntimeError(msg)

            logger.info("Generated audio: %s", output_path)
            return output_path

        except ImportError as exc:
            msg = "f5-tts-mlx not installed. Run: pip install f5-tts-mlx"
            raise RuntimeError(msg) from exc
