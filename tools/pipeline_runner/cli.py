"""CLI entry point for the podcast pipeline runner.

Usage:
    pipeline generate-script --topics "..."  — Generate a podcast script
    pipeline generate-episode --topics "..."  — Full episode pipeline
    pipeline voice-preview --text "..." --lang en  — Preview TTS output
    pipeline list-voices                     — Show configured voice references
    pipeline transcribe --input file.mp3     — Transcribe audio
    pipeline validate                        — Validate configuration
    pipeline scheduler                       — Start the long-running scheduler
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from logging.handlers import RotatingFileHandler

from pipeline_runner.config import PodcastConfig, PodcastSettings


def _setup_logging(settings: PodcastSettings, *, verbose: bool = False) -> None:
    """Configure logging to both console and log/ folder."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(fmt))

    # File handler — writes to log/ folder with rotation
    log_dir = settings.log_dir
    log_file = log_dir / "pipeline.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(file_handler)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="Podcast Agent pipeline runner",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate-script
    script_parser = subparsers.add_parser("generate-script", help="Generate podcast script")
    script_parser.add_argument("--topics", required=False, help="Comma-separated topics")
    script_parser.add_argument("--script-file", required=False, help="Path to manual script file")
    script_parser.add_argument(
        "--lang", default=None, help="Language code (default: all configured)"
    )

    # generate-episode
    episode_parser = subparsers.add_parser("generate-episode", help="Full episode pipeline")
    episode_parser.add_argument("--topics", required=False, help="Comma-separated topics")
    episode_parser.add_argument("--script-file", required=False, help="Path to manual script file")
    episode_parser.add_argument(
        "--lang", default=None, help="Comma-separated language codes (default: all configured)"
    )
    episode_parser.add_argument(
        "--skip-cleanup", action="store_true", help="Skip audio cleanup step"
    )

    # voice-preview
    preview_parser = subparsers.add_parser("voice-preview", help="Preview TTS output")
    preview_parser.add_argument("--text", required=True, help="Text to synthesize")
    preview_parser.add_argument("--lang", default="en", help="Language code")

    # list-voices
    subparsers.add_parser("list-voices", help="Show configured voice references")

    # transcribe
    transcribe_parser = subparsers.add_parser("transcribe", help="Transcribe audio file")
    transcribe_parser.add_argument("--input", required=True, help="Path to audio file")

    # validate
    subparsers.add_parser("validate", help="Validate configuration")

    # scheduler
    subparsers.add_parser("scheduler", help="Start the long-running scheduler (blocks)")

    args = parser.parse_args()

    settings = PodcastSettings()
    _setup_logging(settings, verbose=args.verbose)

    if args.command == "generate-script":
        from pipeline_runner.pipelines.script import run_script_pipeline

        result = run_script_pipeline(
            settings,
            topics=args.topics,
            script_file=args.script_file,
            lang=args.lang,
        )
        print(result)
    elif args.command == "generate-episode":
        from pipeline_runner.pipelines.episode import run_episode_pipeline

        result = run_episode_pipeline(
            settings,
            topics=args.topics,
            script_file=args.script_file,
            langs=args.lang,
            skip_cleanup=args.skip_cleanup,
        )
        print(result)
    elif args.command == "voice-preview":
        from pipeline_runner.pipelines.voice import run_voice_preview

        result = run_voice_preview(settings, text=args.text, lang=args.lang)
        print(result)
    elif args.command == "list-voices":
        _list_voices(settings)
    elif args.command == "transcribe":
        from pipeline_runner.pipelines.distribute import run_transcribe_pipeline

        result = run_transcribe_pipeline(settings, input_path=args.input)
        print(result)
    elif args.command == "validate":
        _validate(settings)
    elif args.command == "scheduler":
        from pipeline_runner.scheduler import run_scheduler

        run_scheduler(settings)
    else:
        parser.print_help()
        sys.exit(1)


def _list_voices(settings: PodcastSettings) -> None:
    """List configured voice references per language."""
    try:
        config = PodcastConfig(settings.podcast_config_file)
        print("Configured voices:")
        print(f"  TTS engine: {config.tts.get('engine', 'unknown')}")
        print(f"  Quantization: {config.tts.get('quantization', 'N/A')}-bit")
        print()
        for lang in config.languages:
            from pathlib import Path

            ref_path = Path(lang.get("voice_reference", ""))
            exists = ref_path.exists() if ref_path.name else False
            status = "OK" if exists else "MISSING"
            print(f"  [{status}] {lang['code']} ({lang['label']})")
            print(f"         Reference: {lang.get('voice_reference', 'N/A')}")
            print(f"         Transcript: {lang.get('voice_transcript', 'N/A')}")
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)


def _validate(settings: PodcastSettings) -> None:
    """Validate configuration files and environment."""
    errors: list[str] = []

    # Check podcast config
    try:
        config = PodcastConfig(settings.podcast_config_file)
        lang_count = len(config.languages)
        engine = config.tts.get("engine", "unknown")
        print(f"Podcast config: {lang_count} languages, TTS engine: {engine}")
    except Exception as e:
        errors.append(f"Podcast config: {e}")

    # Check paths
    if settings.podcast_data_dir.exists():
        print(f"Data dir: {settings.podcast_data_dir} (exists)")
    else:
        errors.append(f"Data dir does not exist: {settings.podcast_data_dir}")

    if settings.librarian_agent_workspace and settings.librarian_agent_workspace.exists():
        print(f"Librarian workspace: {settings.librarian_agent_workspace} (exists)")
    else:
        print(f"Librarian workspace: {settings.librarian_agent_workspace} (not found)")

    # Check podcast.json validity
    try:
        with open(settings.podcast_config_file) as f:
            data = json.load(f)
        required_keys = ["languages", "tts", "audio", "llm"]
        for key in required_keys:
            if key not in data:
                errors.append(f"Missing required key '{key}' in podcast.json")
        print("Config structure: OK")
    except Exception as e:
        errors.append(f"Config file: {e}")

    if errors:
        print(f"\nValidation FAILED with {len(errors)} errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\nValidation OK")


if __name__ == "__main__":
    main()
