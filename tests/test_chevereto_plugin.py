"""Smoke tests for pibooth.plugins.chevereto.plugin.

Covers the sync-upload state machine the plugin drives from
``state_processing_exit``. Marker semantics + upload POST are tested
in test_chevereto_core.py.
"""

import os
import pathlib
from unittest import mock

os.environ.setdefault("CHEVERETO_API_KEY", "test-key")
os.environ.setdefault("CHEVERETO_API_URL", "https://api/u")
os.environ.setdefault("CHEVERETO_SLUG", "Acme")

from pibooth.plugins.chevereto import core, plugin  # noqa: E402


def _write_jpg(tmp_path, stamp="2025-05-29-20-34-13"):
    jpg = tmp_path / f"{stamp}_pibooth.jpg"
    jpg.write_bytes(b"\xff\xd8\xff\xd9")
    return jpg


def _mock_response(url="https://gallery/x"):
    r = mock.Mock()
    r.raise_for_status = mock.Mock()
    r.json = mock.Mock(return_value={"image": {"url": url}})
    return r


class _FakeApp:
    def __init__(self, filepath):
        self.previous_picture_file = str(filepath) if filepath else None
        self.previous_picture_url = None


def test_sync_upload_success_creates_uploaded_and_sets_url(tmp_path):
    jpg = _write_jpg(tmp_path)
    app = _FakeApp(jpg)
    with mock.patch.object(core, "requests") as req:
        req.post.return_value = _mock_response("https://gallery/ok")
        plugin.state_processing_exit(app)

    assert app.previous_picture_url == "https://gallery/ok"
    assert pathlib.Path(str(jpg) + ".uploaded").read_text() == "https://gallery/ok"
    assert not pathlib.Path(str(jpg) + ".pending").exists()


def test_sync_upload_failure_leaves_pending(tmp_path):
    jpg = _write_jpg(tmp_path)
    app = _FakeApp(jpg)
    with mock.patch.object(core, "requests") as req:
        req.post.side_effect = Exception("network down")
        plugin.state_processing_exit(app)

    assert app.previous_picture_url is None
    pending = pathlib.Path(str(jpg) + ".pending")
    assert pending.exists(), "plugin must leave .pending for the drainer"
    assert not pathlib.Path(str(jpg) + ".uploaded").exists()


def test_already_uploaded_reuses_url_without_posting(tmp_path):
    jpg = _write_jpg(tmp_path)
    pathlib.Path(str(jpg) + ".uploaded").write_text("https://gallery/prior")
    app = _FakeApp(jpg)
    with mock.patch.object(core, "requests") as req:
        plugin.state_processing_exit(app)

    assert app.previous_picture_url == "https://gallery/prior"
    req.post.assert_not_called()


def test_missing_api_key_skips(tmp_path, monkeypatch):
    jpg = _write_jpg(tmp_path)
    app = _FakeApp(jpg)
    monkeypatch.setattr(plugin, "API_KEY", None)
    with mock.patch.object(core, "requests") as req:
        plugin.state_processing_exit(app)
    assert app.previous_picture_url is None
    req.post.assert_not_called()
    assert not pathlib.Path(str(jpg) + ".pending").exists()


def test_missing_previous_picture_file_is_noop(tmp_path):
    app = _FakeApp(filepath=None)
    with mock.patch.object(core, "requests") as req:
        plugin.state_processing_exit(app)
    assert app.previous_picture_url is None
    req.post.assert_not_called()
