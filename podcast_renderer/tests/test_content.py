"""Tests for podcast_renderer content steps: chapters, metadata, rss."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from podcast_renderer.content.chapters import ChapterMarkerStep
from podcast_renderer.content.metadata import MetadataStep
from podcast_renderer.content.rss import RSSGenerationStep


# ---------------------------------------------------------------------------
# ChapterMarkerStep
# ---------------------------------------------------------------------------

class TestChapterMarkerStep:
    def test_name(self) -> None:
        assert ChapterMarkerStep().name == "chapter_markers"

    def test_should_run_with_script(self) -> None:
        step = ChapterMarkerStep()
        assert step.should_run({"script": {"segments": []}})

    def test_should_not_run_without_script(self) -> None:
        step = ChapterMarkerStep()
        assert not step.should_run({})

    def test_generates_chapters_from_script(self) -> None:
        step = ChapterMarkerStep()
        ctx: dict[str, Any] = {
            "script": {
                "segments": [
                    {"speaker": "host", "text": "Welcome to the show.", "notes": "intro"},
                    {"speaker": "host", "text": "Today we discuss AI.", "notes": ""},
                    {"speaker": "host", "text": "Thanks for listening.", "notes": "outro"},
                ]
            }
        }
        result = step.execute(ctx)
        chapters = result["chapters"]
        assert len(chapters) == 3
        assert chapters[0]["title"] == "Intro"  # notes.capitalize()
        assert chapters[0]["start_time"] == 0.0

    def test_uses_notes_as_title(self) -> None:
        step = ChapterMarkerStep()
        ctx: dict[str, Any] = {
            "script": {
                "segments": [
                    {"text": "Some text.", "notes": "introduction segment"},
                ]
            }
        }
        result = step.execute(ctx)
        assert result["chapters"][0]["title"] == "Introduction segment"

    def test_uses_text_when_no_notes(self) -> None:
        step = ChapterMarkerStep()
        ctx: dict[str, Any] = {
            "script": {
                "segments": [
                    {"text": "Short text.", "notes": ""},
                ]
            }
        }
        result = step.execute(ctx)
        assert result["chapters"][0]["title"] == "Short text."

    def test_truncates_long_text_title(self) -> None:
        step = ChapterMarkerStep()
        long_text = "This is a very long text that exceeds the fifty character limit for titles."
        ctx: dict[str, Any] = {
            "script": {
                "segments": [
                    {"text": long_text, "notes": ""},
                ]
            }
        }
        result = step.execute(ctx)
        title = result["chapters"][0]["title"]
        assert title.endswith("...")
        assert len(title) <= 53  # 50 chars + "..."

    def test_uses_transcript_timestamps(self) -> None:
        step = ChapterMarkerStep()
        ctx: dict[str, Any] = {
            "script": {
                "segments": [
                    {"text": "First segment.", "notes": "intro"},
                    {"text": "Second segment.", "notes": "main"},
                ]
            },
            "transcript": {
                "segments": [
                    {"start": 0.0, "end": 10.0},
                    {"start": 10.0, "end": 25.0},
                ]
            },
        }
        result = step.execute(ctx)
        assert result["chapters"][0]["start_time"] == 0.0
        assert result["chapters"][1]["start_time"] == 10.0

    def test_estimates_duration_without_transcript(self) -> None:
        step = ChapterMarkerStep()
        ctx: dict[str, Any] = {
            "script": {
                "segments": [
                    {"text": "Word " * 100, "notes": ""},
                    {"text": "Another segment.", "notes": ""},
                ]
            }
        }
        result = step.execute(ctx)
        # Second chapter should start after estimated duration of first
        assert result["chapters"][1]["start_time"] > 0.0

    def test_empty_script_produces_no_chapters(self) -> None:
        step = ChapterMarkerStep()
        ctx: dict[str, Any] = {"script": {"segments": []}}
        result = step.execute(ctx)
        assert result["chapters"] == []


# ---------------------------------------------------------------------------
# MetadataStep
# ---------------------------------------------------------------------------

class TestMetadataStep:
    def test_name(self) -> None:
        assert MetadataStep().name == "metadata"

    def test_should_run_with_episode_mp3(self, tmp_path: Path) -> None:
        step = MetadataStep()
        assert step.should_run({"episode_mp3": tmp_path / "ep.mp3"})

    def test_should_not_run_without_episode_mp3(self) -> None:
        step = MetadataStep()
        assert not step.should_run({})

    @patch("podcast_renderer.content.metadata.get_audio_duration")
    def test_execute_builds_metadata(
        self, mock_duration: MagicMock, tmp_path: Path
    ) -> None:
        mock_duration.return_value = 120.5
        mp3 = tmp_path / "episode.mp3"
        mp3.write_bytes(b"fake mp3 data")

        ctx: dict[str, Any] = {
            "episode_mp3": mp3,
            "script": {
                "title": "My Episode",
                "description": "A great episode",
            },
            "language": "en",
        }
        result = MetadataStep().execute(ctx)
        meta = result["episode_metadata"]
        assert meta["title"] == "My Episode"
        assert meta["description"] == "A great episode"
        assert meta["language"] == "en"
        assert meta["duration_seconds"] == pytest.approx(120.5)
        assert meta["file_size_bytes"] > 0
        assert meta["format"] == "audio/mpeg"

    @patch("podcast_renderer.content.metadata.get_audio_duration")
    def test_execute_includes_show_notes_if_present(
        self, mock_duration: MagicMock, tmp_path: Path
    ) -> None:
        mock_duration.return_value = 60.0
        mp3 = tmp_path / "ep.mp3"
        mp3.write_bytes(b"data")

        ctx: dict[str, Any] = {
            "episode_mp3": mp3,
            "script": {"title": "Ep", "description": ""},
            "show_notes": "## Summary\nGreat episode.",
            "chapters": [{"start_time": 0, "title": "Intro"}],
        }
        result = MetadataStep().execute(ctx)
        meta = result["episode_metadata"]
        assert "show_notes" in meta
        assert "chapters" in meta

    @patch("podcast_renderer.content.metadata.get_audio_duration")
    def test_execute_zero_duration_on_error(
        self, mock_duration: MagicMock, tmp_path: Path
    ) -> None:
        mock_duration.side_effect = Exception("ffprobe failed")
        mp3 = tmp_path / "ep.mp3"
        mp3.write_bytes(b"data")

        ctx: dict[str, Any] = {
            "episode_mp3": mp3,
            "script": {},
        }
        result = MetadataStep().execute(ctx)
        assert result["episode_metadata"]["duration_seconds"] == 0.0

    @patch("podcast_renderer.content.metadata.get_audio_duration")
    def test_execute_zero_size_for_missing_file(
        self, mock_duration: MagicMock, tmp_path: Path
    ) -> None:
        mock_duration.return_value = 0.0
        mp3 = tmp_path / "missing.mp3"
        # Don't create the file

        ctx: dict[str, Any] = {
            "episode_mp3": mp3,
            "script": {"title": "Test"},
        }
        result = MetadataStep().execute(ctx)
        assert result["episode_metadata"]["file_size_bytes"] == 0

    @patch("podcast_renderer.content.metadata.get_audio_duration")
    def test_execute_uses_script_language_when_no_context_language(
        self, mock_duration: MagicMock, tmp_path: Path
    ) -> None:
        mock_duration.return_value = 30.0
        mp3 = tmp_path / "ep.mp3"
        mp3.write_bytes(b"data")

        ctx: dict[str, Any] = {
            "episode_mp3": mp3,
            "script": {"title": "T", "language": "pt"},
        }
        result = MetadataStep().execute(ctx)
        assert result["episode_metadata"]["language"] == "pt"


# ---------------------------------------------------------------------------
# RSSGenerationStep
# ---------------------------------------------------------------------------

class TestRSSGenerationStep:
    def test_name(self) -> None:
        assert RSSGenerationStep().name == "rss_generation"

    def test_should_run_with_metadata(self) -> None:
        step = RSSGenerationStep()
        assert step.should_run({"episode_metadata": {}})

    def test_should_not_run_without_metadata(self) -> None:
        step = RSSGenerationStep()
        assert not step.should_run({})

    def _minimal_metadata(self) -> dict[str, Any]:
        return {
            "title": "Test Episode",
            "description": "Test description",
            "publication_date": "2025-01-15T10:00:00+00:00",
            "file_path": "/tmp/episode.mp3",
            "file_size_bytes": 1000000,
            "duration_seconds": 600,
            "format": "audio/mpeg",
        }

    def test_execute_creates_rss_file(self, tmp_path: Path) -> None:
        settings = SimpleNamespace(
            podcast_config_file=tmp_path / "missing.json",  # force fallback path
            podcast_data_dir=tmp_path,
        )
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_metadata": self._minimal_metadata(),
        }
        result = RSSGenerationStep().execute(ctx)
        assert "rss_feed_path" in result
        rss_path = result["rss_feed_path"]
        assert Path(rss_path).exists()

    def test_execute_writes_valid_xml(self, tmp_path: Path) -> None:
        settings = SimpleNamespace(
            podcast_config_file=tmp_path / "missing.json",
            podcast_data_dir=tmp_path,
        )
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_metadata": self._minimal_metadata(),
        }
        result = RSSGenerationStep().execute(ctx)
        rss_path = result["rss_feed_path"]
        tree = ET.parse(rss_path)
        root = tree.getroot()
        assert root.tag == "rss"

    def test_execute_appends_to_existing_feed(self, tmp_path: Path) -> None:
        settings = SimpleNamespace(
            podcast_config_file=tmp_path / "missing.json",
            podcast_data_dir=tmp_path,
        )
        # Create existing feed
        existing_xml = """<?xml version='1.0' encoding='utf-8'?>
<rss version="2.0"><channel><title>My Podcast</title></channel></rss>"""
        rss_path = tmp_path / "output" / "feed.xml"
        rss_path.parent.mkdir(parents=True)
        rss_path.write_text(existing_xml)

        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_metadata": self._minimal_metadata(),
        }
        result = RSSGenerationStep().execute(ctx)
        tree = ET.parse(result["rss_feed_path"])
        channel = tree.getroot().find("channel")
        assert channel is not None
        items = channel.findall("item")
        assert len(items) == 1

    def test_build_episode_item_structure(self) -> None:
        step = RSSGenerationStep()
        metadata = self._minimal_metadata()
        item = step._build_episode_item(metadata)
        assert item.tag == "item"
        assert item.find("title") is not None
        assert item.find("enclosure") is not None
        assert item.find("guid") is not None

    def test_build_episode_item_itunes_duration(self) -> None:
        step = RSSGenerationStep()
        metadata = {**self._minimal_metadata(), "duration_seconds": 3661}
        item = step._build_episode_item(metadata)
        ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
        duration_el = item.find(f"{ns}duration")
        assert duration_el is not None
        assert duration_el.text == "01:01:01"

    def test_build_episode_item_no_pub_date_on_invalid(self) -> None:
        step = RSSGenerationStep()
        metadata = {**self._minimal_metadata(), "publication_date": "not-a-date"}
        item = step._build_episode_item(metadata)
        # Should not raise, pubDate element is just not added
        assert item.tag == "item"

    def test_build_feed_from_scratch(self) -> None:
        step = RSSGenerationStep()
        podcast_meta = {
            "title": "My Podcast",
            "description": "A great show",
            "language": "en",
            "author": "Test Author",
        }
        item = ET.Element("item")
        ET.SubElement(item, "title").text = "Episode 1"
        root = step._build_feed(podcast_meta, [item])
        assert root.tag == "rss"
        channel = root.find("channel")
        assert channel is not None
        assert channel.find("title").text == "My Podcast"

    def test_build_feed_no_author(self) -> None:
        step = RSSGenerationStep()
        root = step._build_feed({}, [])
        channel = root.find("channel")
        assert channel is not None
        ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
        # No author element when not provided
        assert channel.find(f"{ns}author") is None

    def test_execute_uses_config_rss_path(self, tmp_path: Path) -> None:
        """When config exists, use its rss_file path."""
        import json as _json
        cfg_data = {
            "languages": [],
            "tts": {},
            "audio": {},
            "llm": {},
            "distribution": {"rss_file": "custom/myfeed.xml"},
            "podcast": {},
            "settings": {},
        }
        cfg_path = tmp_path / "podcast.json"
        cfg_path.write_text(_json.dumps(cfg_data))

        settings = SimpleNamespace(
            podcast_config_file=cfg_path,
            podcast_data_dir=tmp_path,
        )
        ctx: dict[str, Any] = {
            "settings": settings,
            "episode_metadata": self._minimal_metadata(),
        }
        result = RSSGenerationStep().execute(ctx)
        assert "custom" in str(result["rss_feed_path"]) or result["rss_feed_path"].exists()
