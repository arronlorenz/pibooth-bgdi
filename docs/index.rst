
Welcome to pibooth-bgdi documentation
=====================================

The ``pibooth`` package shipped here is the **Blue Grass Drive-In**
fork of `pibooth-project/pibooth
<https://github.com/pibooth/pibooth>`_ 2.0.8. Upstream has been
dormant since 2023-07; this fork has diverged significantly (Python
3.11 floor, Chevereto plugin, serial-buttons bridge, shipped
systemd/udev units, window-layer refactor).

For general-purpose pibooth documentation, refer to the original
upstream wiki. The rest of these docs cover the API surface that
survived from upstream; deploy recipes + BGDI-specific layout +
operator cheatsheets live in the ``pibooth-extras`` sibling repo.

.. image:: images/background_samples.png
   :align: center
   :alt: Background samples

.. note:: Even if designed for a Raspberry Pi, this software may be installed on
          any Unix/Linux based OS (tested on Ubuntu 16 and Mac OSX 10.14.6).

.. image:: images/gallery.png
   :align: center
   :alt: Gallery
   :target: sources/examples.html

.. toctree::
   :caption: About
   :maxdepth: 2

   sources/about.rst
   sources/examples.rst

.. toctree::
   :caption: Install
   :maxdepth: 2

   sources/install.rst

.. toctree::
   :caption: Start
   :maxdepth: 2

   sources/start.rst
   sources/config/config.rst
   sources/tutorials/dslr_tips.rst

.. toctree::
   :caption: Scripts and tools
   :maxdepth: 2

   sources/scripts.rst

.. toctree::
   :caption: Plugins
   :maxdepth: 2

   sources/plugins/plugins.rst
   sources/plugins/hooks.rst
   sources/plugins/examples.rst

.. toctree::
   :caption: Developers
   :hidden:

   sources/dev/install.rst
   sources/dev/rules.rst
   sources/dev/release.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. |Pibooth| image:: pibooth.png
   :target: https://www.pibooth.org
   :align: middle

.. |PythonVersions| image:: https://img.shields.io/badge/python-3.7+-red.svg
   :target: https://www.python.org/downloads
   :alt: Python 3.7+

.. |PypiPackage| image:: https://badge.fury.io/py/pibooth.svg
   :target: https://pypi.org/project/pibooth
   :alt: PyPi package

.. |Downloads| image:: https://img.shields.io/pypi/dm/pibooth?color=purple
   :target: https://pypi.org/project/pibooth
   :alt: PyPi downloads
