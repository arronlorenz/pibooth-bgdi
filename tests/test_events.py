import pygame
import types

from pibooth.events import analyze_events, BUTTONDOWN
from pibooth.printer import PRINTER_TASKS_UPDATED

class DummyWindow:
    def __init__(self):
        self.display_size = (800, 600)
    def get_rect(self):
        return pygame.Rect(0, 0, 800, 600)


def test_analyze_events_extracts_flags(monkeypatch):
    pygame.init()
    pygame.key.set_mods(pygame.KMOD_CTRL)

    events = [
        pygame.event.Event(pygame.QUIT),
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f),
        pygame.event.Event(pygame.VIDEORESIZE, size=(1024, 768)),
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p),
        pygame.event.Event(BUTTONDOWN, capture=1),
        pygame.event.Event(BUTTONDOWN, printer=1),
        pygame.event.Event(PRINTER_TASKS_UPDATED),
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT),
    ]

    info = analyze_events(events, DummyWindow(), object(), [])

    assert info.quit.type == pygame.QUIT
    assert info.settings.key == pygame.K_ESCAPE
    assert info.fullscreen.key == pygame.K_f
    assert info.resize.size == (1024, 768)
    assert info.capture.key == pygame.K_p
    assert info.printer.type == BUTTONDOWN
    assert info.print_status.type == PRINTER_TASKS_UPDATED
    assert info.choice.key == pygame.K_LEFT
    pygame.key.set_mods(0)
