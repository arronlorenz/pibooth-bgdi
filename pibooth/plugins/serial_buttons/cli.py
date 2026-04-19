# -*- coding: utf-8 -*-

"""``pibooth-serial-buttons`` console script.

Reads configuration from environment variables (see package docstring),
imports pyserial + python-uinput lazily so ``pibooth-serial-buttons --help``
works on hosts that don't have them, and delegates to
:func:`pibooth.plugins.serial_buttons.bridge.run`.
"""

import logging
import os
import sys

from pibooth.plugins.serial_buttons import bridge


def _load_config():
    return {
        "port": os.environ.get("PIBOOTH_SERIAL_PORT", "/dev/ttyUSB0"),
        "baud": int(os.environ.get("PIBOOTH_SERIAL_BAUD", "9600")),
        "button1_key": os.environ.get("PIBOOTH_SERIAL_BUTTON1_KEY", "P"),
        "button2_key": os.environ.get("PIBOOTH_SERIAL_BUTTON2_KEY", "P"),
        "poll_delay": float(os.environ.get("PIBOOTH_SERIAL_POLL_DELAY", "0.01")),
        "retry_delay": float(os.environ.get("PIBOOTH_SERIAL_RETRY_DELAY", "5")),
    }


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        import serial
        import uinput
    except ImportError as exc:
        print("pibooth-serial-buttons: missing dependency ({}). "
              "Install with: pip install 'pibooth[serial-buttons]'".format(exc),
              file=sys.stderr)
        return 2
    try:
        bridge.run(_load_config(), serial, uinput)
    except Exception:
        logging.exception("Unhandled exception — exiting")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
