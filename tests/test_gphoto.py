# -*- coding: utf-8 -*-

import logging
from pibooth.camera.gphoto import gp_log_callback


def test_gp_log_callback_str(caplog):
    with caplog.at_level(logging.DEBUG, logger="pibooth.gphoto2"):
        gp_log_callback(None, 'Domain', 'Message')
    assert "Domain: Message" in [r.getMessage() for r in caplog.records]


def test_gp_log_callback_bytes(caplog):
    with caplog.at_level(logging.DEBUG, logger="pibooth.gphoto2"):
        gp_log_callback(None, b'Domain', b'Message')
    assert "Domain: Message" in [r.getMessage() for r in caplog.records]
