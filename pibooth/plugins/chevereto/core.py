# -*- coding: utf-8 -*-

"""Shared helpers for uploading captures to Chevereto.

Used by both the pibooth plugin (sync, at capture time) and the
``pibooth-chevereto`` drainer (async, fired by a systemd timer).

Single source of truth for SEO field formatting, the upload POST, and
the ``.pending`` / ``.uploaded`` marker semantics.
"""

import datetime as dt
import logging
import os

import requests

from pibooth.plugins.chevereto import __version__

LOGGER = logging.getLogger("pibooth")
USER_AGENT = "pibooth-chevereto/{}".format(__version__)

SLUG_DEFAULT = "Pibooth"
TITLE_TEMPLATE_DEFAULT = "{slug} Photo Booth Snapshot – {pretty_date}"
DESCRIPTION_TEMPLATE_DEFAULT = (
    "A candid snapshot captured at the {slug} photo booth. "
    "Enjoy the moment from {pretty_date}."
)

# Templates with bad placeholders ({date} instead of {pretty_date}, …)
# raise KeyError on .format(); without this guard the sync plugin would
# leave .pending and the drainer would hit the same KeyError forever,
# silently filling the disk. Fall back to the default and log once per
# offending template so the operator notices on the first capture
# without every subsequent capture re-spamming the journal.
_warned_templates = set()


def _safe_format(template, default, **fields):
    try:
        return template.format(**fields)
    except KeyError as exc:
        if template not in _warned_templates:
            _warned_templates.add(template)
            LOGGER.warning(
                "Chevereto template %r references unknown placeholder %s; "
                "falling back to default. Valid placeholders: %s",
                template, exc, sorted(fields))
        return default.format(**fields)


def pending_path(filepath):
    return filepath + ".pending"


def uploaded_path(filepath):
    return filepath + ".uploaded"


def seo_fields(filepath, slug=SLUG_DEFAULT,
               title_template=TITLE_TEMPLATE_DEFAULT,
               description_template=DESCRIPTION_TEMPLATE_DEFAULT):
    """Return (name, title, description) for a pibooth capture path.

    pibooth filenames are ``YYYY-MM-DD-HH-MM-SS_pibooth.jpg``. When the
    timestamp prefix is unparseable we fall back to "now" so the upload
    still lands with non-empty metadata.
    """
    stamp = os.path.basename(filepath).split("_")[0]
    try:
        ts = dt.datetime.strptime(stamp, "%Y-%m-%d-%H-%M-%S")
    except ValueError:
        ts = dt.datetime.now()
    pretty_date = ts.strftime("%B %d, %Y")
    name = "{}_{}_pibooth".format(stamp, slug)
    title = _safe_format(title_template, TITLE_TEMPLATE_DEFAULT,
                         slug=slug, pretty_date=pretty_date)
    desc = _safe_format(description_template, DESCRIPTION_TEMPLATE_DEFAULT,
                        slug=slug, pretty_date=pretty_date)
    return name, title, desc


def upload(filepath, api_url, api_key, timeout,
           slug=SLUG_DEFAULT,
           title_template=TITLE_TEMPLATE_DEFAULT,
           description_template=DESCRIPTION_TEMPLATE_DEFAULT):
    """POST the file to Chevereto. Returns the image URL on success, raises on failure.

    ``api_key`` travels in the POST form body, never the URL, so it
    doesn't leak into proxy / CDN / journald request logs.
    """
    if not api_url:
        raise ValueError("CHEVERETO_API_URL is required")
    if not api_key:
        raise ValueError("CHEVERETO_API_KEY is required")
    name, title, desc = seo_fields(filepath, slug, title_template, description_template)
    with open(filepath, "rb") as fp:
        r = requests.post(
            api_url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            data={
                "key": api_key,
                "format": "json",
                "name": name,
                "title": title,
                "description": desc,
                "nsfw": 0,
            },
            files={"source": fp},
        )
    r.raise_for_status()
    try:
        return r.json()["image"]["url"]
    except (ValueError, KeyError, TypeError) as exc:
        # Chevereto returned 200 but the body isn't the success shape we
        # expect — often a Cloudflare interstitial or a maintenance page.
        # Surface a preview so the operator can diagnose from journald
        # without having to re-run with DEBUG logging.
        body_preview = r.text[:200].replace("\n", " ")
        raise RuntimeError(
            "unexpected Chevereto response ({}): {!r}".format(exc, body_preview))


def mark_uploaded(filepath, url):
    """Atomically record success: write ``.uploaded``, then remove ``.pending``.

    Uses write-to-temp + ``os.replace`` so a reader never sees a
    partially written URL. A missing ``.pending`` is tolerated — it's
    common when the sync plugin and the retry drainer race to finish
    the same file.
    """
    uploaded = uploaded_path(filepath)
    tmp = uploaded + ".tmp"
    with open(tmp, "w") as f:
        f.write(url)
    os.replace(tmp, uploaded)
    try:
        os.remove(pending_path(filepath))
    except FileNotFoundError:
        pass
