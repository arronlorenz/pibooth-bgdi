# -*- coding: utf-8 -*-

"""A photo booth application in pure Python for the Raspberry Pi.

Originally derived from pibooth-project/pibooth 2.0.8 (Vincent Verdeil
and Antoine Rousseaux, MIT); significantly diverged as the Blue Grass
Drive-In fork at github.com/arronlorenz/pibooth-bgdi — Chevereto upload
plugin, serial-buttons bridge, shipped systemd/udev units, pibooth-doctor,
window-layer refactor, Python 3.11 / Pillow 10 modernization.
"""

__version__ = "3.0.0"

try:

    import pluggy

    # Marker to be imported and used in plugins (and for own implementations)
    hookimpl = pluggy.HookimplMarker('pibooth')

except ImportError:
    pass  # When running the setup.py, pluggy is not yet installed
