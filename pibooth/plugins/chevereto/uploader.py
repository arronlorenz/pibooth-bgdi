# -*- coding: utf-8 -*-

"""``pibooth-chevereto`` — drain pending Chevereto uploads.

Scans ``CHEVERETO_CAPTURES_DIR`` for ``*.pending`` markers left by the
sync-upload plugin when it couldn't reach the gallery. POSTs each file
to Chevereto; on success writes ``<capture>.uploaded`` (containing the
returned URL) and removes ``<capture>.pending``. On failure leaves
``.pending`` in place — the next timer fire will try again.

Designed to be invoked from a systemd timer; does nothing if there are
no pendings. Reads env-var configuration — see the package docstring
in :mod:`pibooth.plugins.chevereto`.

The scan is **non-recursive** — ``CHEVERETO_CAPTURES_DIR`` must be the
flat directory pibooth writes into.
"""

import glob
import logging
import os
import sys
import time

from pibooth.plugins.chevereto import core


def _int_env(name, default, log):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        log.warning("ignoring malformed %s=%r; using default %d", name, raw, default)
        return default


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s pibooth-chevereto %(levelname)s %(message)s",
    )
    log = logging.getLogger("pibooth-chevereto")

    api_url = os.environ.get("CHEVERETO_API_URL")
    api_key = os.environ.get("CHEVERETO_API_KEY")
    captures_dir = os.environ.get("CHEVERETO_CAPTURES_DIR") or os.environ.get("CAPTURES_DIR")
    upload_timeout = _int_env("CHEVERETO_UPLOAD_TIMEOUT", 30, log)
    min_age_sec = _int_env("CHEVERETO_MIN_AGE_SEC", 10, log)
    slug = os.environ.get("CHEVERETO_SLUG", core.SLUG_DEFAULT)
    title_template = os.environ.get("CHEVERETO_TITLE_TEMPLATE", core.TITLE_TEMPLATE_DEFAULT)
    description_template = os.environ.get("CHEVERETO_DESCRIPTION_TEMPLATE",
                                          core.DESCRIPTION_TEMPLATE_DEFAULT)

    if not api_key or not api_url:
        log.error("CHEVERETO_API_KEY / CHEVERETO_API_URL not set; exiting")
        return 2
    if not captures_dir:
        log.error("CHEVERETO_CAPTURES_DIR not set; exiting")
        return 2
    if not os.path.isdir(captures_dir):
        log.error("CHEVERETO_CAPTURES_DIR not found: %s", captures_dir)
        return 2

    pendings = sorted(glob.glob(os.path.join(captures_dir, "*.pending")))
    if not pendings:
        log.debug("nothing pending")
        return 0

    log.info("%d pending upload(s)", len(pendings))
    succ = 0
    for p in pendings:
        try:
            if _process_one(p, api_url, api_key, upload_timeout, min_age_sec,
                            slug, title_template, description_template, log) is not None:
                succ += 1
        except Exception as exc:
            log.exception("unhandled error on %s: %s", p, exc)
    # Re-count what's actually left so a concurrent drain (or the sync
    # plugin racing us) doesn't produce a negative-looking "left pending".
    remaining = len(glob.glob(os.path.join(captures_dir, "*.pending")))
    log.info("done: %d succeeded, %d left pending", succ, remaining)
    return 0


def _process_one(pending_file, api_url, api_key, upload_timeout, min_age_sec,
                 slug, title_template, description_template, log):
    """Return the uploaded URL, or None on failure/skip."""
    jpg = pending_file[: -len(".pending")]

    # Skip if the plugin already uploaded it after writing .pending.
    if os.path.exists(core.uploaded_path(jpg)):
        log.info("already uploaded, cleaning marker: %s", jpg)
        try:
            os.remove(pending_file)
        except FileNotFoundError:
            pass
        return None

    # Orphaned marker (JPG deleted/moved): clean up.
    if not os.path.exists(jpg):
        log.warning("orphan pending marker (no JPG), removing: %s", pending_file)
        try:
            os.remove(pending_file)
        except FileNotFoundError:
            pass
        return None

    # Don't race with the plugin's sync attempt on very new files. If
    # stat fails (file vanished between glob and getmtime), treat that
    # as "skip this round"; we'll be re-invoked on the next timer tick.
    # Previously this fell through to upload, opening a tiny window for
    # a double-POST.
    try:
        age = time.time() - os.path.getmtime(pending_file)
    except OSError as exc:
        log.warning("could not stat %s: %s — skip this round", pending_file, exc)
        return None
    if age < min_age_sec:
        log.info("skip, too fresh (%.0fs < %ds): %s", age, min_age_sec, jpg)
        return None

    log.info("uploading %s", jpg)
    try:
        url = core.upload(jpg, api_url, api_key, upload_timeout,
                          slug=slug, title_template=title_template,
                          description_template=description_template)
    except Exception as exc:
        log.warning("upload failed for %s: %s (will retry)", jpg, exc)
        return None

    core.mark_uploaded(jpg, url)
    log.info("upload OK: %s -> %s", jpg, url)
    return url


if __name__ == "__main__":
    sys.exit(main())
