# -*- coding: utf-8 -*-

"""Tests for the Phase 3 worker-pool integration in PicturePlugin +
ViewPlugin.state_processing_validate gate.

These tests avoid real multiprocessing by replacing the pool with a
stub whose ``submit_main`` / ``poll_main`` / ``main_pending`` return
controlled values. The goal is contract coverage, not end-to-end
worker exercise.
"""

import pytest

from pibooth.plugins.picture_plugin import PicturePlugin
from pibooth.plugins.view_plugin import ViewPlugin


class _StubPool(object):
    """Minimal stand-in for PicturesFactoryPool. Caller drives state
    via ``set_result`` / ``set_exception``; the picture_plugin under
    test never needs a real worker process.
    """

    def __init__(self):
        self._submitted = False
        self._pending = False
        self._result = None
        self._exception = None
        self.submit_main_calls = []
        self.cleared = 0

    def submit_main(self, factory, save_path=None):
        self.submit_main_calls.append((factory, save_path))
        self._submitted = True
        self._pending = True

    def poll_main(self):
        if not self._pending:
            return None
        # Ready only when the caller primed a result or exception.
        if self._exception is not None:
            self._pending = False
            exc, self._exception = self._exception, None
            raise exc
        if self._result is not None:
            self._pending = False
            res, self._result = self._result, None
            return res
        return None

    def main_pending(self):
        return self._pending

    def clear(self):
        self.cleared += 1
        self._pending = False
        self._result = None
        self._exception = None

    # Animation-path API used by picture_plugin — harmless no-ops here.
    def add(self, factory):
        pass

    def get(self):
        return []

    def quit(self):
        pass


class _StubApp(object):
    """Cheap stand-in for pibooth.PiApplication, just enough state for
    the validate hook to probe."""

    def __init__(self):
        self.previous_picture = None

        class _Printer(object):
            def is_ready(self):
                return False
        self.printer = _Printer()

        class _Count(object):
            remaining_duplicates = 0
        self.count = _Count()


class _StubCfg(object):
    def getfloat(self, *_args, **_kw):
        return 0.0


def _make_plugin_with_stub_pool():
    plugin = PicturePlugin(plugin_manager=None)
    plugin.factory_pool = _StubPool()
    return plugin


def test_processing_do_polls_pool_sets_previous_picture_on_ready():
    """Happy path: worker completes, poll_main returns the PIL image,
    picture_plugin publishes it on app.previous_picture."""
    plugin = _make_plugin_with_stub_pool()
    pool = plugin.factory_pool
    app = _StubApp()
    app.picture_filename = "test.jpg"
    cfg = _StubCfg()

    # Pretend enter already ran — submit is what it did last.
    pool.submit_main(factory=object(), save_path="/tmp/x.jpg")
    assert pool.main_pending() is True
    assert app.previous_picture is None

    # First do-tick, worker not done yet — stays pending, picture unset.
    plugin.state_processing_do(cfg=cfg, app=app)
    assert app.previous_picture is None

    # Prime result and poll again — picture now published.
    pool._result = object()  # sentinel PIL image
    plugin.state_processing_do(cfg=cfg, app=app)
    assert app.previous_picture is not None


def test_processing_do_noop_once_picture_published():
    """After the worker result has landed, subsequent do-ticks should
    not re-poll (poll_main returning None would otherwise unset the
    picture and bounce us back into processing)."""
    plugin = _make_plugin_with_stub_pool()
    pool = plugin.factory_pool
    app = _StubApp()
    cfg = _StubCfg()
    app.previous_picture = object()  # already published

    poll_count = [0]
    original_poll = pool.poll_main

    def counting_poll():
        poll_count[0] += 1
        return original_poll()
    pool.poll_main = counting_poll

    plugin.state_processing_do(cfg=cfg, app=app)
    assert poll_count[0] == 0, "should skip poll when previous_picture is set"
    assert app.previous_picture is not None


def test_processing_do_worker_exception_propagates():
    """Failure path: if the worker raised, poll_main re-raises on the
    main thread so StateMachine.process catches it and routes to the
    failsafe state. picture_plugin must not swallow the exception."""
    plugin = _make_plugin_with_stub_pool()
    pool = plugin.factory_pool
    app = _StubApp()
    cfg = _StubCfg()

    pool.submit_main(factory=object(), save_path=None)
    pool._exception = RuntimeError("factory build blew up")

    with pytest.raises(RuntimeError, match="factory build blew up"):
        plugin.state_processing_do(cfg=cfg, app=app)


def test_view_processing_validate_waits_for_picture():
    """ViewPlugin.state_processing_validate must return None (stay in
    processing) until PicturePlugin publishes app.previous_picture —
    otherwise the state machine transitions to 'finish' while the
    worker is still composing the image."""
    view = ViewPlugin(plugin_manager=None)
    app = _StubApp()
    cfg = _StubCfg()

    # Worker in flight: picture not set yet.
    assert view.state_processing_validate(cfg=cfg, app=app) is None

    # Worker done: picture published -> validate returns next state.
    app.previous_picture = object()
    assert view.state_processing_validate(cfg=cfg, app=app) == 'finish'
