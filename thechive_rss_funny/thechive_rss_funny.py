import io
import logging
import re
import textwrap
from datetime import datetime
from xml.etree import ElementTree as ET

import requests
from PIL import Image, ImageOps

from core.plugins import BasePlugin

LOGGER = logging.getLogger(__name__)


class ChiveFunny(BasePlugin):
    """
    InkyPi plugin: show latest image from theCHIVE Funny RSS feed.
    """

    RSS_URL = "https://thechive.com/category/funny/feed/"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_image(self, img: Image.Image, draw, settings: dict) -> Image.Image:
        """
        img: base PIL.Image from InkyPi (already sized to display)
        draw: ImageDraw, if you want to overlay text
        settings: dict from settings.html (unused here, but wired for future)
        """
        try:
            item = self._fetch_latest_item()
            if not item:
                self._draw_error(img, draw, "No items in feed")
                return img

            title = item.get("title", "theCHIVE")
            image_url = item.get("image_url")

            if not image_url:
                self._draw_error(img, draw, "No image URL in item")
                return img

            LOGGER.info("ChiveFunny: using image %s", image_url)
            post_img = self._download_image(image_url)
            if not post_img:
                self._draw_error(img, draw, "Image download failed")
                return img

            # Fit to display while preserving aspect ratio
            post_img = self._fit_to_display(post_img, img.size)

            # Paste centered
            x = (img.size[0] - post_img.size[0]) // 2
            y = (img.size[1] - post_img.size[1]) // 2
            img.paste(post_img, (x, y))

            # Optional: overlay title at bottom
            self._draw_title_bar(img, draw, title)

        except Exception as exc:
            LOGGER.exception("ChiveFunny plugin error: %s", exc)
            self._draw_error(img, draw, "Plugin error")

        return img

    # ------------------------------------------------------------------ #
    # Feed parsing
    # ------------------------------------------------------------------ #

    def _fetch_latest_item(self):
        res = requests.get(self.RSS_URL, timeout=10)
        res.raise_for_status()

        # Parse XML
        root = ET.fromstring(res.content)

        channel = root.find("channel")
        if channel is None:
            # Some feeds namespace channel, handle conservatively
            for child in root:
                if child.tag.endswith("channel"):
                    channel = child
                    break

        if channel is None:
            LOGGER.error("ChiveFunny: channel element not found")
            return None

        item_el = channel.find("item")
        if item_el is None:
            LOGGER.error("ChiveFunny: no item element found")
            return None

        ns = {
            "media": "http://search.yahoo.com/mrss/",
            "dc": "http://purl.org/dc/elements/1.1/",
            "content": "http://purl.org/rss/1.0/modules/content/"
        }

        title_el = item_el.find("title")
        title = title_el.text.strip() if title_el is not None and title_el.text else ""

        # Prefer media:content
        media_content = item_el.find("media:content", ns)
        media_thumb = item_el.find("media:thumbnail", ns)

        image_url = None
        if media_content is not None and "url" in media_content.attrib:
            image_url = media_content.attrib["url"]
        elif media_thumb is not None and "url" in media_thumb.attrib:
            image_url = media_thumb.attrib["url"]
        else:
            # Fallback: parse <description> HTML for first <img src="">
            desc_el = item_el.find("description")
            if desc_el is not None and desc_el.text:
                image_url = self._extract_img_from_html(desc_el.text)

        if not image_url:
            LOGGER.warning("ChiveFunny: no image URL found in latest item")

        return {
            "title": title,
            "image_url": image_url,
        }

    def _extract_img_from_html(self, html: str):
        # Simple regex to find first src="..."
        match = re.search(r'src="([^"]+)"', html)
        if match:
            return match.group(1)
        return None

    # ------------------------------------------------------------------ #
    # Image helpers
    # ------------------------------------------------------------------ #

    def _download_image(self, url: str) -> Image.Image | None:
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            img = Image.open(io.BytesIO(res.content))
            # Convert to RGB, let InkyPi handle palette/convert
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            return img
        except Exception as exc:
            LOGGER.error("ChiveFunny: failed to download image %s: %s", url, exc)
            return None

    def _fit_to_display(self, src_img: Image.Image, target_size):
        tw, th = target_size
        # Contain-fit with letterbox, then crop any padding (preserve aspect)
        img = ImageOps.contain(src_img, (tw, th))
        return img

    # ------------------------------------------------------------------ #
    # UI helpers
    # ------------------------------------------------------------------ #

    def _draw_error(self, img, draw, msg: str):
        w, h = img.size
        text = f"theCHIVE Funny\n{msg}"
        lines = textwrap.wrap(text, width=20)
        total_h = len(lines) * 14
        y = (h - total_h) // 2
        for line in lines:
            lw, lh = draw.textsize(line, font=self.font)
            x = (w - lw) // 2
            draw.text((x, y), line, fill=0, font=self.font)
            y += lh + 2

    def _draw_title_bar(self, img, draw, title: str):
        if not title:
            return
        w, h = img.size
        bar_h = 32

        # Dark bar at bottom
        draw.rectangle([0, h - bar_h, w, h], fill=0)

        # Truncate / wrap title
        max_chars = 40
        if len(title) > max_chars:
            title = title[: max_chars - 1] + "…"

        tw, th = draw.textsize(title, font=self.font_small)
        x = (w - tw) // 2
        y = h - bar_h + (bar_h - th) // 2

        # White text on dark bar
        draw.text((x, y), title, fill=255, font=self.font_small)