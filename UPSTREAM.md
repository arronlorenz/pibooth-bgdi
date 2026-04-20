# Upstream-worthy commits

This fork (`arronlorenz/pibooth-bgdi`) has diverged significantly from
upstream (`pibooth-project/pibooth`). Upstream is dormant — 2.0.8 is
the latest release (2023-07, 21+ months stale). Most of the fork's
divergence is BGDI-specific stuff (AGENTS.md, diagnostic dumps, README
badge updates, Chevereto plugin, serial-buttons bridge, systemd units
as package data) that has no business upstream. A handful are generic
fixes or features the upstream maintainers would probably accept —
tracking them here so we don't lose the thread.

> **Operator note (2026-04-20)**: the user has no current plan to
> open upstream PRs — see
> `~/.claude/.../memory/upstream_publishing_preference.md`. This
> doc is kept as context, not as a todo list.

## Candidates for upstream PRs

| Commit | Description | Rationale |
|---|---|---|
| `2aba90c` | **Pillow 10 / Python 3.11 / pygame-menu 4.5.2 modernization**. Migrates `Image.ROTATE_*`/`FLIP_LEFT_RIGHT` → `Image.Transpose.*`; `textsize`/`getsize` → `getbbox` everywhere; drops `Resampling` shim; bumps floors. | Upstream's master still has the same Pillow 10 breakage the earlier `88a5ffe` partially fixed. This commit is the exhaustive version. |
| `1a2b919` | Fix `gp_log_callback` for str input + tests | gphoto2 can pass either bytes or str to the log callback; upstream currently assumes bytes and crashes on str. |
| `472f0cc` | Check `$EDITOR` env variable before default editors | Small QoL — respect the user's configured editor. |
| `46759b7` | Add picamera2 support | Raspberry Pi OS Bullseye/Bookworm ship picamera2 by default; legacy picamera is deprecated. Guarded with `try:/except ImportError:` so it doesn't break anyone. ⚠️ Fix `IMAGE_EFFECTS = ['none']` placeholder to a proper libcamera-based list before PR'ing. ⚠️ Also: the BGDI fork dropped the picamera paths entirely in the 2026-04-19 code review sweep, so this commit would need to be re-extracted from history before upstreaming. |
| `b39509f` | Add unified event parsing helper (`events.py`) and tests | Refactor that extracts the pygame event loop into a standalone module with a dataclass return type. Makes `booth.py` much more readable. PR the cleaned-up version — see `fix/events-py-bugs` PR on this fork for the incremental correctness fixes that should land before upstreaming. |
| `ce9f6e8` / `7d84e9a` | **Window/render layer refactor**: StateMachine baseline surface clear, xrandr-based crash recovery, worker-pool processing (no main-loop freeze during factory build). | Generic framework improvements — not BGDI-specific. Would need splitting into 3 PRs (surface contract / crash recovery / worker pool) per the upstream maintainers' preference for focused PRs. |

## Not upstream-worthy (keep in fork)

- `AGENTS.md` + `tests/dslr_diag/` — BGDI-specific dev-tooling
- Swedish translation tweak (`2127006`) — too narrow; pibooth's i18n flow probably wants a full transifex-style pass, not a one-off
- Python 3.11 floor bump — upstream will have their own version
  policy; we bumped because the BGDI Pi is moving to Bookworm
- Raspbian install doc updates (`08876a4`, `0834ff8`) — some of these might work as PRs, some are too local-phrasing; review individually before PR'ing
- Module-level docstrings commit (`1601812`) — one-line generic docstrings across 20 files; would need to be rewritten as actually-useful docstrings before upstream would take it
- Chevereto plugin, serial-buttons bridge, shipped systemd units /
  udev rules as package data, `pibooth-doctor`, `pibooth-install-*`
  console scripts — all BGDI-specific deploy infrastructure, no
  upstream equivalent and unlikely to be accepted as-is

## Workflow for upstreaming each item

```
# From the fork, on master:
git fetch upstream
git checkout -b upstream/<topic> upstream/master
git cherry-pick <sha>
# Fix up / rebase / refresh tests as needed
git push origin upstream/<topic>
gh pr create --repo pibooth-project/pibooth --base master --head arronlorenz:upstream/<topic>
```

Keep each upstream PR to a single logical change — upstream maintainers
are more likely to merge focused PRs than "here's 5 fixes in one PR".
