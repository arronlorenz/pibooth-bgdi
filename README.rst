pibooth-bgdi
============

The photobooth software running at the **Blue Grass Drive-In**.

This is a self-contained Raspberry Pi photobooth stack maintained for
BGDrive.in's drive-in theatre. Originally derived from
`pibooth-project/pibooth <https://github.com/pibooth/pibooth>`_ 2.0.8
(MIT license, Vincent Verdeil / Antoine Rousseaux), significantly
diverged since — upstream has been dormant since 2023-07.

If you stumbled on this repo looking for a general-purpose pibooth,
you probably want upstream. This fork is BGDI-specific and is not
published to PyPI.

What's different from upstream
------------------------------

* **Python 3.11 / Debian Bookworm floor** — upstream targets 3.7+.
* **Chevereto upload plugin** as a shipped ``[chevereto]`` extra.
  Gallery integration with a retry queue + drainer, all pluggy-native.
* **Serial-buttons bridge** as ``[serial-buttons]`` — USB-serial
  DSR/DCD line transitions → uinput key events. Parameterized by
  env var.
* **Shipped systemd units + udev rules** as package data.
  ``pibooth-install-udev`` and ``pibooth-install-systemd`` copy the
  right ones into ``/etc/`` based on which extras are installed.
* **pibooth-doctor** — preflight health check for the full chain
  (Python version, X/Wayland session, gphoto2 liveness, udev rules,
  systemd units, ``/etc/pibooth.env``, captures dir, group
  membership).
* **Window/render layer refactor** — ``StateMachine.set_state``
  baseline surface wipe, ``xrandr --auto`` crash recovery,
  worker-pool processing (no main-loop freeze during factory build).
  See ``pibooth-extras/docs/FRAMEWORK_NOTES.md``.
* **picamera / picamera2 paths dropped** — BGDI uses a DSLR over
  USB, and legacy picamera is deprecated on Bookworm anyway.

Features carried over from upstream
-----------------------------------

* 1–4 captures per session, concatenated into a final picture
* gPhoto2, OpenCV, Raspberry Pi camera support (picamera dropped in
  this fork)
* GPIO buttons + lamps on the Pi
* Fully driven from buttons / keyboard / mouse / touchscreen
* Auto-start at boot via systemd
* CUPS printing with queue indication
* Custom overlays, backgrounds, texts on the final picture
* pluggy-based plugin system — load external plugins via pip extras
  or a ``plugins=`` path in ``pibooth.cfg``
* Multi-language UI (Danish, Dutch, English, French, German,
  Hungarian, Norwegian, Portuguese, Spanish, Swedish). BGDI runs the
  English strings.

Installing on the BGDI Pi
-------------------------

See ``pibooth-extras/docs/INSTALL.md`` — the full recipe is
``piadmin/setup.sh install`` on a fresh Raspberry Pi OS Bookworm
image with an external USB at ``/mnt/picstorage``.

For dev-only install::

    pip install --user '.[dslr,chevereto,serial-buttons]'

Console scripts land under ``~/.local/bin/``:

* ``pibooth`` — main app
* ``pibooth-chevereto`` — upload queue drainer
* ``pibooth-serial-buttons`` — serial→uinput bridge
* ``pibooth-install-udev`` / ``pibooth-install-systemd`` — deploy shipped rules/units
* ``pibooth-doctor`` — preflight diagnostic

Tests::

    SDL_VIDEODRIVER=dummy CAM_VIDEODRIVER=dummy pytest -q

Related repos
-------------

* ``arronlorenz/pibooth-extras`` (private) — BGDI deployment config:
  runtime cfg, branding assets, env template, Pi admin scripts,
  operator docs, nested ``pi-shutdown-api`` checkout.
* ``pibooth-project/pibooth`` — original upstream project. Not
  tracked for merges — see diff between this fork and
  ``upstream/master`` if you want the genealogy.

License
-------

MIT. Original copyright Vincent Verdeil and Antoine Rousseaux; fork
changes copyright Arron Lorenz. See ``LICENSE``.
