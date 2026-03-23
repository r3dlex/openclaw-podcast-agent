"""mlx-audio TTS engine — Qwen3-TTS via the mlx-audio library.

Uses mlx-audio (github.com/Blaizzy/mlx-audio) for high-quality voice cloning
with Qwen3-TTS. Requires Apple Silicon with MLX framework.

See ARCH-003 for the engine selection rationale.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MlxAudioEngine:
    """TTS engine using mlx-audio with Qwen3-TTS.

    This engine provides:
    - Voice cloning from 3-second reference audio
    - Multilingual support (10+ languages)
    - 4-bit and 8-bit quantization
    - Streaming and batch generation
    """

    @property
    def name(self) -> str:
        return "mlx-audio"

    def is_available(self) -> bool:
        """Check if mlx-audio is installed."""
        try:
            import mlx_audio  # noqa: F401

            return True
        except ImportError:
            logger.debug("mlx-audio not installed")
            return False

    def generate(
        self,
        text: str,
        reference_audio: Path,
        reference_text: str,
        output_path: Path,
        *,
        quantization: int = 4,
        model: str = "mlx-community/Qwen3-TTS-0.6B-4bit",
        **kwargs: object,
    ) -> Path:
        """Generate speech using mlx-audio Qwen3-TTS.

        Args:
            text: Text to synthesize.
            reference_audio: Reference voice audio (mono, 24kHz, 16-bit WAV).
            reference_text: Transcript of reference audio.
            output_path: Where to write the generated WAV.
            quantization: Model quantization bits (4 or 8).
            model: HuggingFace model ID for the TTS model.

        Returns:
            Path to the generated audio file.
        """
        try:
            from mlx_audio.tts import generate as mlx_generate

            # Select model based on quantization
            if quantization == 8:
                model = model.replace("4bit", "8bit")

            logger.info(
                "Generating audio with mlx-audio (model=%s, text=%d chars)",
                model,
                len(text),
            )

            mlx_generate(
                text=text,
                model=model,
                ref_audio=str(reference_audio),
                ref_text=reference_text,
                output=str(output_path),
            )

            if not output_path.exists():
                msg = f"mlx-audio did not produce output at {output_path}"
                raise RuntimeError(msg)

            logger.info("Generated audio: %s", output_path)
            return output_path

        except ImportError as exc:
            msg = "mlx-audio not installed. Run: pip install mlx-audio"
            raise RuntimeError(msg) from exc
