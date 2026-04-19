# -*- coding: utf-8 -*-

"""``pibooth-doctor`` — preflight health check for a pibooth deployment.

Walks the chain from "is pibooth installed?" through "can it actually
run on this Pi?": extras, gphoto2, udev rules, systemd units,
``/etc/pibooth.env`` contents and permissions, captures directory,
group membership.

Exits 0 if every check passed (warnings are OK), 1 if anything failed.
``--json`` emits a machine-readable report for ``piadmin/setup.sh`` to
consume at postflight.

Each check produces a structured result:
  status: "pass" | "warn" | "fail"
  label:  short human description
  detail: one-line finding
  fix:    concrete next-step command, if applicable
"""

import argparse
import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys


PASS, WARN, FAIL = "pass", "warn", "fail"


def _result(status, label, detail="", fix=""):
    return {"status": status, "label": label, "detail": detail, "fix": fix}


# ─── checks ──────────────────────────────────────────────────────────────────

def check_pibooth_import():
    try:
        import pibooth  # noqa: F401
        return _result(PASS, "pibooth importable",
                       "version={}".format(getattr(pibooth, "__version__", "?")))
    except ImportError as exc:
        return _result(FAIL, "pibooth importable",
                       str(exc),
                       "pip3 install --user '.[dslr,chevereto,serial-buttons]' from the pibooth-bgdi checkout")


def check_extras():
    """Report which optional extras are importable (not a pass/fail)."""
    present = []
    missing = []
    for name, mod in [("chevereto", "pibooth.plugins.chevereto"),
                      ("serial-buttons", "pibooth.plugins.serial_buttons")]:
        if importlib.util.find_spec(mod):
            present.append(name)
        else:
            missing.append(name)
    return _result(PASS, "pibooth extras",
                   "installed: {}; missing: {}".format(
                       ", ".join(present) or "(none)",
                       ", ".join(missing) or "(none)"))


def check_gphoto2():
    if not shutil.which("gphoto2"):
        return _result(FAIL, "gphoto2 binary",
                       "not installed",
                       "sudo apt install gphoto2 (or piadmin/install-latest-gphoto2.sh for a newer version)")
    try:
        out = subprocess.check_output(["gphoto2", "--auto-detect"], text=True,
                                      stderr=subprocess.STDOUT, timeout=10)
    except subprocess.CalledProcessError as exc:
        first_line = (exc.output or "").splitlines()[:1]
        return _result(FAIL, "gphoto2 --auto-detect",
                       "errored out: {}".format(first_line[0] if first_line else "(no output)"),
                       "sudo piadmin/install-latest-gphoto2.sh")
    except subprocess.TimeoutExpired:
        return _result(FAIL, "gphoto2 --auto-detect",
                       "hung — packaged version may be too old for the DSLR's PTP dialect",
                       "sudo piadmin/install-latest-gphoto2.sh")
    # Parse by locating the `-----` separator line rather than assuming
    # fixed line count — gphoto2 sometimes prints libusb/locale warnings
    # before the "Model   Port" banner.
    rows = []
    after_sep = False
    for ln in out.splitlines():
        if after_sep:
            if ln.strip():
                rows.append(ln)
        elif "----" in ln:
            after_sep = True
    if not rows:
        return _result(WARN, "gphoto2 --auto-detect",
                       "no DSLR detected (fine if none is plugged in right now)",
                       "plug in the DSLR and re-run, or sudo piadmin/install-latest-gphoto2.sh if it's connected but invisible")
    return _result(PASS, "gphoto2 --auto-detect",
                   "sees {} camera(s)".format(len(rows)))


def check_udev_rules():
    required = [("/etc/udev/rules.d/90-no-camera-automount.rules", True)]
    if importlib.util.find_spec("pibooth.plugins.serial_buttons"):
        required.append(("/etc/udev/rules.d/99-serial-uinput.rules", True))

    missing = [p for p, _ in required if not os.path.exists(p)]
    if missing:
        return _result(FAIL, "udev rules",
                       "missing: " + ", ".join(missing),
                       "sudo pibooth-install-udev")
    return _result(PASS, "udev rules",
                   "{} installed".format(len(required)))


def _systemctl(*args):
    try:
        return subprocess.check_output(["systemctl"] + list(args), text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def check_systemd_units():
    units = [("pibooth.service", True)]
    if importlib.util.find_spec("pibooth.plugins.serial_buttons"):
        units.append(("pibooth-buttons.service", True))
    if importlib.util.find_spec("pibooth.plugins.chevereto"):
        units.append(("pibooth-uploader.service", True))
        units.append(("pibooth-uploader.timer", True))

    missing = []
    inactive = []
    for name, _ in units:
        unit_path = "/etc/systemd/system/{}".format(name)
        if not os.path.exists(unit_path):
            missing.append(name)
            continue
        state = _systemctl("is-enabled", name)
        if state not in ("enabled", "static", "alias"):
            inactive.append("{} (is-enabled={})".format(name, state or "unknown"))

    if missing:
        return _result(FAIL, "systemd units",
                       "missing: " + ", ".join(missing),
                       "sudo pibooth-install-systemd")
    if inactive:
        return _result(WARN, "systemd units",
                       "present but not enabled: " + ", ".join(inactive),
                       "sudo systemctl enable --now " + " ".join(
                           u.split()[0] for u in inactive))
    return _result(PASS, "systemd units", "{} present + enabled".format(len(units)))


def check_pibooth_env():
    path = "/etc/pibooth.env"
    if not os.path.exists(path):
        return _result(FAIL, "/etc/pibooth.env",
                       "missing",
                       "sudo cp piadmin/pibooth.env.example /etc/pibooth.env && sudoedit /etc/pibooth.env")

    st = os.stat(path)
    mode = st.st_mode & 0o777
    if mode != 0o600:
        return _result(WARN, "/etc/pibooth.env permissions",
                       "mode={:o} (want 600)".format(mode),
                       "sudo chmod 600 /etc/pibooth.env")

    env = _parse_env_file(path)
    if env.get("_unreadable"):
        # File exists at 0600 but this process can't read it (e.g. doctor
        # run as `pi`, env file owned root:root). Don't misreport the key
        # as empty — acknowledge we can't check its content.
        return _result(WARN, "/etc/pibooth.env content",
                       "file exists and is 0600 but not readable by the current user; content check skipped",
                       "sudo pibooth-doctor  (or re-check after 'sudo cat /etc/pibooth.env | grep CHEVERETO_API_KEY')")

    api_key = env.get("CHEVERETO_API_KEY", "")
    if not api_key or api_key == "REPLACE_ME":
        return _result(FAIL, "/etc/pibooth.env secret",
                       "CHEVERETO_API_KEY is empty or REPLACE_ME",
                       "sudoedit /etc/pibooth.env (fill in the real key from Chevereto Dashboard → API)")
    return _result(PASS, "/etc/pibooth.env", "exists, 0600, CHEVERETO_API_KEY populated")


def _parse_env_file(path):
    """Parse KEY=value lines with an optional 'export' prefix and quoted values."""
    try:
        with open(path) as f:
            content = f.read()
    except PermissionError:
        # File exists but we can't read it (not root); don't block the report.
        return {"_unreadable": True}

    env = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
            v = v[1:-1]
        env[k.strip()] = v
    return env


def check_captures_dir():
    path = "/etc/pibooth.env"
    captures_dir = ""
    if os.path.exists(path):
        env = _parse_env_file(path)
        captures_dir = env.get("CHEVERETO_CAPTURES_DIR", "")
    if not captures_dir:
        captures_dir = os.path.expanduser("~/Pictures/pibooth")

    if not os.path.isdir(captures_dir):
        return _result(FAIL, "captures directory",
                       "{} does not exist".format(captures_dir),
                       "mkdir -p {} && chown pi:pi {}".format(captures_dir, captures_dir))
    if not os.access(captures_dir, os.W_OK):
        return _result(FAIL, "captures directory",
                       "{} not writable by current user".format(captures_dir),
                       "sudo chown pi:pi {}".format(captures_dir))
    return _result(PASS, "captures directory",
                   "{} exists + writable".format(captures_dir))


def check_user_groups():
    # Use the real uid rather than $USER — under sudo without -E,
    # $USER may be unset or stale, which misreports membership.
    try:
        import pwd
        user = pwd.getpwuid(os.getuid()).pw_name
    except Exception as exc:
        return _result(WARN, "user groups", "could not resolve current user: {}".format(exc))
    try:
        import grp
        groups = {g.gr_name for g in grp.getgrall() if user in g.gr_mem}
    except Exception as exc:
        return _result(WARN, "user groups", "lookup failed: {}".format(exc))

    need = {"dialout", "input", "video", "plugdev"}
    missing = sorted(need - groups)
    if missing:
        return _result(WARN, "user groups",
                       "{} missing from: {}".format(user, ", ".join(missing)),
                       "sudo usermod -a -G {} {}  (then log out + back in)".format(
                           ",".join(missing), user))
    return _result(PASS, "user groups", "{} is in dialout, input, video, plugdev".format(user))


ALL_CHECKS = [
    check_pibooth_import,
    check_extras,
    check_gphoto2,
    check_udev_rules,
    check_systemd_units,
    check_pibooth_env,
    check_captures_dir,
    check_user_groups,
]


# ─── output ──────────────────────────────────────────────────────────────────

COLOR = {PASS: "\033[32m", WARN: "\033[33m", FAIL: "\033[31m"}
RESET = "\033[0m"
SIGIL = {PASS: "✓", WARN: "!", FAIL: "✗"}


def _print_human(results, use_color):
    for r in results:
        sigil = SIGIL[r["status"]]
        if use_color:
            sigil = COLOR[r["status"]] + sigil + RESET
        print("  {} {:<28} {}".format(sigil, r["label"], r["detail"]))
        if r["fix"] and r["status"] != PASS:
            print("      fix: {}".format(r["fix"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true",
                        help="Emit results as JSON (for piadmin/setup.sh postflight).")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors in human output.")
    args = parser.parse_args()

    results = []
    for check in ALL_CHECKS:
        try:
            results.append(check())
        except Exception as exc:
            results.append(_result(FAIL, check.__name__, "check raised: {}".format(exc)))

    if args.json:
        print(json.dumps({"results": results}, indent=2))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        print("pibooth-doctor — {} checks".format(len(results)))
        _print_human(results, use_color)
        counts = {PASS: 0, WARN: 0, FAIL: 0}
        for r in results:
            counts[r["status"]] += 1
        print()
        print("  summary: {} pass · {} warn · {} fail".format(
            counts[PASS], counts[WARN], counts[FAIL]))

    return 1 if any(r["status"] == FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
