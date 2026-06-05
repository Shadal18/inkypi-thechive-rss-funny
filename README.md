# InkyPi theCHIVE Funny RSS

A custom InkyPi plugin that shows the latest funny image from theCHIVE “Funny” RSS feed on your Inky e‑paper display.

## Install

Use the InkyPi plugin installer with the plugin ID and this repository URL, following the install pattern shown by the official InkyPi plugin template.

```bash
inkypi plugin install inkypi-thechive-rss-funny https://github.com/shadal18/inkypi-thechive-rss-funny
```

## Update

To update the plugin on your InkyPi device:

1. SSH into your InkyPi host.
2. Change into the plugin directory:

   ```bash
   cd ~/InkyPi/src/plugins/thechive_rss_funny
   ```

3. Run this update command:

   ```bash
   git pull origin main && \
   if [ -d thechive_rss_funny ]; then \
     rsync -a thechive_rss_funny/ ./ && \
     rm -rf thechive_rss_funny; \
   fi && \
   sudo systemctl restart inkypi.service
   ```

If you don’t see your changes after updating:

- Confirm you are in the correct plugin folder.
- Clear your browser cache or hard refresh the InkyPi web UI.
- Check the InkyPi logs for any plugin errors.

## Requirements

- Network access from the InkyPi device to `thechive.com` over HTTPS.

## Features

This plugin is an extension for the InkyPi e‑paper display frame and includes the following features.

- Fetches the latest post from theCHIVE “Funny” RSS feed.
- Extracts the primary image using `<media:content>` / `<media:thumbnail>` when available.
- Falls back to parsing the `<description>` HTML for the first `<img>` if media tags are missing.
- Downloads and scales the image to fit the InkyPi display while preserving aspect ratio.
- Centers the image on the display.
- Graceful error handling with on‑screen error messages instead of blank or crashed displays.

## Details

The plugin queries theCHIVE “Funny” RSS feed and parses the latest `<item>` entry to find an appropriate image URL.  
It prefers `<media:content>` and `<media:thumbnail>` fields, which are part of the media namespace used by the feed, and will fall back to extracting the first `src="..."` from the `<description>` HTML when needed.  
Once the image URL is found, the plugin downloads the image, converts it to a display‑friendly format, scales it to fit the InkyPi display, and renders it centered with an optional title bar overlay containing the post title.

## Repository

GitHub repository:

```text
https://github.com/shadal18/inkypi-thechive-rss-funny
```

## Screenshots

- Main plugin display showing the latest funny image from theCHIVE.

```text
screenshots/example.png
```
