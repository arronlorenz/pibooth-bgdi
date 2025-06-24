import importlib
import types
from pibooth.camera import rpi

def test_no_camera_lib(monkeypatch):
    monkeypatch.setattr(rpi, 'Picamera2', None)
    monkeypatch.setattr(rpi, 'picamera', None)
    assert rpi.get_rpi_camera_proxy() is None
