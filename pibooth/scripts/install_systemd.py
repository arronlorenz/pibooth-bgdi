# -*- coding: utf-8 -*-

"""``pibooth-install-systemd`` — copy shipped systemd units into
``/etc/systemd/system/``.

Which units get installed depends on which pibooth extras are present:

- ``pibooth.service`` — always installed; runs the main app.
- ``pibooth-buttons.service`` — if ``pibooth[serial-buttons]`` is in use.
- ``pibooth-uploader.service`` + ``pibooth-uploader.timer`` — if
  ``pibooth[chevereto]`` is in use.

Must be run as root. Triggers ``systemctl daemon-reload`` after copying.
Does NOT enable or start anything — the operator decides which units
to turn on.
"""

import argparse
import os
import shutil
import subprocess
import sys

try:
    from importlib.resources import files as _files
except ImportError:  # pragma: no cover
    from importlib_resources import files as _files  # type: ignore[no-redef]


DEST_DIR = "/etc/systemd/system"


def _have_extra_script(console_script):
    """A pibooth extra is installed iff pip wrote its console script to disk."""
    return shutil.which(console_script) is not None


def _shipped_unit(filename):
    return _files("pibooth.share.systemd").joinpath(filename)


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
                        help="Skip `systemctl daemon-reload`.")
    args = parser.parse_args()

    if not args.dry_run and os.geteuid() != 0:
        print("pibooth-install-systemd: must run as root (try: sudo pibooth-install-systemd)",
              file=sys.stderr)
        return 2

    # Gate each extra's units on the presence of its console script.
    # The pibooth.plugins.<extra> packages ship in-tree even without
    # the extra installed, so a `find_spec` check would false-positive.
    # The console script only lands when `pip install 'pibooth[<x>]'`
    # ran, which also guarantees the runtime deps (pyserial+uinput,
    # requests, …) are present.
    units = [
        ("pibooth.service", True, None),
        ("pibooth-buttons.service",
         _have_extra_script("pibooth-serial-buttons"),
         "pibooth[serial-buttons]"),
        ("pibooth-uploader.service",
         _have_extra_script("pibooth-chevereto"),
         "pibooth[chevereto]"),
        ("pibooth-uploader.timer",
         _have_extra_script("pibooth-chevereto"),
         "pibooth[chevereto]"),
    ]

    print("Installing systemd units into", DEST_DIR)
    installed_any = False
    for name, enabled, extra in units:
        if not enabled:
            print("  skip {} ({} not installed)".format(name, extra))
            continue
        src = str(_shipped_unit(name))
        dst = os.path.join(DEST_DIR, name)
        _copy(src, dst, args.dry_run)
        installed_any = True

    if installed_any and not args.no_reload and not args.dry_run:
        subprocess.check_call(["systemctl", "daemon-reload"])
        print("systemd reloaded. Enable the units you want with:")
        print("  sudo systemctl enable --now pibooth")
        print("  sudo systemctl enable --now pibooth-buttons     # if installed")
        print("  sudo systemctl enable --now pibooth-uploader.timer  # if installed")
    elif args.dry_run:
        print("(dry run — nothing written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
