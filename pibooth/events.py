"""Event helper utilities."""

from dataclasses import dataclass
from typing import List, Optional

import pygame

from pibooth.utils import get_event_pos
from pibooth.printer import PRINTER_TASKS_UPDATED

#: Custom pygame event type fired by hardware button handlers.
#: Single source of truth — :mod:`pibooth.booth` imports this.
BUTTONDOWN = pygame.USEREVENT + 1


@dataclass
class EventInfo:
    quit: Optional[pygame.event.Event] = None
    settings: Optional[pygame.event.Event] = None
    fullscreen: Optional[pygame.event.Event] = None
    resize: Optional[pygame.event.Event] = None
    capture: Optional[pygame.event.Event] = None
    printer: Optional[pygame.event.Event] = None
    print_status: Optional[pygame.event.Event] = None
    choice: Optional[pygame.event.Event] = None


def analyze_events(
    events: List[pygame.event.Event],
    window,
    buttons,
    fingerdown_events: List[pygame.event.Event],
) -> EventInfo:
    """Iterate over ``events`` once and return an :class:`EventInfo`.

    A single ``BUTTONDOWN`` with both ``capture=1`` and ``printer=1``
    legitimately satisfies several slots (settings, capture, printer,
    choice). That's intentional: the main loop checks
    ``find_settings_event`` first and short-circuits, so the duplicate
    fills are inert in practice.
    """

    info = EventInfo()
    for event in events:
        if not info.quit and event.type == pygame.QUIT:
            info.quit = event
            continue

        if not info.settings:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                info.settings = event
            elif event.type == BUTTONDOWN and getattr(event, "capture", False) and getattr(event, "printer", False):
                info.settings = event
            elif event.type == pygame.FINGERDOWN:
                fingerdown_events.append(event)
            elif event.type == pygame.FINGERUP:
                fingerdown_events.clear()
            if not info.settings and len(fingerdown_events) > 3:
                fingerdown_events.clear()
                info.settings = pygame.event.Event(BUTTONDOWN, capture=1, printer=1, button=buttons)

        if not info.fullscreen and event.type == pygame.KEYDOWN and event.key == pygame.K_f and pygame.key.get_mods() & pygame.KMOD_CTRL:
            info.fullscreen = event

        if not info.resize and event.type == pygame.VIDEORESIZE:
            info.resize = event

        if not info.capture:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                info.capture = event
            elif (event.type == pygame.MOUSEBUTTONUP and event.button in (1, 2, 3)) or event.type == pygame.FINGERUP:
                pos = get_event_pos(window.display_size, event)
                rect = window.get_rect()
                if pygame.Rect(0, 0, rect.width // 2, rect.height).collidepoint(pos):
                    info.capture = event
            elif event.type == BUTTONDOWN and getattr(event, "capture", False):
                info.capture = event

        if not info.printer:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_e and pygame.key.get_mods() & pygame.KMOD_CTRL:
                info.printer = event
            elif (event.type == pygame.MOUSEBUTTONUP and event.button in (1, 2, 3)) or event.type == pygame.FINGERUP:
                pos = get_event_pos(window.display_size, event)
                rect = window.get_rect()
                if pygame.Rect(rect.width // 2, 0, rect.width // 2, rect.height).collidepoint(pos):
                    info.printer = event
            elif event.type == BUTTONDOWN and getattr(event, "printer", False):
                info.printer = event

        if not info.print_status and event.type == PRINTER_TASKS_UPDATED:
            info.print_status = event

        if not info.choice:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                info.choice = event
            elif (event.type == pygame.MOUSEBUTTONUP and event.button in (1, 2, 3)) or event.type == pygame.FINGERUP:
                pos = get_event_pos(window.display_size, event)
                rect = window.get_rect()
                key = pygame.K_LEFT if pygame.Rect(0, 0, rect.width // 2, rect.height).collidepoint(pos) else pygame.K_RIGHT
                info.choice = _with_key(event, key)
            elif event.type == BUTTONDOWN:
                key = pygame.K_LEFT if getattr(event, "capture", False) else pygame.K_RIGHT
                info.choice = _with_key(event, key)

    return info


def _with_key(event: pygame.event.Event, key: int) -> pygame.event.Event:
    """Return a copy of ``event`` augmented with a ``key`` attribute.

    Avoids mutating pygame Event objects in place (which is treated as
    immutable in modern pygame and raises AttributeError on some versions).
    """
    attrs = dict(event.__dict__)
    attrs["key"] = key
    return pygame.event.Event(event.type, attrs)
