"""Tests for the text segmentation step."""

from __future__ import annotations

from typing import Any

import pytest

from pipeline_runner.steps.segment import TextSegmentationStep, split_text_into_chunks


class TestSplitTextIntoChunks:
    """Test the split_text_into_chunks utility function."""

    def test_short_text_single_chunk(self) -> None:
        result = split_text_into_chunks("Hello world.", 200)
        assert result == ["Hello world."]

    def test_empty_text(self) -> None:
        result = split_text_into_chunks("", 200)
        assert result == [""]

    def test_split_at_sentence_boundary(self) -> None:
        text = "First sentence. Second sentence. Third sentence."
        result = split_text_into_chunks(text, 35)
        assert len(result) >= 2
        # Each chunk should end at a sentence boundary
        for chunk in result:
            assert len(chunk) <= 35 or "." in chunk

    def test_respects_max_chars(self) -> None:
        text = "This is a short sentence. " * 20
        result = split_text_into_chunks(text.strip(), 100)
        for chunk in result:
            assert len(chunk) <= 100

    def test_long_sentence_force_split(self) -> None:
        # A single sentence longer than max_chars
        text = "word " * 50  # ~250 chars
        result = split_text_into_chunks(text.strip(), 100)
        assert len(result) >= 2
        for chunk in result:
            assert len(chunk) <= 100

    def test_preserves_content(self) -> None:
        text = "First sentence. Second sentence. Third sentence."
        chunks = split_text_into_chunks(text, 200)
        recombined = " ".join(chunks)
        assert recombined == text

    def test_question_marks(self) -> None:
        text = "What is AI? It's complex. How does it work?"
        result = split_text_into_chunks(text, 25)
        assert len(result) >= 2

    def test_exclamation_marks(self) -> None:
        text = "Amazing! Incredible! Wonderful!"
        result = split_text_into_chunks(text, 20)
        assert len(result) >= 2

    def test_exact_limit(self) -> None:
        text = "Hello world."
        result = split_text_into_chunks(text, 12)
        assert result == ["Hello world."]


class TestTextSegmentationStep:
    """Test the TextSegmentationStep pipeline step."""

    def test_should_run_with_script(self) -> None:
        step = TextSegmentationStep()
        assert step.should_run({"script": {"segments": []}})

    def test_should_not_run_without_script(self) -> None:
        step = TextSegmentationStep()
        assert not step.should_run({})

    def test_segments_get_chunks(self, test_settings: Any) -> None:
        step = TextSegmentationStep()
        context = {
            "settings": test_settings,
            "script": {
                "segments": [
                    {"speaker": "host", "text": "Short text.", "notes": ""},
                    {"speaker": "host", "text": "Another short text.", "notes": ""},
                ],
            },
        }
        result = step.execute(context)
        for segment in result["script"]["segments"]:
            assert "chunks" in segment
            assert len(segment["chunks"]) >= 1

    def test_long_segment_splits(self, test_settings: Any) -> None:
        step = TextSegmentationStep()
        long_text = "This is a sentence about AI. " * 20  # ~580 chars
        context = {
            "settings": test_settings,
            "script": {
                "segments": [
                    {"speaker": "host", "text": long_text.strip(), "notes": ""},
                ],
            },
        }
        result = step.execute(context)
        chunks = result["script"]["segments"][0]["chunks"]
        assert len(chunks) > 1

    def test_name(self) -> None:
        assert TextSegmentationStep().name == "text_segmentation"
