# -*- coding: utf-8 -*-

"""Core logic for the serial-to-uinput button bridge.

Kept separate from cli.py so it can be imported (and unit-tested)
without triggering any serial open, uinput device creation, or signal
handler setup.
"""

import logging
import re
import signal
import time


log = logging.getLogger("pibooth-serial-buttons")


def resolve_keycode(name, uinput_module):
    """Return the uinput KEY_* integer for a human-friendly name.

    Accepts:
      - single A-Z or 0-9 characters: ``"P"`` → ``KEY_P`` (case-insensitive)
      - keypad digits: ``"KP3"`` → ``KEY_KP3``
      - any uinput ``KEY_*`` constant: ``"ENTER"`` or ``"KEY_ENTER"`` → ``KEY_ENTER``

    Other single-character names (space, symbols) probably don't map to
    a ``uinput.KEY_*`` and raise ``ValueError``.

    :param name: human-friendly key name
    :param uinput_module: the ``uinput`` module (injected for testability)
    :raises ValueError: if the name doesn't resolve
    """
    name = name.strip().upper()
    m = re.fullmatch(r"KP(\d)", name)
    if m:
        attr = "KEY_KP" + m.group(1)
    elif len(name) == 1 and name.isprintable():
        attr = "KEY_" + name
    elif name.startswith("KEY_"):
        attr = name
    else:
        attr = "KEY_" + name
    try:
        return getattr(uinput_module, attr)
    except AttributeError:
        raise ValueError("Unknown key name '{}'".format(name))


def open_serial(serial_module, port, baud, retry_delay):
    """Block until the serial port opens. Retries forever on failure."""
    while True:
        try:
            ser = serial_module.Serial(port, baud, timeout=0)
            log.info("Serial port %s opened", port)
            return ser
        except (serial_module.SerialException, OSError) as exc:
            log.warning("Serial open failed: %s — retrying in %ss", exc, retry_delay)
            time.sleep(retry_delay)


def run(config, serial_module, uinput_module):
    """Main poll loop. Returns cleanly on SIGINT/SIGTERM.

    :param config: dict with keys ``port``, ``baud``, ``button1_key``,
                   ``button2_key``, ``poll_delay``, ``retry_delay``
    :param serial_module: the ``serial`` module (pyserial)
    :param uinput_module: the ``uinput`` module (python-uinput)
    """
    key1_code = resolve_keycode(config["button1_key"], uinput_module)
    key2_code = resolve_keycode(config["button2_key"], uinput_module)

    ser = open_serial(serial_module, config["port"], config["baud"], config["retry_delay"])
    device = uinput_module.Device([key1_code, key2_code],
                                  name="Pibooth Virtual Keyboard")
    log.info("uinput ready — Btn1→%s, Btn2→%s",
             config["button1_key"].upper(), config["button2_key"].upper())

    running = [True]

    def shutdown(_signum, _frame):
        running[0] = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    prev1 = prev2 = False
    while running[0]:
        try:
            b1 = not ser.getDSR()
            b2 = not ser.getCD()

            if b1 and not prev1:
                device.emit_click(key1_code)
                log.debug("Btn1 → %s", config["button1_key"].upper())
            if b2 and not prev2:
                device.emit_click(key2_code)
                log.debug("Btn2 → %s", config["button2_key"].upper())

            prev1, prev2 = b1, b2
            time.sleep(config["poll_delay"])

        except (serial_module.SerialException, OSError) as exc:
            log.error("Serial error: %s — reopening port", exc)
            try:
                ser.close()
            except Exception:
                pass
            ser = open_serial(serial_module, config["port"], config["baud"],
                              config["retry_delay"])

    ser.close()
    log.info("Exiting cleanly")
