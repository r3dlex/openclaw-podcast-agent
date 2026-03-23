"""Shared ffmpeg helper — all audio processing goes through this module.

Provides a single entry point for ffmpeg subprocess calls with consistent
logging, error handling, and timeout management.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Default timeout for ffmpeg operations (5 minutes)
DEFAULT_TIMEOUT = 300


def run_ffmpeg(
    args: list[str],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run an ffmpeg command with consistent error handling.

    Args:
        args: ffmpeg arguments (without the 'ffmpeg' binary itself).
        timeout: Maximum execution time in seconds.
        check: If True, raise CalledProcessError on non-zero exit.

    Returns:
        CompletedProcess with stdout and stderr captured.

    Raises:
        subprocess.CalledProcessError: If ffmpeg exits non-zero and check=True.
        subprocess.TimeoutExpired: If ffmpeg exceeds the timeout.
        FileNotFoundError: If ffmpeg is not installed.
    """
    cmd = ["ffmpeg", "-y", *args]
    logger.debug("Running: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
        )
        logger.debug("ffmpeg completed (returncode=%d)", result.returncode)
        return result
    except FileNotFoundError:
        logger.error("ffmpeg not found. Install ffmpeg or ensure it's in PATH.")
        raise
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timed out after %ds", timeout)
        raise
    except subprocess.CalledProcessError as exc:
        logger.error("ffmpeg failed (rc=%d): %s", exc.returncode, exc.stderr[:500])
        raise


def run_ffprobe(
    args: list[str],
    *,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    """Run an ffprobe command for audio inspection.

    Args:
        args: ffprobe arguments (without the 'ffprobe' binary itself).
        timeout: Maximum execution time in seconds.

    Returns:
        CompletedProcess with stdout and stderr captured.
    """
    cmd = ["ffprobe", *args]
    logger.debug("Running: %s", " ".join(cmd))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    return result


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of an audio file in seconds."""
    result = run_ffprobe([
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ])
    return float(result.stdout.strip())


def convert_reference_audio(
    input_path: Path,
    output_path: Path,
    *,
    sample_rate: int = 24000,
    max_duration: int = 15,
) -> Path:
    """Convert audio to TTS reference format: mono, 24kHz, 16-bit PCM WAV.

    Args:
        input_path: Source audio file.
        output_path: Destination WAV file.
        sample_rate: Target sample rate (default 24000 for TTS).
        max_duration: Maximum duration in seconds.

    Returns:
        Path to the converted file.
    """
    run_ffmpeg([
        "-i", str(input_path),
        "-ac", "1",
        "-ar", str(sample_rate),
        "-sample_fmt", "s16",
        "-t", str(max_duration),
        str(output_path),
    ])
    return output_path
