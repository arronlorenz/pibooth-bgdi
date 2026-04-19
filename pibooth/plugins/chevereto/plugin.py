# -*- coding: utf-8 -*-

"""pibooth hookimpl — sync upload at capture time.

Workflow per completed capture:

1. write the ``.pending`` marker
2. try ONE fast upload (bounded by ``CHEVERETO_SYNC_TIMEOUT``) so the
   QR code on screen can point at the live image before the user
   walks away
3. on success: set ``app.previous_picture_url`` (for pibooth-qrcode),
   then write ``.uploaded`` and drop ``.pending``
4. on failure: leave ``.pending`` for the drainer (``pibooth-chevereto``,
   fired by its systemd timer) to retry later

Reads configuration from environment variables — see the package
docstring in :mod:`pibooth.plugins.chevereto`.
"""

import datetime as dt
import os

import pibooth
from pibooth.utils import LOGGER

from pibooth.plugins.chevereto import core

API_URL = os.getenv("CHEVERETO_API_URL")
API_KEY = os.getenv("CHEVERETO_API_KEY")
SLUG = os.getenv("CHEVERETO_SLUG", core.SLUG_DEFAULT)
TITLE_TEMPLATE = os.getenv("CHEVERETO_TITLE_TEMPLATE", core.TITLE_TEMPLATE_DEFAULT)
DESCRIPTION_TEMPLATE = os.getenv("CHEVERETO_DESCRIPTION_TEMPLATE", core.DESCRIPTION_TEMPLATE_DEFAULT)


def _int_env(name, default):
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        LOGGER.warning("ignoring malformed %s=%r; using default %d", name, raw, default)
        return default


# Parsed lazily at module-level but safely — a malformed env var must
# not prevent pibooth from starting.
SYNC_TIMEOUT = _int_env("CHEVERETO_SYNC_TIMEOUT", 8)


@pibooth.hookimpl
def state_processing_exit(app):
    """Run right after the final picture is written on disk."""
    if not API_KEY or not API_URL:
        LOGGER.error("CHEVERETO_API_KEY / CHEVERETO_API_URL not set; skip upload")
        return

    filepath = app.previous_picture_file
    if not filepath:
        LOGGER.debug("state_processing_exit fired without a capture; nothing to upload")
        return

    # If something already uploaded this file (e.g. the drainer beat us
    # to it after a prior failure), reuse the stored URL.
    if os.path.exists(core.uploaded_path(filepath)):
        try:
            with open(core.uploaded_path(filepath)) as f:
                app.previous_picture_url = f.read().strip()
            LOGGER.info("Already uploaded; reusing URL for %s", filepath)
            return
        except OSError:
            pass  # fall through and re-upload

    # Mark as owed — drainer will pick it up if we fail below.
    try:
        with open(core.pending_path(filepath), "w") as f:
            f.write(str(dt.datetime.now()))
    except OSError as exc:
        LOGGER.warning("Could not write pending marker for %s: %s", filepath, exc)

    LOGGER.info("Uploading %s to Chevereto (sync, %ds timeout)…", filepath, SYNC_TIMEOUT)
    try:
        url = core.upload(filepath, API_URL, API_KEY, SYNC_TIMEOUT,
                          slug=SLUG, title_template=TITLE_TEMPLATE,
                          description_template=DESCRIPTION_TEMPLATE)
    except Exception as exc:
        LOGGER.warning("Sync upload failed for %s: %s — drainer will retry",
                       filepath, exc)
        return

    # Set the QR URL before persisting the .uploaded marker: if the
    # marker write fails (e.g. disk full), the upload itself still
    # succeeded, so the QR should still point at the live image.
    app.previous_picture_url = url
    try:
        core.mark_uploaded(filepath, url)
    except OSError as exc:
        LOGGER.warning("Upload OK but could not write .uploaded marker for %s: %s",
                       filepath, exc)
    LOGGER.info("Upload OK: %s", url)
