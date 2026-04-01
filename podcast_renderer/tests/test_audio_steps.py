"""Tests for audio pipeline steps: cleanup, loudness, concat, assemble, reference, tts_step."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from podcast_renderer.audio.assemble import EpisodeAssemblyStep
from podcast_renderer.audio.cleanup import AudioCleanupStep
from podcast_renderer.audio.concat import ConcatenateStep
from podcast_renderer.audio.loudness import LoudnessNormStep
from podcast_renderer.audio.reference import PrepareReferenceStep
from podcast_renderer.audio.tts_step import TTSGenerationStep


# ---------------------------------------------------------------------------
# AudioCleanupStep
# ---------------------------------------------------------------------------

class TestAudioCleanupStep:
    def test_name(self) -> None:
        assert AudioCleanupStep().name == "audio_cleanup"

    def test_should_run_with_raw_audio(self) -> None:
        step = AudioCleanupStep()
        assert step.should_run({"raw_episode_audio": Path("/tmp/ep.wav")})

    def test_should_not_run_when_skip_cleanup(self) -> None:
        step = AudioCleanupStep()
        ctx: dict[str, Any] = {
            "raw_episode_audio": Path("/tmp/ep.wav"),
            "skip_cleanup": True,
        }
        assert not step.should_run(ctx)

    def test_should_not_run_without_raw_audio(self) -> None:
        step = AudioCleanupStep()
        assert not step.should_run({})

    @patch("podcast_renderer.audio.cleanup.run_ffmpeg")
    def test_execute_calls_ffmpeg(self, mock_ffmpeg: MagicMock, tmp_path: Path) -> None:
        mock_ffmpeg.return_value = MagicMock(returncode=0)
        raw = tmp_path / "raw_episode.wav"
        raw.touch()
        ctx: dict[str, Any] = {
            "raw_episode_audio": raw,
            "settings": SimpleNamespace(),
        }
        step = AudioCleanupStep()
        result = step.execute(ctx)
        assert "clean_episode_audio" in result
        mock_ffmpeg.assert_called_once()

    @patch("podcast_renderer.audio.cleanup.run_ffmpeg")
    def test_execute_output_path(self, mock_ffmpeg: MagicMock, tmp_path: Path) -> None:
        mock_ffmpeg.return_value = MagicMock(returncode=0)
        raw = tmp_path / "raw_episode.wav"
        raw.touch()
        ctx: dict[str, Any] = {"raw_episode_audio": raw}
        result = AudioCleanupStep().execute(ctx)
        assert result["clean_episode_audio"] == raw.parent / "clean_episode.wav"

    @patch("podcast_renderer.audio.cleanup.run_ffmpeg")
    def test_execute_uses_filter_chain(self, mock_ffmpeg: MagicMock, tmp_path: Path) -> None:
        mock_ffmpeg.return_value = MagicMock(returncode=0)
        raw = tmp_path / "raw_episode.wav"
        raw.touch()
        ctx: dict[str, Any] = {"raw_episode_audio": raw}
        AudioCleanupStep().execute(ctx)
        args = mock_ffmpeg.call_args[0][0]
        # filter chain contains highpass and afftdn
        filter_arg = " ".join(args)
        assert "highpass" in filter_arg
        assert "afftdn" in filter_arg


# ---------------------------------------------------------------------------
# LoudnessNormStep
# ---------------------------------------------------------------------------

class TestLoudnessNormStep:
    def test_name(self) -> None:
        assert LoudnessNormStep().name == "loudness_norm"

    def test_should_run_with_clean_audio(self) -> None:
        step = LoudnessNormStep()
        assert step.should_run({"clean_episode_audio": Path("/tmp/clean.wav")})

    def test_should_run_with_raw_audio(self) -> None:
        step = LoudnessNormStep()
        assert step.should_run({"raw_episode_audio": Path("/tmp/raw.wav")})

    def test_should_not_run_without_audio(self) -> None:
        step = LoudnessNormStep()
        assert not step.should_run({})

    @patch("podcast_renderer.audio.loudness.run_ffmpeg")
    def test_execute_uses_config_targets(
        self,
        mock_ffmpeg: MagicMock,
        tmp_path: Path,
        test_settings: Any,
    ) -> None:
        # Pass 1 returns JSON measurement in stderr
        measurement_json = json.dumps({
            "input_i": "-20",
            "input_tp": "-3",
            "input_lra": "5",
            "input_thresh": "-30",
        })
        pass1_result = MagicMock(returncode=0, stdout="", stderr=measurement_json)
        pass2_result = MagicMock(returncode=0, stdout="", stderr="")
        mock_ffmpeg.side_effect = [pass1_result, pass2_result]

        clean = tmp_path / "clean_episode.wav"
        clean.touch()

        ctx: dict[str, Any] = {
            "clean_episode_audio": clean,
            "settings": test_settings,
        }
        result = LoudnessNormStep().execute(ctx)
        assert "normalized_audio" in result
        assert mock_ffmpeg.call_count == 2

    @patch("podcast_renderer.audio.loudness.run_ffmpeg")
    def test_execute_single_pass_fallback_when_no_json(
        self, mock_ffmpeg: MagicMock, tmp_path: Path, test_settings: Any
    ) -> None:
        # Pass 1 returns no parseable JSON — triggers single-pass fallback
        pass1 = MagicMock(returncode=0, stdout="", stderr="no json here")
        pass2 = MagicMock(returncode=0, stdout="", stderr="")
        mock_ffmpeg.side_effect = [pass1, pass2]

        raw = tmp_path / "raw_episode.wav"
        raw.touch()

        ctx: dict[str, Any] = {
            "raw_episode_audio": raw,
            "settings": test_settings,
        }
        result = LoudnessNormStep().execute(ctx)
        assert "normalized_audio" in result

    @patch("podcast_renderer.audio.loudness.run_ffmpeg")
    def test_execute_uses_defaults_when_config_fails(
        self, mock_ffmpeg: MagicMock, tmp_path: Path
    ) -> None:
        """When settings.podcast_config_file is invalid, defaults are used."""
        pass1 = MagicMock(returncode=0, stdout="", stderr="{}")
        pass2 = MagicMock(returncode=0, stdout="", stderr="")
        mock_ffmpeg.side_effect = [pass1, pass2]

        raw = tmp_path / "raw_episode.wav"
        raw.touch()
        settings = SimpleNamespace(podcast_config_file=tmp_path / "missing.json")

        ctx: dict[str, Any] = {
            "raw_episode_audio": raw,
            "settings": settings,
        }
        result = LoudnessNormStep().execute(ctx)
        assert "normalized_audio" in result


# ---------------------------------------------------------------------------
# ConcatenateStep
# ---------------------------------------------------------------------------

class TestConcatenateStep:
    def test_name(self) -> None:
        assert ConcatenateStep().name == "concatenate"

    def test_should_run_with_segments(self) -> None:
        step = ConcatenateStep()
        assert step.should_run({"raw_audio_segments": [Path("/tmp/seg.wav")]})

    def test_should_not_run_with_empty_list(self) -> None:
        step = ConcatenateStep()
        assert not step.should_run({"raw_audio_segments": []})

    def test_should_not_run_without_key(self) -> None:
        step = ConcatenateStep()
        assert not step.should_run({})

    def test_single_segment_no_ffmpeg(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg_0000.wav"
        seg.touch()
        settings = SimpleNamespace(output_dir=tmp_path)
        ctx: dict[str, Any] = {
            "raw_audio_segments": [seg],
            "settings": settings,
            "episode_id": "test",
        }
        result = ConcatenateStep().execute(ctx)
        assert result["raw_episode_audio"] == seg

    @patch("podcast_renderer.audio.concat.run_ffmpeg")
    def test_multiple_segments_concatenates(
        self, mock_ffmpeg: MagicMock, tmp_path: Path
    ) -> None:
        mock_ffmpeg.return_value = MagicMock(returncode=0)
        segs = [tmp_path / f"seg_{i}.wav" for i in range(3)]
        for s in segs:
            s.touch()

        # Create expected output dir
        (tmp_path / "output" / "tmp" / "ep").mkdir(parents=True)

        settings = SimpleNamespace(output_dir=tmp_path / "output")
        ctx: dict[str, Any] = {
            "raw_audio_segments": segs,
            "settings": settings,
            "episode_id": "ep",
        }
        result = ConcatenateStep().execute(ctx)
        mock_ffmpeg.assert_called_once()
        assert "raw_episode_audio" in result

    @patch("podcast_renderer.audio.concat.run_ffmpeg")
    def test_writes_concat_list_file(
        self, mock_ffmpeg: MagicMock, tmp_path: Path
    ) -> None:
        mock_ffmpeg.return_value = MagicMock(returncode=0)
        segs = [tmp_path / f"seg_{i}.wav" for i in range(2)]
        for s in segs:
            s.touch()

        output_base = tmp_path / "out"
        (output_base / "tmp" / "ep2").mkdir(parents=True)

        settings = SimpleNamespace(output_dir=output_base)
        ctx: dict[str, Any] = {
            "raw_audio_segments": segs,
            "settings": settings,
            "episode_id": "ep2",
        }
        ConcatenateStep().execute(ctx)
        list_file = output_base / "tmp" / "ep2" / "concat_list.txt"
        assert list_file.exists()


# ---------------------------------------------------------------------------
# EpisodeAssemblyStep
# ---------------------------------------------------------------------------

class TestEpisodeAssemblyStep:
    def test_name(self) -> None:
        assert EpisodeAssemblyStep().name == "episode_assembly"

    def test_should_run_with_normalized_audio(self) -> None:
        step = EpisodeAssemblyStep()
        assert step.should_run({"normalized_audio": Path("/tmp/norm.wav")})

    def test_should_not_run_without_normalized_audio(self) -> None:
        step = EpisodeAssemblyStep()
        assert not step.should_run({})

    @patch("podcast_renderer.audio.assemble.run_ffmpeg")
    def test_execute_produces_mp3_and_wav(
        self, mock_ffmpeg: MagicMock, tmp_path: Path, test_settings: Any
    ) -> None:
        mock_ffmpeg.return_value = MagicMock(returncode=0)
        norm = tmp_path / "normalized_episode.wav"
        norm.touch()

        ctx: dict[str, Any] = {
            "normalized_audio": norm,
            "settings": test_settings,
            "episode_id": "ep001",
            "language": "en",
        }
        result = EpisodeAssemblyStep().execute(ctx)
        assert "episode_wav" in result
        assert "episode_mp3" in result
        assert str(result["episode_mp3"]).endswith(".mp3")

    @patch("podcast_renderer.audio.assemble.run_ffmpeg")
    def test_execute_uses_config_bitrate(
        self, mock_ffmpeg: MagicMock, tmp_path: Path, test_settings: Any
    ) -> None:
        mock_ffmpeg.return_value = MagicMock(returncode=0)
        norm = tmp_path / "normalized_episode.wav"
        norm.touch()

        ctx: dict[str, Any] = {
            "normalized_audio": norm,
            "settings": test_settings,
            "episode_id": "ep001",
            "language": "en",
        }
        EpisodeAssemblyStep().execute(ctx)
        # Two ffmpeg calls: WAV copy + MP3 encode
        assert mock_ffmpeg.call_count == 2

    @patch("podcast_renderer.audio.assemble.run_ffmpeg")
    def test_execute_with_intro_outro(
        self, mock_ffmpeg: MagicMock, tmp_path: Path, test_settings: Any
    ) -> None:
        """When intro/outro exist, _assemble_with_parts is called."""
        mock_ffmpeg.return_value = MagicMock(returncode=0)

        intro = tmp_path / "intro.wav"
        intro.touch()
        outro = tmp_path / "outro.wav"
        outro.touch()
        norm = tmp_path / "normalized_episode.wav"
        norm.touch()

        # Patch config to return intro/outro paths
        with patch("podcast_renderer.audio.assemble.PodcastConfig") as mock_cfg_cls:
            mock_cfg = MagicMock()
            mock_cfg.mp3_bitrate = 192
            mock_cfg.intro_audio = str(intro)
            mock_cfg.outro_audio = str(outro)
            mock_cfg_cls.return_value = mock_cfg

            ctx: dict[str, Any] = {
                "normalized_audio": norm,
                "settings": test_settings,
                "episode_id": "ep002",
                "language": "en",
            }
            result = EpisodeAssemblyStep().execute(ctx)
        assert "episode_mp3" in result

    @patch("podcast_renderer.audio.assemble.run_ffmpeg")
    def test_assemble_with_parts_single_part(
        self, mock_ffmpeg: MagicMock, tmp_path: Path
    ) -> None:
        """_assemble_with_parts with only voice track (no intro/outro found)."""
        mock_ffmpeg.return_value = MagicMock(returncode=0)
        norm = tmp_path / "norm.wav"
        norm.touch()
        out = tmp_path / "assembled.wav"
        step = EpisodeAssemblyStep()
        # Pass nonexistent intro/outro paths so they don't get included
        step._assemble_with_parts(norm, out, "/nonexistent/intro.wav", "/nonexistent/outro.wav")
        # Only voice: single ffmpeg copy call
        mock_ffmpeg.assert_called_once()


# ---------------------------------------------------------------------------
# PrepareReferenceStep
# ---------------------------------------------------------------------------

class TestPrepareReferenceStep:
    def test_name(self) -> None:
        assert PrepareReferenceStep().name == "prepare_reference"

    def test_should_run_with_language_config(self) -> None:
        step = PrepareReferenceStep()
        assert step.should_run({"language_config": {"code": "en"}})

    def test_should_not_run_without_language_config(self) -> None:
        step = PrepareReferenceStep()
        assert not step.should_run({})

    def test_raises_when_reference_not_found(
        self, tmp_path: Path, test_settings: Any
    ) -> None:
        step = PrepareReferenceStep()
        ctx: dict[str, Any] = {
            "language_config": {
                "code": "en",
                "voice_reference": str(tmp_path / "missing.wav"),
                "voice_transcript": "Hello",
            },
            "settings": test_settings,
        }
        with pytest.raises(FileNotFoundError):
            step.execute(ctx)

    @patch("podcast_renderer.audio.reference.convert_reference_audio")
    def test_execute_converts_audio(
        self, mock_convert: MagicMock, tmp_path: Path, test_settings: Any
    ) -> None:
        ref_wav = tmp_path / "ref.wav"
        ref_wav.touch()
        converted = tmp_path / "log" / "reference_en.wav"

        mock_convert.return_value = converted

        # Ensure log dir exists
        (tmp_path / "log").mkdir(exist_ok=True)

        ctx: dict[str, Any] = {
            "language_config": {
                "code": "en",
                "voice_reference": str(ref_wav),
                "voice_transcript": "Hello world",
            },
            "settings": test_settings,
        }
        result = PrepareReferenceStep().execute(ctx)
        assert result["reference_audio_path"] == converted
        assert result["reference_text"] == "Hello world"
        mock_convert.assert_called_once()


# ---------------------------------------------------------------------------
# TTSGenerationStep
# ---------------------------------------------------------------------------

class TestTTSGenerationStep:
    def test_name(self) -> None:
        assert TTSGenerationStep().name == "tts_generation"

    def test_should_run_with_all_keys(self, tmp_path: Path) -> None:
        step = TTSGenerationStep()
        ctx: dict[str, Any] = {
            "script": {"segments": []},
            "reference_audio_path": tmp_path / "ref.wav",
            "reference_text": "hello",
        }
        assert step.should_run(ctx)

    def test_should_not_run_without_script(self, tmp_path: Path) -> None:
        step = TTSGenerationStep()
        assert not step.should_run({
            "reference_audio_path": tmp_path / "ref.wav",
            "reference_text": "hello",
        })

    def test_should_not_run_without_reference_audio(self) -> None:
        step = TTSGenerationStep()
        assert not step.should_run({
            "script": {},
            "reference_text": "hello",
        })

    @patch("podcast_renderer.audio.tts_step.get_engine")
    def test_execute_generates_segments(
        self, mock_get_engine: MagicMock, tmp_path: Path, test_settings: Any
    ) -> None:
        # Mock engine
        mock_engine = MagicMock()
        mock_engine.name = "mlx-audio"

        def fake_generate(**kwargs: Any) -> Path:
            out = kwargs["output_path"]
            out.touch()
            return out

        mock_engine.generate.side_effect = fake_generate
        mock_get_engine.return_value = mock_engine

        ref = tmp_path / "ref.wav"
        ref.touch()

        ctx: dict[str, Any] = {
            "settings": test_settings,
            "script": {
                "segments": [
                    {"speaker": "host", "text": "Hello world.", "chunks": ["Hello world."]},
                    {"speaker": "host", "text": "Goodbye.", "chunks": ["Goodbye."]},
                ]
            },
            "reference_audio_path": ref,
            "reference_text": "Hello",
            "episode_id": "ep001",
        }
        result = TTSGenerationStep().execute(ctx)
        assert "raw_audio_segments" in result
        assert len(result["raw_audio_segments"]) == 2

    @patch("podcast_renderer.audio.tts_step.get_engine")
    def test_execute_skips_empty_chunks(
        self, mock_get_engine: MagicMock, tmp_path: Path, test_settings: Any
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.name = "mlx-audio"
        mock_get_engine.return_value = mock_engine

        ref = tmp_path / "ref.wav"
        ref.touch()

        ctx: dict[str, Any] = {
            "settings": test_settings,
            "script": {
                "segments": [
                    {"speaker": "host", "text": "", "chunks": ["", "  ", "Hello."]},
                ]
            },
            "reference_audio_path": ref,
            "reference_text": "Hello",
            "episode_id": "ep001",
        }

        def fake_generate(**kwargs: Any) -> Path:
            out = kwargs["output_path"]
            out.touch()
            return out

        mock_engine.generate.side_effect = fake_generate
        result = TTSGenerationStep().execute(ctx)
        # Only "Hello." should produce a segment
        assert len(result["raw_audio_segments"]) == 1

    @patch("podcast_renderer.audio.tts_step.get_engine")
    def test_execute_reraises_on_failure(
        self, mock_get_engine: MagicMock, tmp_path: Path, test_settings: Any
    ) -> None:
        mock_engine = MagicMock()
        mock_engine.name = "mlx-audio"
        mock_engine.generate.side_effect = RuntimeError("TTS failed")
        mock_get_engine.return_value = mock_engine

        ref = tmp_path / "ref.wav"
        ref.touch()

        ctx: dict[str, Any] = {
            "settings": test_settings,
            "script": {
                "segments": [
                    {"speaker": "host", "text": "Hello.", "chunks": ["Hello."]},
                ]
            },
            "reference_audio_path": ref,
            "reference_text": "Hello",
            "episode_id": "ep001",
        }
        with pytest.raises(RuntimeError, match="TTS failed"):
            TTSGenerationStep().execute(ctx)

    @patch("podcast_renderer.audio.tts_step.get_engine")
    def test_execute_uses_text_when_no_chunks(
        self, mock_get_engine: MagicMock, tmp_path: Path, test_settings: Any
    ) -> None:
        """If no 'chunks' key, falls back to the segment 'text'."""
        mock_engine = MagicMock()
        mock_engine.name = "mlx-audio"

        def fake_generate(**kwargs: Any) -> Path:
            out = kwargs["output_path"]
            out.touch()
            return out

        mock_engine.generate.side_effect = fake_generate
        mock_get_engine.return_value = mock_engine

        ref = tmp_path / "ref.wav"
        ref.touch()

        ctx: dict[str, Any] = {
            "settings": test_settings,
            "script": {
                "segments": [
                    {"speaker": "host", "text": "No chunks here."},
                ]
            },
            "reference_audio_path": ref,
            "reference_text": "Hello",
            "episode_id": "ep001",
        }
        result = TTSGenerationStep().execute(ctx)
        assert len(result["raw_audio_segments"]) == 1
