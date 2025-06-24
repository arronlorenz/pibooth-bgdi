# -*- coding: utf-8 -*-

"""Camera backend for the Raspberry Pi Camera Module."""

import time
import subprocess
from io import BytesIO
from PIL import Image
try:
    # New libcamera based implementation
    from picamera2 import Picamera2, Preview
except Exception:  # pragma: no cover - optional dependency can fail to import
    Picamera2 = None
    Preview = None
try:
    import picamera
except ImportError:  # pragma: no cover - optional dependency
    picamera = None  # picamera is optional
from pibooth.language import get_translated_text
from pibooth.camera.base import BaseCamera


def get_rpi_camera_proxy(port=None):
    """Return a camera proxy for Raspberry Pi cameras.

    The function first tries to instantiate a ``Picamera2`` object when the
    library is available. If this fails or ``picamera2`` is not installed, the
    legacy :mod:`picamera` library is used as a fallback. When no compatible
    library is found or no camera is detected, ``None`` is returned.

    :param port: look on given port number
    :type port: int
    """
    try:
        process = subprocess.Popen(['vcgencmd', 'get_camera'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _ = process.communicate()
        if not stdout or u'detected=1' not in stdout.decode('utf-8'):
            return None
    except OSError:
        return None

    if Picamera2:
        try:
            return Picamera2()
        except Exception:
            pass

    if picamera:
        try:
            if port is not None:
                return picamera.PiCamera(camera_num=port)
            return picamera.PiCamera()
        except Exception:
            pass

    return None


class RpiCamera(BaseCamera):

    """Camera management supporting ``picamera2`` and ``picamera`` backends."""

    if picamera:
        _PICAMERA_EFFECTS = list(picamera.PiCamera.IMAGE_EFFECTS.keys())
    else:  # pragma: no cover - picamera not installed
        _PICAMERA_EFFECTS = []

    IMAGE_EFFECTS = _PICAMERA_EFFECTS

    def __init__(self, camera_proxy):
        super(RpiCamera, self).__init__(camera_proxy)
        if Picamera2 and isinstance(camera_proxy, Picamera2):
            self._backend = 'picamera2'
            self.IMAGE_EFFECTS = ['none']
        else:
            self._backend = 'picamera'
    def _specific_initialization(self):
        """Camera initialization."""
        if self._backend == 'picamera2':
            config = self._cam.create_still_configuration(main={'size': self.resolution})
            self._cam.configure(config)
            self._cam.start()
        else:
            self._cam.framerate = 15  # Slower is necessary for high-resolution
            self._cam.video_stabilization = True
            self._cam.vflip = False
            self._cam.hflip = self.capture_flip
            self._cam.resolution = self.resolution
            self._cam.iso = self.preview_iso
            self._cam.rotation = self.preview_rotation

    def _show_overlay(self, text, alpha):
        """Add an image as an overlay."""
        if self._backend == 'picamera' and self._window:
            rect = self.get_rect(self._cam.MAX_RESOLUTION)

            # Create an image padded to the required size (required by picamera)
            size = (((rect.width + 31) // 32) * 32, ((rect.height + 15) // 16) * 16)

            image = self.build_overlay(size, str(text), alpha)
            self._overlay = self._cam.add_overlay(image.tobytes(), image.size, layer=3,
                                                  window=tuple(rect), fullscreen=False)

    def _hide_overlay(self):
        """Remove any existing overlay.
        """
        if self._backend == 'picamera' and self._overlay:
            self._cam.remove_overlay(self._overlay)
            self._overlay = None

    def _post_process_capture(self, capture_data):
        """Rework capture data."""
        if self._backend == 'picamera2':
            return capture_data
        capture_data.seek(0)
        return Image.open(capture_data)

    def preview(self, window, flip=True):
        """Display a preview on the given Rect (flip if necessary).
        """
        if self._cam.preview is not None:
            # Already running
            return

        if self._backend == 'picamera2':
            self._window = window
            if not getattr(self._cam, 'started', False):
                self._cam.start_preview(Preview.NULL)
        else:
            self._window = window
            rect = self.get_rect(self._cam.MAX_RESOLUTION)
            if self._cam.hflip:
                if flip:
                    flip = False
                else:
                    flip = True
            self._cam.start_preview(resolution=(rect.width, rect.height), hflip=flip,
                                    fullscreen=False, window=tuple(rect))

    def preview_countdown(self, timeout, alpha=60):
        """Show a countdown of `timeout` seconds on the preview.
        Returns when the countdown is finished.
        """
        timeout = int(timeout)
        if timeout < 1:
            raise ValueError("Start time shall be greater than 0")
        if self._backend == 'picamera' and not self._cam.preview:
            raise EnvironmentError("Preview shall be started first")

        while timeout > 0:
            self._show_overlay(timeout, alpha)
            time.sleep(1)
            timeout -= 1
            self._hide_overlay()

        self._show_overlay(get_translated_text('smile'), alpha)

    def preview_wait(self, timeout, alpha=60):
        """Wait the given time.
        """
        time.sleep(timeout)
        self._show_overlay(get_translated_text('smile'), alpha)

    def stop_preview(self):
        """Stop the preview.
        """
        if self._backend == 'picamera':
            self._hide_overlay()
            self._cam.stop_preview()
        self._window = None

    def capture(self, effect=None):
        """Capture a new picture in a file.
        """
        effect = str(effect).lower()
        if effect not in self.IMAGE_EFFECTS:
            raise ValueError("Invalid capture effect '{}' (choose among {})".format(effect, self.IMAGE_EFFECTS))

        if self._backend == 'picamera2':
            image = Image.fromarray(self._cam.capture_array())
            self._captures.append(image)
        else:
            try:
                if self.capture_iso != self.preview_iso:
                    self._cam.iso = self.capture_iso
                if self.capture_rotation != self.preview_rotation:
                    self._cam.rotation = self.capture_rotation

                stream = BytesIO()
                self._cam.image_effect = effect
                self._cam.capture(stream, format='jpeg')

                if self.capture_iso != self.preview_iso:
                    self._cam.iso = self.preview_iso
                if self.capture_rotation != self.preview_rotation:
                    self._cam.rotation = self.preview_rotation

                self._captures.append(stream)
            finally:
                self._cam.image_effect = 'none'

            self._hide_overlay()  # If stop_preview() has not been called

    def quit(self):
        """Close the camera driver, it's definitive.
        """
        self._cam.close()
