import io
import logging
import re
import textwrap
from typing import Optional
from xml.etree import ElementTree as ET

import requests
from PIL import Image, ImageDraw, ImageOps

from plugins.base_plugin.base_plugin import BasePlugin

LOGGER = logging.getLogger(__name__)


class ChiveFunny(BasePlugin):
    RSS_URL = "https://thechive.com/category/funny/feed/"

    def __init__(self, config):
        super().__init__(config)

    def generate_image(self, settings, device_config, inky_display):
        width = getattr(device_config, "width", 800)
        height = getattr(device_config, "height", 480)

        try:
            item = self._fetch_latest_item()
            if not item:
                return self._build_error_image(width, height, "No items in feed")

            title = item.get("title", "theCHIVE")
            image_url = item.get("image_url")

            if not image_url:
                return self._build_error_image(width, height, "No image URL in item")

            LOGGER.info("ChiveFunny: using image %s", image_url)

            post_img = self._download_image(image_url)
            if not post_img:
                return self._build_error_image(width, height, "Image download failed")

            canvas = Image.new("RGB", (width, height), "white")

            title_bar_height = 32
            fitted = self._fit_to_display(post_img, (width, height - title_bar_height))
            x = (width - fitted.size[0]) // 2
            y = ((height - title_bar_height) - fitted.size[1]) // 2
            canvas.paste(fitted, (x, max(0, y)))

            self._draw_title_bar(canvas, title)

            return canvas

        except Exception as exc:
            LOGGER.exception("ChiveFunny plugin error: %s", exc)
            return self._build_error_image(width, height, "Plugin error")

    def _fetch_latest_item(self):
        response = requests.get(self.RSS_URL, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; InkyPi theCHIVE RSS)"
        })
        response.raise_for_status()

        root = ET.fromstring(response.content)

        channel = root.find("channel")
        if channel is None:
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

        namespaces = {
            "media": "http://search.yahoo.com/mrss/",
            "dc": "http://purl.org/dc/elements/1.1/",
            "content": "http://purl.org/rss/1.0/modules/content/",
        }

        title_el = item_el.find("title")
        title = title_el.text.strip() if title_el is not None and title_el.text else ""

        image_url = None

        media_content = item_el.find("media:content", namespaces)
        if media_content is not None and media_content.attrib.get("url"):
            image_url = media_content.attrib["url"]

        if not image_url:
            media_thumb = item_el.find("media:thumbnail", namespaces)
            if media_thumb is not None and media_thumb.attrib.get("url"):
                image_url = media_thumb.attrib["url"]

        if not image_url:
            desc_el = item_el.find("description")
            if desc_el is not None and desc_el.text:
                image_url = self._extract_img_from_html(desc_el.text)

        if image_url:
            image_url = image_url.replace("&#038;", "&").replace("&amp;", "&")

        return {
            "title": title,
            "image_url": image_url,
        }

    def _extract_img_from_html(self, html):
        match = re.search(r'src="([^"]+)"', html)
        if match:
            return match.group(1)
        return None

    def _download_image(self, url) -> Optional[Image.Image]:
        try:
            response = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (compatible; InkyPi theCHIVE RSS)"
            })
            response.raise_for_status()

            img = Image.open(io.BytesIO(response.content))

            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, "white")
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            return img

        except Exception as exc:
            LOGGER.error("ChiveFunny: failed to download image %s: %s", url, exc)
            return None

    def _fit_to_display(self, src_img, target_size):
        return ImageOps.contain(src_img, target_size)

    def _build_error_image(self, width, height, message):
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)

        text = "theCHIVE Funny\n%s" % message
        lines = textwrap.wrap(text, width=24)

        y = max(20, (height // 2) - (len(lines) * 12))
        for line in lines:
            draw.text((20, y), line, fill="black")
            y += 20

        return img

    def _draw_title_bar(self, img, title):
        draw = ImageDraw.Draw(img)
        width, height = img.size
        bar_height = 32

        draw.rectangle([0, height - bar_height, width, height], fill="black")

        max_chars = 50
        if len(title) > max_chars:
            title = title[:max_chars - 3] + "..."

        draw.text((10, height - 24), title, fill="white")