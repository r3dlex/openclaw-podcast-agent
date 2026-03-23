"""Abstract TTS engine interface.

Defines the protocol that all TTS engines must implement. This allows
switching between mlx-audio (Qwen3-TTS) and f5-tts-mlx via config.

See ARCH-003 for the design rationale.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSEngine(Protocol):
    """Protocol for TTS engines.

    All TTS engines must implement this interface to be used
    by the TTSGenerationStep.
    """

    @property
    def name(self) -> str:
        """Engine identifier (e.g., 'mlx-audio', 'f5-tts-mlx')."""
        ...

    def is_available(self) -> bool:
        """Check if the engine's dependencies are installed and functional."""
        ...

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
        """Generate speech audio from text using voice cloning.

        Args:
            text: The text to synthesize.
            reference_audio: Path to reference voice audio (mono, 24kHz, 16-bit WAV).
            reference_text: Transcript of the reference audio.
            output_path: Where to write the generated audio.
            quantization: Model quantization bits (4 or 8).

        Returns:
            Path to the generated audio file.

        Raises:
            RuntimeError: If generation fails.
        """
        ...


def get_engine(engine_name: str) -> TTSEngine:
    """Factory: return the appropriate TTS engine by name.

    Args:
        engine_name: 'mlx-audio' or 'f5-tts-mlx'.

    Returns:
        An instance of the requested TTS engine.

    Raises:
        ValueError: If the engine name is unknown.
        RuntimeError: If the engine's dependencies are not available.
    """
    if engine_name == "mlx-audio":
        from pipeline_runner.tts.mlx_audio_engine import MlxAudioEngine

        engine = MlxAudioEngine()
    elif engine_name == "f5-tts-mlx":
        from pipeline_runner.tts.f5_tts_engine import F5TTSEngine

        engine = F5TTSEngine()
    else:
        msg = f"Unknown TTS engine: {engine_name!r}. Use 'mlx-audio' or 'f5-tts-mlx'."
        raise ValueError(msg)

    if not engine.is_available():
        msg = f"TTS engine '{engine_name}' is not available. Install its dependencies."
        raise RuntimeError(msg)

    return engine
