# -*- coding: utf-8 -*-

"""Chevereto upload plugin for pibooth.

Uploads each completed capture to a Chevereto gallery via its HTTP API
and maintains a filesystem-based retry queue (``.pending`` / ``.uploaded``
markers) so a failed upload is never lost.

Two entry points ship together:

- a pibooth plugin (registered via setuptools entry point) that fires
  on ``state_processing_exit`` and attempts ONE fast sync upload so the
  on-screen QR code is populated before the user walks away;
- a standalone ``pibooth-chevereto`` console script (intended to be run
  from a systemd timer) that drains leftover ``.pending`` markers.

See :mod:`pibooth.plugins.chevereto.plugin` for the hook implementation
and :mod:`pibooth.plugins.chevereto.uploader` for the drainer CLI.

Configuration is env-var driven so secrets live outside the repo:

    CHEVERETO_API_KEY           required
    CHEVERETO_API_URL           required — full POST URL for the Chevereto upload endpoint
    CHEVERETO_SLUG              used in the generated image name / title (default "Pibooth")
    CHEVERETO_TITLE_TEMPLATE    f-string-style template, {slug}/{pretty_date} (has default)
    CHEVERETO_DESCRIPTION_TEMPLATE   same placeholders (has default)
    CHEVERETO_SYNC_TIMEOUT      plugin sync-upload timeout in seconds (default 8)
    CHEVERETO_UPLOAD_TIMEOUT    drainer per-attempt timeout in seconds (default 30)
    CHEVERETO_MIN_AGE_SEC       drainer skip-too-fresh threshold (default 10)
    CHEVERETO_CAPTURES_DIR      drainer scan directory (required for the drainer)
"""

__version__ = "0.1.0"
