# -*- coding: utf-8 -*-

"""``pibooth-install-udev`` — copy shipped udev rules into ``/etc/udev/rules.d/``.

Which rules get installed depends on which pibooth extras are present:

- ``90-no-camera-automount.rules`` — always installed; makes the DE stop
  grabbing the DSLR as USB storage so libgphoto2 can open it.
- ``99-serial-uinput.rules`` — installed only if ``pibooth[serial-buttons]``
  is importable, i.e. the button-bridge extra is in use.

Must be run as root. Triggers ``udevadm control --reload-rules`` and
``udevadm trigger`` after copying so the rules take effect immediately.
"""

import argparse
import os
import shutil
import subprocess
import sys

try:
    from importlib.resources import files as _files  # Py 3.9+
except ImportError:  # pragma: no cover — Py 3.7/3.8 fallback
    from importlib_resources import files as _files  # type: ignore[no-redef]


DEST_DIR = "/etc/udev/rules.d"


def _have_extra_script(console_script):
    """A pibooth extra is installed iff pip wrote its console script to disk."""
    return shutil.which(console_script) is not None


def _shipped_rule(filename):
    return _files("pibooth.share.udev").joinpath(filename)


def _copy(src, dst, dry_run):
    print("  {} -> {}".format(src, dst))
    if not dry_run:
        shutil.copy(src, dst)
        os.chmod(dst, 0o644)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be installed without touching the filesystem.")
    parser.add_argument("--no-reload", action="store_true",
                        help="Skip `udevadm control --reload-rules` + `udevadm trigger`.")
    args = parser.parse_args()

    if not args.dry_run and os.geteuid() != 0:
        print("pibooth-install-udev: must run as root (try: sudo pibooth-install-udev)",
              file=sys.stderr)
        return 2

    rules = [("90-no-camera-automount.rules", True)]
    # Install the serial-buttons rule iff the extra's console script is
    # on disk. That's the strongest signal pip ran with the extra and
    # both pyserial + python-uinput are present (the bridge needs both).
    rules.append(("99-serial-uinput.rules",
                  _have_extra_script("pibooth-serial-buttons")))

    print("Installing udev rules into", DEST_DIR)
    installed_any = False
    for name, enabled in rules:
        if not enabled:
            print("  skip {} (pibooth[serial-buttons] not installed)".format(name))
            continue
        src = str(_shipped_rule(name))
        dst = os.path.join(DEST_DIR, name)
        _copy(src, dst, args.dry_run)
        installed_any = True

    if installed_any and not args.no_reload and not args.dry_run:
        subprocess.check_call(["udevadm", "control", "--reload-rules"])
        subprocess.check_call(["udevadm", "trigger"])
        print("udev rules reloaded.")
    elif args.dry_run:
        print("(dry run — nothing written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
