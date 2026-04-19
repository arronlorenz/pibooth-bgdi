"""Unit tests for pibooth-chevereto's drainer orchestration.

The upload POST, SEO formatting and marker semantics live in
``pibooth.plugins.chevereto.core`` and are covered by
``test_chevereto_core.py``. This file focuses on the drainer state
machine: too-fresh skipping, orphan cleanup, failure leaves .pending.
"""

import os
import pathlib
import time
from unittest import mock

os.environ.setdefault("CHEVERETO_API_KEY", "test-key")
os.environ.setdefault("CHEVERETO_API_URL", "https://api/u")

from pibooth.plugins.chevereto import core, uploader  # noqa: E402


def _write_jpg(tmp_path, stamp="2025-05-29-20-34-13"):
    jpg = tmp_path / f"{stamp}_pibooth.jpg"
    jpg.write_bytes(b"\xff\xd8\xff\xd9")
    return jpg


def _write_pending(jpg, *, age_sec=60):
    pending = pathlib.Path(str(jpg) + ".pending")
    pending.write_text("marker")
    now = time.time()
    os.utime(pending, (now - age_sec, now - age_sec))
    return pending


def _mock_response(url="https://gallery/x"):
    r = mock.Mock()
    r.raise_for_status = mock.Mock()
    r.json = mock.Mock(return_value={"image": {"url": url}})
    return r


def _process_one(pending_file):
    """Test helper that calls uploader._process_one with the defaults main() would pass."""
    import logging
    return uploader._process_one(
        pending_file,
        api_url="https://api/u",
        api_key="test-key",
        upload_timeout=5,
        min_age_sec=10,
        slug="Acme",
        title_template=core.TITLE_TEMPLATE_DEFAULT,
        description_template=core.DESCRIPTION_TEMPLATE_DEFAULT,
        log=logging.getLogger("test"),
    )


# ---------------------------------------------------------------------------
# _process_one — the state machine
# ---------------------------------------------------------------------------
def test_process_one_happy_path(tmp_path):
    jpg = _write_jpg(tmp_path)
    pending = _write_pending(jpg, age_sec=60)
    with mock.patch.object(core, "requests") as req:
        req.post.return_value = _mock_response("https://gallery/ok")
        url = _process_one(str(pending))
    assert url == "https://gallery/ok"
    assert pathlib.Path(str(jpg) + ".uploaded").exists()
    assert not pending.exists()


def test_process_one_skips_when_already_uploaded(tmp_path):
    jpg = _write_jpg(tmp_path)
    pending = _write_pending(jpg, age_sec=60)
    pathlib.Path(str(jpg) + ".uploaded").write_text("https://gallery/prior")
    with mock.patch.object(core, "requests") as req:
        result = _process_one(str(pending))
    assert result is None
    req.post.assert_not_called()
    assert not pending.exists()


def test_process_one_cleans_orphan_pending_when_jpg_missing(tmp_path):
    pending = tmp_path / "2025-05-29-01-01-01_pibooth.jpg.pending"
    pending.write_text("orphan")
    now = time.time()
    os.utime(pending, (now - 60, now - 60))
    with mock.patch.object(core, "requests") as req:
        result = _process_one(str(pending))
    assert result is None
    req.post.assert_not_called()
    assert not pending.exists()


def test_process_one_skips_too_fresh(tmp_path):
    jpg = _write_jpg(tmp_path)
    pending = _write_pending(jpg, age_sec=1)
    with mock.patch.object(core, "requests") as req:
        result = _process_one(str(pending))
    assert result is None
    req.post.assert_not_called()
    assert pending.exists()


def test_process_one_leaves_pending_on_upload_failure(tmp_path):
    jpg = _write_jpg(tmp_path)
    pending = _write_pending(jpg, age_sec=60)
    with mock.patch.object(core, "requests") as req:
        req.post.side_effect = Exception("boom")
        result = _process_one(str(pending))
    assert result is None
    assert pending.exists()
    assert not pathlib.Path(str(jpg) + ".uploaded").exists()


# ---------------------------------------------------------------------------
# main — drains a dir with multiple pendings
# ---------------------------------------------------------------------------
def test_main_drains_multiple_pendings(tmp_path, monkeypatch):
    jpg_a = _write_jpg(tmp_path, "2025-05-29-10-00-00")
    jpg_b = _write_jpg(tmp_path, "2025-05-29-10-00-01")
    _write_pending(jpg_a, age_sec=60)
    _write_pending(jpg_b, age_sec=60)

    monkeypatch.setenv("CHEVERETO_CAPTURES_DIR", str(tmp_path))
    with mock.patch.object(core, "requests") as req:
        req.post.return_value = _mock_response("https://gallery/bulk")
        rc = uploader.main()
    assert rc == 0
    assert pathlib.Path(str(jpg_a) + ".uploaded").exists()
    assert pathlib.Path(str(jpg_b) + ".uploaded").exists()
    assert not pathlib.Path(str(jpg_a) + ".pending").exists()
    assert not pathlib.Path(str(jpg_b) + ".pending").exists()


def test_main_no_work_returns_cleanly(tmp_path, monkeypatch):
    monkeypatch.setenv("CHEVERETO_CAPTURES_DIR", str(tmp_path))
    with mock.patch.object(core, "requests") as req:
        rc = uploader.main()
    assert rc == 0
    req.post.assert_not_called()


def test_main_rejects_missing_captures_dir(monkeypatch):
    monkeypatch.delenv("CHEVERETO_CAPTURES_DIR", raising=False)
    monkeypatch.delenv("CAPTURES_DIR", raising=False)
    rc = uploader.main()
    assert rc == 2
