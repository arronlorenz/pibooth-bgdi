# -*- coding: utf-8 -*-

"""Plugin building the final picture montage."""

import os
import os.path as osp
import itertools
from datetime import datetime
import pibooth
from pibooth.utils import LOGGER, PoolingTimer
from pibooth.pictures import get_picture_factory
from pibooth.pictures.pool import PicturesFactoryPool


class PicturePlugin(object):

    """Plugin to build the final picture.
    """

    name = 'pibooth-core:picture'

    def __init__(self, plugin_manager):
        self._pm = plugin_manager
        self.factory_pool = PicturesFactoryPool()
        self.picture_destroy_timer = PoolingTimer(0)
        self.second_previous_picture = None
        self.texts_vars = {}
        # Path to save the in-flight built picture to, stashed at
        # state_processing_enter and used by poll_main -> app assignment.
        self._pending_save_path = None

    def _reset_vars(self, app):
        """Destroy final picture (can not be used anymore).
        """
        self.factory_pool.clear()
        app.previous_picture = None
        app.previous_animated = None
        app.previous_picture_file = None
        self._pending_save_path = None
        self._pending_factory = None
        self._pending_extra_savedirs = ()

    @pibooth.hookimpl(hookwrapper=True)
    def pibooth_setup_picture_factory(self, cfg, opt_index, factory):

        outcome = yield  # all corresponding hookimpls are invoked here
        factory = outcome.get_result() or factory

        factory.set_margin(cfg.getint('PICTURE', 'margin_thick'))

        backgrounds = cfg.gettuple('PICTURE', 'backgrounds', ('color', 'path'), 2)
        factory.set_background(backgrounds[opt_index])

        overlays = cfg.gettuple('PICTURE', 'overlays', 'path', 2)
        if overlays[opt_index]:
            factory.set_overlay(overlays[opt_index])

        texts = [cfg.get('PICTURE', 'footer_text1').strip('"').format(**self.texts_vars),
                 cfg.get('PICTURE', 'footer_text2').strip('"').format(**self.texts_vars)]
        colors = cfg.gettuple('PICTURE', 'text_colors', 'color', len(texts))
        text_fonts = cfg.gettuple('PICTURE', 'text_fonts', str, len(texts))
        alignments = cfg.gettuple('PICTURE', 'text_alignments', str, len(texts))
        if any(elem != '' for elem in texts):
            for params in zip(texts, text_fonts, colors, alignments):
                factory.add_text(*params)

        if cfg.getboolean('PICTURE', 'captures_cropping'):
            factory.set_cropping()

        if cfg.getboolean('GENERAL', 'debug'):
            factory.set_outlines()

        outcome.force_result(factory)

    @pibooth.hookimpl
    def pibooth_cleanup(self):
        self.factory_pool.quit()

    @pibooth.hookimpl
    def state_failsafe_enter(self, app):
        self._reset_vars(app)

    @pibooth.hookimpl
    def state_wait_enter(self, cfg, app):
        animated = self.factory_pool.get()
        if cfg.getfloat('WINDOW', 'wait_picture_delay') == 0:
            # Do it here to avoid a transient display of the picture
            self._reset_vars(app)
        elif animated:
            app.previous_animated = itertools.cycle(animated)

        # Reset timeout in case of settings changed
        self.picture_destroy_timer.timeout = max(0, cfg.getfloat('WINDOW', 'wait_picture_delay'))
        self.picture_destroy_timer.start()

    @pibooth.hookimpl
    def state_wait_do(self, cfg, app):
        if cfg.getfloat('WINDOW', 'wait_picture_delay') > 0 and self.picture_destroy_timer.is_timeout()\
                and app.previous_picture_file:
            self._reset_vars(app)

    @pibooth.hookimpl
    def state_processing_enter(self, cfg, app):
        """Prepare inputs for the factory build, then kick the build off
        in a worker process so the main loop stays responsive while it
        runs. Camera IO has to stay on the main thread because the
        gphoto2 handle isn't pickleable for multiprocessing; everything
        downstream of ``get_captures()`` is offloaded.
        """
        self.second_previous_picture = app.previous_picture
        self._reset_vars(app)

        idx = app.capture_choices.index(app.capture_nbr)
        self.texts_vars['date'] = datetime.strptime(app.capture_date, "%Y-%m-%d-%H-%M-%S")
        self.texts_vars['count'] = app.count

        LOGGER.info("Saving raw captures")
        captures = app.camera.get_captures()

        for savedir in cfg.gettuple('GENERAL', 'directory', 'path'):
            rawdir = osp.join(savedir, "raw", app.capture_date)
            os.makedirs(rawdir)

            for capture in captures:
                count = captures.index(capture)
                capture.save(osp.join(rawdir, "pibooth{:03}.jpg".format(count)))

        LOGGER.info("Creating the final picture")
        default_factory = get_picture_factory(captures, cfg.get('PICTURE', 'orientation'))
        factory = self._pm.hook.pibooth_setup_picture_factory(cfg=cfg,
                                                              opt_index=idx,
                                                              factory=default_factory)

        savedirs = cfg.gettuple('GENERAL', 'directory', 'path')
        # Save to the first directory from the worker; mirror to any
        # others after the build completes (state_processing_do).
        primary_save = osp.join(savedirs[0], app.picture_filename) if savedirs else None
        app.previous_picture_file = primary_save
        self._pending_save_path = primary_save
        self._pending_extra_savedirs = savedirs[1:] if savedirs else ()
        self._pending_factory = factory

        self.factory_pool.submit_main(factory, save_path=primary_save)

        if cfg.getboolean('WINDOW', 'animate') and app.capture_nbr > 1:
            LOGGER.info("Asyncronously generate pictures for animation")
            for capture in captures:
                default_factory = get_picture_factory((capture,), cfg.get(
                    'PICTURE', 'orientation'), force_pil=True, dpi=200)
                factory = self._pm.hook.pibooth_setup_picture_factory(cfg=cfg,
                                                                      opt_index=idx,
                                                                      factory=default_factory)
                factory.set_margin(factory._margin // 3)  # 1/3 since DPI is divided by 3
                self.factory_pool.add(factory)

    @pibooth.hookimpl
    def state_processing_do(self, cfg, app):
        """Poll the worker. When the built image arrives, publish it on
        ``app.previous_picture`` so ViewPlugin.state_processing_validate
        lets the state machine advance.
        """
        if app.previous_picture is not None:
            return  # already built this cycle
        image = self.factory_pool.poll_main()
        if image is None:
            return  # worker still running — stay in processing
        app.previous_picture = image
        # Factory saved to the primary directory in-worker; mirror to
        # any additional configured directories from the main process.
        factory = getattr(self, '_pending_factory', None)
        for extra in getattr(self, '_pending_extra_savedirs', ()):
            path = osp.join(extra, app.picture_filename)
            try:
                if factory is not None:
                    factory.save(path)
            except Exception as exc:
                LOGGER.warning("Mirror save to %s failed: %s", path, exc)
        self._pending_factory = None
        self._pending_extra_savedirs = ()

    @pibooth.hookimpl
    def state_processing_exit(self, app):
        app.count.taken += 1  # Do it here because 'print' state can be skipped

    @pibooth.hookimpl
    def state_print_do(self, cfg, app, events):
        if app.find_capture_event(events):

            LOGGER.info("Moving the picture in the forget folder")
            for savedir in cfg.gettuple('GENERAL', 'directory', 'path'):
                forgetdir = osp.join(savedir, "forget")
                if not osp.isdir(forgetdir):
                    os.makedirs(forgetdir)
                os.rename(osp.join(savedir, app.picture_filename), osp.join(forgetdir, app.picture_filename))

            self._reset_vars(app)
            app.count.forgotten += 1
            app.previous_picture = self.second_previous_picture

            # Deactivate the print function for the backuped picture
            # as we don't known how many times it has already been printed
            app.count.remaining_duplicates = 0
