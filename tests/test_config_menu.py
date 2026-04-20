# -*- coding: utf-8 -*-

"""Headless smoke test for PiConfigMenu.

Guards against pygame-menu API drift (hard-pin 4.0.7 → >=4.5.2). Does
not verify correctness — just that construction + one render/dispatch
tick doesn't raise.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

import pibooth.fonts as fonts
from pibooth.config.menu import PiConfigMenu
from pibooth.view.window import PiWindow


class _StubCfg:
    """Minimal duck-typed stand-in for PiConfigParser. Provides just
    enough attributes/methods for PiConfigMenu.__init__ to land.
    """

    def __init__(self):
        self.filename = "/tmp/pibooth-menu-smoke.cfg"

    def get(self, section, option, fallback=""):
        return ""

    def getint(self, section, option, fallback=0):
        return 0

    def getfloat(self, section, option, fallback=0.0):
        return 0.0

    def getboolean(self, section, option, fallback=False):
        return False

    def gettyped(self, section, option):
        return (0, 0, 0)

    def gettuple(self, *args, **kw):
        return ()

    def getpath(self, section, option):
        return ""

    def join_path(self, name):
        return "/tmp/" + name


class _StubPM:
    """Duck-typed plugin manager. PiConfigMenu calls
    ``pm.list_external_plugins()`` to decide whether to add the plugins
    submenu; returning an empty list keeps the menu construction short
    without needing to register real plugins.
    """

    def list_external_plugins(self):
        return []

    def get_friendly_name(self, plugin):
        return "stub"


class _StubApp:
    def __init__(self):
        self.capture_choices = (4, 1)

        class _Count:
            taken = 0
            printed = 0
            forgotten = 0

            def names(self):
                return ("taken", "printed", "forgotten")

            def __iter__(self):
                return iter(self.names())

            def __getitem__(self, name):
                return 0

        self.count = _Count()


@pytest.fixture(scope="module")
def win():
    return PiWindow("menu-smoke", debug=False)


def test_pi_config_menu_constructs(win):
    """PiConfigMenu.__init__ should succeed against the installed
    pygame-menu version. Covers constructor-arg drift between 4.0.7
    and 4.5.2 (width / height / theme / touchscreen kwarg names)."""
    try:
        menu = PiConfigMenu(
            plugins_manager=_StubPM(),
            configuration=_StubCfg(),
            application=_StubApp(),
            window=win,
        )
    except Exception as exc:
        pytest.fail(f"PiConfigMenu construction raised: {exc!r}")
    assert menu is not None


def test_pi_config_menu_show_and_process_tick(win):
    """Show the menu, dispatch one empty event tick, draw once.
    Catches API drift in .show() / .process() / ._main_menu.update()."""
    menu = PiConfigMenu(
        plugins_manager=_StubPM(),
        configuration=_StubCfg(),
        application=_StubApp(),
        window=win,
    )
    try:
        menu.show()
        menu.process([])  # no events, just cycle the update path
    except Exception as exc:
        pytest.fail(f"menu.show/process raised: {exc!r}")
