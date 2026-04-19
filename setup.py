#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from io import open
import os.path as osp
from setuptools import setup, find_packages


HERE = osp.abspath(osp.dirname(__file__))
sys.path.insert(0, HERE)
import pibooth  # nopep8 : import shall be done after adding setup to paths


with open(osp.join(HERE, 'docs', 'requirements.txt')) as fd:
    docs_require = fd.read().splitlines()


def main():
    setup(
        name=pibooth.__name__,
        version=pibooth.__version__,
        description=pibooth.__doc__,
        long_description=open(osp.join(HERE, 'README.rst'), encoding='utf-8').read(),
        long_description_content_type='text/x-rst',
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: Other Environment',
            'Intended Audience :: Developers',
            'Intended Audience :: End Users/Desktop',
            'License :: OSI Approved :: MIT License',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Natural Language :: Danish',
            'Natural Language :: Dutch',
            'Natural Language :: English',
            'Natural Language :: French',
            'Natural Language :: German',
            'Natural Language :: Hungarian',
            'Natural Language :: Italian',
            'Natural Language :: Norwegian',
            'Natural Language :: Portuguese',
            'Natural Language :: Portuguese (Brazilian)',
            'Natural Language :: Spanish',
            'Topic :: Multimedia :: Graphics :: Capture :: Digital Camera',
        ],
        author="Vincent Verdeil, Antoine Rousseaux",
        url="https://github.com/pibooth/pibooth",
        download_url="https://github.com/pibooth/pibooth/archive/{}.tar.gz".format(pibooth.__version__),
        license='MIT license',
        platforms=['unix', 'linux'],
        keywords=[
            'Raspberry Pi',
            'camera',
            'photobooth'
        ],
        packages=find_packages(),
        package_data={
            'pibooth': ['*.ini'],
            'pibooth.fonts': ['*.ttf'],
            'pibooth.pictures': ['*/*.png'],
            'pibooth.share.udev': ['*.rules'],
            'pibooth.share.systemd': ['*.service', '*.timer'],
        },
        include_package_data=True,
        python_requires=">=3.7",
        install_requires=[
            # Pillow 10+ requires Python 3.8; the BGDI Pi is on 3.7.3. The
            # 9.x line supports 3.7 through 3.12 and pip will pick the
            # newest compatible release on each host. Bump the floor when
            # the Pi moves off Python 3.7.
            'Pillow>=9.2.0',
            # importlib.resources.files() was added in Python 3.9.
            # pibooth.scripts.install_udev / install_systemd need it to
            # locate shipped .rules / .service files; on 3.7–3.8 the
            # backport package provides the same API.
            'importlib_resources >= 5.0 ; python_version < "3.9"',
            'pygame>=1.9.6',
            'pygame-menu==4.0.7',
            'pygame-vkeyboard>=2.0.8',
            'psutil>=5.5.1',
            'pluggy>=0.13.1',
            'gpiozero>=1.5.1',
            # RPi.GPIO backend for gpiozero (not always installed by
            # default). PEP 508 `>=` / `<=` are *version* comparisons,
            # not string comparisons — the previous "armv0l..armv9l"
            # range silently evaluated to False on every architecture
            # because those strings aren't valid PEP 440 versions. List
            # the supported machines explicitly. armv6l = Pi Zero/1,
            # armv7l = Pi 2/3 in 32-bit mode, aarch64 = any Pi running
            # 64-bit Raspberry Pi OS (including the BGDI Buster booth).
            'RPi.GPIO>=0.7.0 ; platform_machine == "aarch64" or platform_machine == "armv7l" or platform_machine == "armv6l"'
        ],
        extras_require={
            'dslr': ['gphoto2>=2.0.0'],
            'printer': ['pycups>=1.9.73', 'pycups-notify>=0.0.4'],
            'chevereto': ['requests>=2.28'],
            'serial-buttons': ['pyserial>=3.4', 'python-uinput>=0.11.2'],
            'doc': docs_require
        },
        zip_safe=False,  # Don't install the lib as an .egg zipfile
        entry_points={
            'console_scripts': ["pibooth = pibooth.booth:main",
                                "pibooth-count = pibooth.scripts.count:main",
                                "pibooth-diag = pibooth.scripts.diagnostic:main",
                                "pibooth-fonts = pibooth.scripts.fonts:main",
                                "pibooth-regen = pibooth.scripts.regenerate:main",
                                "pibooth-printcfg = pibooth.scripts.printer:main",
                                "pibooth-chevereto = pibooth.plugins.chevereto.uploader:main",
                                "pibooth-serial-buttons = pibooth.plugins.serial_buttons.cli:main",
                                "pibooth-install-udev = pibooth.scripts.install_udev:main",
                                "pibooth-install-systemd = pibooth.scripts.install_systemd:main",
                                "pibooth-doctor = pibooth.scripts.doctor:main"],
            # Pibooth's plugin manager discovers external plugins from this
            # entry-point group — it calls `load_setuptools_entrypoints("pibooth")`.
            # Users opt in with `pip install pibooth[chevereto]`.
            'pibooth': ["chevereto = pibooth.plugins.chevereto.plugin"],
        },
    )


if __name__ == '__main__':
    main()
