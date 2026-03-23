"""RSS feed generation step — create/update podcast RSS feed.

Generates a podcast RSS feed from episode metadata using the
configured RSS template. Stateless approach: regenerates the
full feed from metadata files each time.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from typing import Any

from podcast_renderer.config import PodcastConfig

logger = logging.getLogger(__name__)


class RSSGenerationStep:
    """Generate or update the podcast RSS feed.

    Context in:  episode_metadata (dict), settings
    Context out: rss_feed_path (Path)
    """

    name = "rss_generation"

    def should_run(self, context: dict[str, Any]) -> bool:
        return "episode_metadata" in context

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        settings = context.get("settings")
        metadata = context["episode_metadata"]

        try:
            config = PodcastConfig(settings.podcast_config_file)
            dist = config.distribution
            podcast_meta = config.podcast_metadata
        except Exception:
            dist = {"rss_file": "output/feed.xml"}
            podcast_meta = {}

        rss_path = Path(dist.get("rss_file", "output/feed.xml"))
        rss_path.parent.mkdir(parents=True, exist_ok=True)

        # Build the episode item XML
        episode_item = self._build_episode_item(metadata)

        # Load or create the feed
        if rss_path.exists():
            tree = ET.parse(rss_path)
            root = tree.getroot()
            channel = root.find("channel")
            if channel is not None:
                channel.append(episode_item)
        else:
            root = self._build_feed(podcast_meta, [episode_item])

        # Write feed
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(rss_path, encoding="unicode", xml_declaration=True)

        context["rss_feed_path"] = rss_path
        logger.info("RSS feed updated: %s", rss_path)
        return context

    def _build_episode_item(self, metadata: dict[str, Any]) -> ET.Element:
        """Build an RSS <item> element for an episode."""
        item = ET.Element("item")

        ET.SubElement(item, "title").text = metadata.get("title", "Untitled")
        ET.SubElement(item, "description").text = metadata.get("description", "")

        # Publication date
        pub_date = metadata.get("publication_date", "")
        if pub_date:
            try:
                dt = datetime.fromisoformat(pub_date)
                ET.SubElement(item, "pubDate").text = format_datetime(dt)
            except ValueError:
                pass

        # Enclosure (audio file)
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", metadata.get("file_path", ""))
        enclosure.set("length", str(metadata.get("file_size_bytes", 0)))
        enclosure.set("type", metadata.get("format", "audio/mpeg"))

        # iTunes duration
        duration = metadata.get("duration_seconds", 0)
        if duration:
            minutes, seconds = divmod(int(duration), 60)
            hours, minutes = divmod(minutes, 60)
            ET.SubElement(
                item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}duration"
            ).text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # GUID
        ET.SubElement(item, "guid").text = metadata.get("title", "untitled")

        return item

    def _build_feed(
        self, podcast_meta: dict[str, Any], items: list[ET.Element]
    ) -> ET.Element:
        """Build a new RSS feed from scratch."""
        rss = ET.Element("rss", version="2.0")
        rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")

        channel = ET.SubElement(rss, "channel")
        ET.SubElement(channel, "title").text = podcast_meta.get("title", "My Podcast")
        ET.SubElement(channel, "description").text = podcast_meta.get("description", "")
        ET.SubElement(channel, "language").text = podcast_meta.get("language", "en")

        author = podcast_meta.get("author", "")
        if author:
            ET.SubElement(
                channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}author"
            ).text = author

        for item in items:
            channel.append(item)

        return rss
