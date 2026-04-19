# -*- coding: utf-8 -*-

"""Serial-to-uinput button bridge for pibooth.

For deployments where the capture / print buttons are wired through a
USB-serial adapter (PL2303 or similar — DSR/DCD lines as switch inputs)
rather than the Pi's GPIO. Translates line-state transitions into
synthetic keystrokes on a uinput virtual keyboard, which pibooth's
normal KEYDOWN handlers then pick up.

Opt-in via ``pip install pibooth[serial-buttons]``; the extra pulls in
``pyserial`` and ``python-uinput``.

Exposes a ``pibooth-serial-buttons`` console script, a systemd unit
(``pibooth-buttons.service``, installable via ``pibooth-install-systemd``),
and a udev rule (``99-serial-uinput.rules``, installable via
``pibooth-install-udev``) that grants the ``dialout`` + ``input`` groups
access to ``/dev/ttyUSB*`` and ``/dev/uinput``.

Configuration is env-var driven:

    PIBOOTH_SERIAL_PORT          serial device (default /dev/ttyUSB0)
    PIBOOTH_SERIAL_BAUD          baud rate (default 9600)
    PIBOOTH_SERIAL_BUTTON1_KEY   keystroke for DSR button (default P)
    PIBOOTH_SERIAL_BUTTON2_KEY   keystroke for DCD button (default P)
    PIBOOTH_SERIAL_POLL_DELAY    poll interval in seconds (default 0.01)
    PIBOOTH_SERIAL_RETRY_DELAY   reopen-after-error delay (default 5)

Key names: single printable chars (``P``, ``A``, ``1``), keypad digits
(``KP0``–``KP9``), or any uinput ``KEY_*`` constant (``ENTER`` → ``KEY_ENTER``).
"""

__version__ = "0.1.0"
