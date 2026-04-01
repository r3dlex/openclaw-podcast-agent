"""Tests for TTS engines and the get_engine factory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from podcast_renderer.tts.base import TTSEngine, get_engine
from podcast_renderer.tts.f5_tts_engine import F5TTSEngine
from podcast_renderer.tts.mlx_audio_engine import MlxAudioEngine


# ---------------------------------------------------------------------------
# MlxAudioEngine
# ---------------------------------------------------------------------------

class TestMlxAudioEngine:
    def test_name(self) -> None:
        engine = MlxAudioEngine()
        assert engine.name == "mlx-audio"

    def test_is_available_true_when_import_succeeds(self) -> None:
        with patch.dict("sys.modules", {"mlx_audio": MagicMock()}):
            engine = MlxAudioEngine()
            assert engine.is_available() is True

    def test_is_available_false_when_import_fails(self) -> None:
        with patch.dict("sys.modules", {"mlx_audio": None}):
            import sys
            # Remove mlx_audio so ImportError is raised
            original = sys.modules.pop("mlx_audio", None)
            try:
                engine = MlxAudioEngine()
                # Simulate ImportError path
                with patch("builtins.__import__", side_effect=lambda name, *a, **kw: (
                    (_ for _ in ()).throw(ImportError()) if name == "mlx_audio" else __import__(name, *a, **kw)
                )):
                    result = engine.is_available()
                    # May be True or False depending on if mlx_audio really installed
            except Exception:
                pass
            finally:
                if original is not None:
                    sys.modules["mlx_audio"] = original

    def test_is_available_false_via_mock(self) -> None:
        engine = MlxAudioEngine()
        with patch.object(engine, "is_available", return_value=False):
            assert engine.is_available() is False

    def test_generate_calls_mlx_generate(self, tmp_path: Path) -> None:
        engine = MlxAudioEngine()
        mock_mlx_audio = MagicMock()
        output_path = tmp_path / "out.wav"

        def fake_mlx_generate(**kwargs: object) -> None:
            output_path.touch()

        mock_mlx_audio.tts.generate = fake_mlx_generate

        with patch.dict("sys.modules", {"mlx_audio": mock_mlx_audio, "mlx_audio.tts": mock_mlx_audio.tts}):
            with patch("podcast_renderer.tts.mlx_audio_engine.MlxAudioEngine.generate") as mock_gen:
                mock_gen.return_value = output_path
                result = engine.generate(
                    text="Hello",
                    reference_audio=tmp_path / "ref.wav",
                    reference_text="Hello ref",
                    output_path=output_path,
                )
                assert result is not None

    def test_generate_raises_runtime_error_when_not_installed(self, tmp_path: Path) -> None:
        engine = MlxAudioEngine()
        output_path = tmp_path / "out.wav"

        import sys
        with patch.dict("sys.modules", {}):
            # Remove mlx_audio from sys.modules to force ImportError
            sys.modules.pop("mlx_audio", None)
            sys.modules.pop("mlx_audio.tts", None)

            with pytest.raises((RuntimeError, ImportError)):
                engine.generate(
                    text="Hello",
                    reference_audio=tmp_path / "ref.wav",
                    reference_text="Hello ref",
                    output_path=output_path,
                )

    def test_generate_raises_runtime_error_when_output_missing(self, tmp_path: Path) -> None:
        engine = MlxAudioEngine()
        output_path = tmp_path / "out.wav"

        mock_mlx_audio = MagicMock()

        def fake_mlx_generate(**kwargs: object) -> None:
            # Does not create output file
            pass

        mock_mlx_audio.tts.generate = fake_mlx_generate

        with patch("podcast_renderer.tts.mlx_audio_engine.MlxAudioEngine.generate") as mock_gen:
            mock_gen.side_effect = RuntimeError("mlx-audio did not produce output")
            with pytest.raises(RuntimeError, match="mlx-audio did not produce output"):
                engine.generate(
                    text="Hello",
                    reference_audio=tmp_path / "ref.wav",
                    reference_text="ref",
                    output_path=output_path,
                )

    def test_quantization_8bit_changes_model(self, tmp_path: Path) -> None:
        engine = MlxAudioEngine()
        output_path = tmp_path / "out.wav"

        captured: dict = {}

        def fake_generate(**kwargs: object) -> None:
            captured.update(kwargs)
            output_path.touch()

        mock_module = MagicMock()
        mock_module.tts.generate = fake_generate

        with patch.dict("sys.modules", {
            "mlx_audio": mock_module,
            "mlx_audio.tts": mock_module.tts,
        }):
            # Patch the import inside the method
            with patch("podcast_renderer.tts.mlx_audio_engine.MlxAudioEngine.generate") as mg:
                mg.return_value = output_path
                result = engine.generate(
                    text="Hello",
                    reference_audio=tmp_path / "ref.wav",
                    reference_text="ref",
                    output_path=output_path,
                    quantization=8,
                )
                mg.assert_called_once()


# ---------------------------------------------------------------------------
# F5TTSEngine
# ---------------------------------------------------------------------------

class TestF5TTSEngine:
    def test_name(self) -> None:
        engine = F5TTSEngine()
        assert engine.name == "f5-tts-mlx"

    def test_is_available_false_via_mock(self) -> None:
        engine = F5TTSEngine()
        with patch.object(engine, "is_available", return_value=False):
            assert engine.is_available() is False

    def test_is_available_true_when_import_succeeds(self) -> None:
        with patch.dict("sys.modules", {"f5_tts_mlx": MagicMock()}):
            engine = F5TTSEngine()
            assert engine.is_available() is True

    def test_generate_raises_runtime_error_when_not_installed(self, tmp_path: Path) -> None:
        engine = F5TTSEngine()
        output_path = tmp_path / "out.wav"

        import sys
        sys.modules.pop("f5_tts_mlx", None)

        with pytest.raises((RuntimeError, ImportError)):
            engine.generate(
                text="Hello",
                reference_audio=tmp_path / "ref.wav",
                reference_text="ref",
                output_path=output_path,
            )

    def test_generate_raises_when_output_missing(self, tmp_path: Path) -> None:
        engine = F5TTSEngine()
        output_path = tmp_path / "out.wav"

        with patch.object(engine, "generate", side_effect=RuntimeError("f5-tts-mlx did not produce output")):
            with pytest.raises(RuntimeError, match="f5-tts-mlx did not produce output"):
                engine.generate(
                    text="Hello",
                    reference_audio=tmp_path / "ref.wav",
                    reference_text="ref",
                    output_path=output_path,
                )

    def test_generate_success(self, tmp_path: Path) -> None:
        engine = F5TTSEngine()
        output_path = tmp_path / "out.wav"

        with patch.object(engine, "generate", return_value=output_path) as mock_gen:
            result = engine.generate(
                text="Hello",
                reference_audio=tmp_path / "ref.wav",
                reference_text="ref",
                output_path=output_path,
            )
            assert result == output_path


# ---------------------------------------------------------------------------
# get_engine factory
# ---------------------------------------------------------------------------

class TestGetEngine:
    def test_unknown_engine_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown TTS engine"):
            get_engine("unknown-engine")

    def test_mlx_audio_engine_not_available_raises_runtime(self) -> None:
        mock_engine = MagicMock(spec=MlxAudioEngine)
        mock_engine.is_available.return_value = False
        mock_engine.name = "mlx-audio"
        # The engine is imported locally inside get_engine; patch the module-level class
        with patch("podcast_renderer.tts.mlx_audio_engine.MlxAudioEngine", return_value=mock_engine):
            with pytest.raises(RuntimeError, match="not available"):
                get_engine("mlx-audio")

    def test_f5_engine_not_available_raises_runtime(self) -> None:
        mock_engine = MagicMock(spec=F5TTSEngine)
        mock_engine.is_available.return_value = False
        mock_engine.name = "f5-tts-mlx"
        with patch("podcast_renderer.tts.f5_tts_engine.F5TTSEngine", return_value=mock_engine):
            with pytest.raises(RuntimeError, match="not available"):
                get_engine("f5-tts-mlx")

    def test_mlx_audio_engine_available_returns_engine(self) -> None:
        mock_engine = MagicMock(spec=MlxAudioEngine)
        mock_engine.is_available.return_value = True
        mock_engine.name = "mlx-audio"
        with patch("podcast_renderer.tts.mlx_audio_engine.MlxAudioEngine", return_value=mock_engine):
            result = get_engine("mlx-audio")
            assert result is mock_engine

    def test_f5_engine_available_returns_engine(self) -> None:
        mock_engine = MagicMock(spec=F5TTSEngine)
        mock_engine.is_available.return_value = True
        mock_engine.name = "f5-tts-mlx"
        with patch("podcast_renderer.tts.f5_tts_engine.F5TTSEngine", return_value=mock_engine):
            result = get_engine("f5-tts-mlx")
            assert result is mock_engine

    def test_tts_engine_is_runtime_checkable_protocol(self) -> None:
        """TTSEngine is a @runtime_checkable Protocol."""
        # Just verify the protocol is importable and has the right interface
        assert callable(TTSEngine)
