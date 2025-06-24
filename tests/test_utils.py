import os
import subprocess
from pibooth.utils import open_text_editor


def test_open_text_editor_uses_env(monkeypatch):
    calls = []

    class DummyProc:
        def __init__(self, cmd):
            self.cmd = cmd
            calls.append(cmd)
            self.returncode = 0

        def communicate(self):
            return (b"", b"")

    def fake_popen(cmd):
        return DummyProc(cmd)

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setenv("EDITOR", "myeditor")

    assert open_text_editor("file.txt")
    assert calls[0][0] == "myeditor"
    assert len(calls) == 1

