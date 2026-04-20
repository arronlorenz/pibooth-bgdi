# -*- coding: utf-8 -*-

"""Asynchronous workers for generating pictures."""

import multiprocessing


def _build_and_save(factory, save_path):
    """Worker entry point: build the final PIL image and optionally save
    it to disk. Runs in a child process so ``pygame.display.update`` on
    the main thread keeps flipping while the factory composites.
    """
    image = factory.build()
    if save_path:
        factory.save(save_path)
    return image


class PicturesFactoryPool(object):

    def __init__(self):
        self._pool = None
        self._async_results = []
        # Main-capture future. Animation futures stay in
        # ``_async_results`` (the existing API); the main-capture future
        # is separate because its lifecycle is different: exactly one at
        # a time, polled by state_processing_validate, result consumed
        # on transition to 'finish'.
        self._main_result = None

    def _ensure_pool(self):
        if not self._pool:
            self._pool = multiprocessing.Pool(processes=min(multiprocessing.cpu_count(), 4))
        return self._pool

    def add(self, factory):
        """Add a new picture factory and build it asyncronously.
        """
        self._async_results.append(self._ensure_pool().apply_async(factory.build))

    def get(self):
        """Return all the results.
        """
        return [res.get() for res in self._async_results]

    def submit_main(self, factory, save_path=None):
        """Kick off the main-capture factory.build (+ optional save) in a
        worker process. Returns immediately so the main loop stays
        responsive. Use :py:meth:`poll_main` to wait/collect the result.
        """
        self._main_result = self._ensure_pool().apply_async(
            _build_and_save, (factory, save_path))

    def poll_main(self):
        """Poll the main-capture future.

        Returns the built PIL image when the worker is done. Returns
        ``None`` if not yet ready. Raises if the worker raised (so the
        state machine's failsafe path can catch it). Returning-then-
        clearing the result means repeat calls after completion return
        ``None`` again — guard against that in the caller.
        """
        res = self._main_result
        if res is None:
            return None
        if not res.ready():
            return None
        self._main_result = None
        return res.get()  # re-raises in the main process if the worker raised

    def main_pending(self):
        """True iff ``submit_main`` has been called and the result is
        not yet collected. Useful so the caller doesn't double-submit.
        """
        return self._main_result is not None

    def clear(self):
        """Cancel all run tasks and drop all factories.
        """
        for res in self._async_results:
            res.get(5)
        self._async_results = []

    def quit(self):
        """Quit and cleanup the pool.
        """
        if self._pool:
            self._pool.terminate()
            self._pool.join()
