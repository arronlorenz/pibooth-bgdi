"""Unit tests for pibooth.plugins.chevereto.core.

Single source of truth for SEO formatting, the upload POST, and marker
semantics — both the plugin and the drainer delegate here.
"""

import pathlib
from unittest import mock

from pibooth.plugins.chevereto import core


def _write_jpg(tmp_path, stamp="2025-05-29-20-34-13"):
    jpg = tmp_path / f"{stamp}_pibooth.jpg"
    jpg.write_bytes(b"\xff\xd8\xff\xd9")
    return jpg


def _mock_response(url="https://gallery/x"):
    r = mock.Mock()
    r.raise_for_status = mock.Mock()
    r.json = mock.Mock(return_value={"image": {"url": url}})
    return r


# ---------------------------------------------------------------------------
# seo_fields
# ---------------------------------------------------------------------------
def test_seo_fields_well_formed_timestamp(tmp_path):
    jpg = _write_jpg(tmp_path, stamp="2025-05-29-20-34-13")
    name, title, desc = core.seo_fields(str(jpg), slug="Acme")
    assert name == "2025-05-29-20-34-13_Acme_pibooth"
    assert "May 29, 2025" in title
    assert "May 29, 2025" in desc
    assert "Acme" in title
    assert "Acme" in desc


def test_seo_fields_falls_back_when_stamp_unparseable(tmp_path):
    jpg = tmp_path / "garbagefile_pibooth.jpg"
    jpg.write_bytes(b"\x00")
    name, title, desc = core.seo_fields(str(jpg), slug="Acme")
    assert name.startswith("garbagefile_")
    assert "Acme" in name


def test_seo_fields_honors_custom_templates(tmp_path):
    jpg = _write_jpg(tmp_path)
    _, title, desc = core.seo_fields(
        str(jpg),
        slug="Acme",
        title_template="{slug}::T::{pretty_date}",
        description_template="{slug}::D::{pretty_date}",
    )
    assert title.startswith("Acme::T::")
    assert desc.startswith("Acme::D::")


def test_seo_fields_falls_back_on_bad_template(tmp_path, caplog):
    """A typo in the env-var template (e.g. {date} not {pretty_date})
    must not raise — that would leave every capture stuck in .pending
    and the drainer would never recover.
    """
    core._warned_templates.clear()  # so the warning fires deterministically
    jpg = _write_jpg(tmp_path)
    with caplog.at_level("WARNING", logger="pibooth"):
        _, title, desc = core.seo_fields(
            str(jpg),
            slug="Acme",
            title_template="{slug} on {date}",     # {date} is not provided
            description_template="{slug} on {date}",
        )
    # Got the *default* templates' formatting, not the broken one.
    assert "Acme" in title and "May 29, 2025" in title
    assert "Acme" in desc and "May 29, 2025" in desc
    assert any("unknown placeholder" in r.message for r in caplog.records), \
        "operator must see a warning explaining the fallback"


def test_seo_fields_warns_once_per_bad_template(tmp_path, caplog):
    """Repeated calls with the same broken template must not respam the
    journal — once is enough to alert the operator. Distinct template
    strings each get their own warning.
    """
    core._warned_templates.clear()
    jpg = _write_jpg(tmp_path)
    with caplog.at_level("WARNING", logger="pibooth"):
        for _ in range(3):
            core.seo_fields(str(jpg), slug="Acme",
                            title_template="{slug} title {nope}",
                            description_template="{slug} desc {oops}")
    warnings = [r for r in caplog.records if "unknown placeholder" in r.message]
    # Two distinct templates → two warnings total across three calls.
    assert len(warnings) == 2
    assert any("'nope'" in r.message for r in warnings)
    assert any("'oops'" in r.message for r in warnings)


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------
def test_upload_posts_expected_fields(tmp_path):
    jpg = _write_jpg(tmp_path)
    with mock.patch.object(core, "requests") as req:
        req.post.return_value = _mock_response("https://gallery/x")
        url = core.upload(str(jpg), api_url="https://api/u", api_key="k", timeout=5,
                          slug="Acme")
    assert url == "https://gallery/x"

    args, kwargs = req.post.call_args
    assert args[0] == "https://api/u"
    assert kwargs["timeout"] == 5
    assert kwargs["data"]["key"] == "k"
    assert kwargs["data"]["format"] == "json"
    assert kwargs["data"]["nsfw"] == 0
    assert "Acme" in kwargs["data"]["name"]
    assert "source" in kwargs["files"]


def test_upload_rejects_missing_api_url(tmp_path):
    jpg = _write_jpg(tmp_path)
    try:
        core.upload(str(jpg), api_url="", api_key="k", timeout=1)
    except ValueError as exc:
        assert "API_URL" in str(exc)
    else:
        raise AssertionError("expected ValueError for empty api_url")


def test_upload_rejects_missing_api_key(tmp_path):
    jpg = _write_jpg(tmp_path)
    try:
        core.upload(str(jpg), api_url="https://api/u", api_key="", timeout=1)
    except ValueError as exc:
        assert "API_KEY" in str(exc)
    else:
        raise AssertionError("expected ValueError for empty api_key")


# ---------------------------------------------------------------------------
# marker semantics
# ---------------------------------------------------------------------------
def test_mark_uploaded_creates_uploaded_and_removes_pending(tmp_path):
    jpg = _write_jpg(tmp_path)
    pending = pathlib.Path(core.pending_path(str(jpg)))
    pending.write_text("marker")

    core.mark_uploaded(str(jpg), "https://gallery/y")

    uploaded = pathlib.Path(core.uploaded_path(str(jpg)))
    assert uploaded.read_text() == "https://gallery/y"
    assert not pending.exists()


def test_mark_uploaded_tolerates_missing_pending(tmp_path):
    jpg = _write_jpg(tmp_path)
    core.mark_uploaded(str(jpg), "https://gallery/z")
    assert pathlib.Path(core.uploaded_path(str(jpg))).read_text() == "https://gallery/z"


def test_pending_and_uploaded_paths():
    assert core.pending_path("/foo/bar.jpg") == "/foo/bar.jpg.pending"
    assert core.uploaded_path("/foo/bar.jpg") == "/foo/bar.jpg.uploaded"
