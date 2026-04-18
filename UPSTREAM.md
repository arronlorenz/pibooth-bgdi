# Upstream-worthy commits

This fork (`arronlorenz/pibooth-bgdi`) is 31 commits ahead of upstream
(`pibooth-project/pibooth`) as of 2026-04-18. Most of that divergence is
BGDI-specific stuff (AGENTS.md, diagnostic dumps, README badge updates)
that has no business upstream. A handful are genuine fixes or features
that the upstream maintainers would probably accept — tracking them here
so we don't lose the thread.

## Candidates for upstream PRs

| Commit | Description | Rationale |
|---|---|---|
| `88a5ffe` | Fix text sizing for Pillow 10 (`getsize` → `getbbox`) | Pillow 10 removed `ImageFont.getsize`; breaks upstream too on any modern install. |
| `1a2b919` | Fix `gp_log_callback` for str input + tests | gphoto2 can pass either bytes or str to the log callback; upstream currently assumes bytes and crashes on str. |
| `472f0cc` | Check `$EDITOR` env variable before default editors | Small QoL — respect the user's configured editor. |
| `46759b7` | Add picamera2 support | Raspberry Pi OS Bullseye/Bookworm ship picamera2 by default; legacy picamera is deprecated. Guarded with `try:/except ImportError:` so it doesn't break anyone. ⚠️ Fix `IMAGE_EFFECTS = ['none']` placeholder to a proper libcamera-based list before PR'ing. |
| `b39509f` | Add unified event parsing helper (`events.py`) and tests | Refactor that extracts the pygame event loop into a standalone module with a dataclass return type. Makes `booth.py` much more readable. PR the cleaned-up version — see `fix/events-py-bugs` PR on this fork for the incremental correctness fixes that should land before upstreaming. |

## Not upstream-worthy (keep in fork)

- `AGENTS.md` + `tests/dslr_diag/` — BGDI-specific dev-tooling
- Swedish translation tweak (`2127006`) — too narrow; pibooth's i18n flow probably wants a full transifex-style pass, not a one-off
- README badge / Python 3.9+ version bump (`a95f70f`, `8d08f32`) — upstream will have their own version policy
- Raspbian install doc updates (`08876a4`, `0834ff8`) — some of these might work as PRs, some are too local-phrasing; review individually before PR'ing
- Module-level docstrings commit (`1601812`) — one-line generic docstrings across 20 files; would need to be rewritten as actually-useful docstrings before upstream would take it

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
