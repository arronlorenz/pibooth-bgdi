"""Unit tests for pibooth.plugins.serial_buttons.

The ``bridge`` module takes ``serial`` and ``uinput`` as injected
parameters, so it's testable without pyserial or python-uinput being
installed. ``cli._load_config`` is pure env-var reading.
"""

import os
from unittest import mock

import pytest

from pibooth.plugins.serial_buttons import bridge, cli


# ---------------------------------------------------------------------------
# resolve_keycode
# ---------------------------------------------------------------------------
class _FakeUinput:
    """Stand-in for the real ``uinput`` module with only the KEY_* attrs we set.

    Missing attrs raise AttributeError (like the real module), so
    resolve_keycode's unknown-name path is exercised.
    """
    def __init__(self, **constants):
        for k, v in constants.items():
            setattr(self, k, v)


def _fake_uinput(**constants):
    return _FakeUinput(**constants)


def test_resolve_keycode_single_letter():
    u = _fake_uinput(KEY_P=25)
    assert bridge.resolve_keycode("P", u) == 25


def test_resolve_keycode_is_case_insensitive():
    u = _fake_uinput(KEY_P=25)
    assert bridge.resolve_keycode("p", u) == 25


def test_resolve_keycode_keypad_digit():
    u = _fake_uinput(KEY_KP3=83)
    assert bridge.resolve_keycode("KP3", u) == 83


def test_resolve_keycode_accepts_full_key_name():
    u = _fake_uinput(KEY_ENTER=28)
    assert bridge.resolve_keycode("KEY_ENTER", u) == 28


def test_resolve_keycode_accepts_short_name():
    u = _fake_uinput(KEY_ENTER=28)
    assert bridge.resolve_keycode("ENTER", u) == 28


def test_resolve_keycode_rejects_unknown():
    u = _fake_uinput(KEY_P=25)   # no KEY_UNKNOWN
    with pytest.raises(ValueError, match="Unknown key"):
        bridge.resolve_keycode("UNKNOWN", u)


# ---------------------------------------------------------------------------
# cli._load_config — env-var defaults
# ---------------------------------------------------------------------------
def test_load_config_defaults(monkeypatch):
    for k in ("PIBOOTH_SERIAL_PORT", "PIBOOTH_SERIAL_BAUD",
              "PIBOOTH_SERIAL_BUTTON1_KEY", "PIBOOTH_SERIAL_BUTTON2_KEY",
              "PIBOOTH_SERIAL_POLL_DELAY", "PIBOOTH_SERIAL_RETRY_DELAY"):
        monkeypatch.delenv(k, raising=False)
    cfg = cli._load_config()
    assert cfg["port"] == "/dev/ttyUSB0"
    assert cfg["baud"] == 9600
    assert cfg["button1_key"] == "P"
    assert cfg["button2_key"] == "P"
    assert cfg["poll_delay"] == 0.01
    assert cfg["retry_delay"] == 5


def test_load_config_honors_env_overrides(monkeypatch):
    monkeypatch.setenv("PIBOOTH_SERIAL_PORT", "/dev/ttyUSB1")
    monkeypatch.setenv("PIBOOTH_SERIAL_BAUD", "115200")
    monkeypatch.setenv("PIBOOTH_SERIAL_BUTTON1_KEY", "A")
    monkeypatch.setenv("PIBOOTH_SERIAL_BUTTON2_KEY", "ENTER")
    monkeypatch.setenv("PIBOOTH_SERIAL_POLL_DELAY", "0.05")
    monkeypatch.setenv("PIBOOTH_SERIAL_RETRY_DELAY", "2")
    cfg = cli._load_config()
    assert cfg["port"] == "/dev/ttyUSB1"
    assert cfg["baud"] == 115200
    assert cfg["button1_key"] == "A"
    assert cfg["button2_key"] == "ENTER"
    assert cfg["poll_delay"] == 0.05
    assert cfg["retry_delay"] == 2


# ---------------------------------------------------------------------------
# cli.main — missing deps
# ---------------------------------------------------------------------------
def test_cli_main_reports_missing_dependency(monkeypatch, capsys):
    """If pyserial isn't installed, main should exit 2 with a clear msg."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name in ("serial", "uinput"):
            raise ImportError("No module named '{}'".format(name))
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    rc = cli.main()
    assert rc == 2
    err = capsys.readouterr().err
    assert "missing dependency" in err
    assert "pibooth[serial-buttons]" in err
