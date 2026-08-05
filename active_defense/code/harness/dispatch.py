"""Forward a dataset entry point to one harness implementation.

The entries in ``code/run_<dataset>*.py`` are the whole invocation surface: they
select an implementation and forward every remaining flag unchanged, so each
harness keeps its own CLI.

Switch handling is deliberately manual rather than argparse-based: argparse
would consume ``--help`` at the entry, and the useful behavior is
``run_scr.py --help`` listing the suites while
``run_scr.py --suite capflow --help`` shows that suite's own flags.
"""
from __future__ import annotations

import pathlib
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def ensure_root_on_path() -> None:
    """Allow ``python code/run_<dataset>.py`` without setting PYTHONPATH."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


def forward(module: str, rest) -> None:
    """Run one harness module exactly as if it had been invoked directly."""
    ensure_root_on_path()
    sys.argv = [module, *rest]
    runpy.run_module(module, run_name="__main__")


def _split(argv, flag: str):
    """Pull the switch out of ``argv``; everything else is forwarded."""
    selected, rest, index = None, [], 0
    while index < len(argv):
        item = argv[index]
        if item == flag and index + 1 < len(argv):
            selected, index = argv[index + 1], index + 2
            continue
        if item.startswith(flag + "="):
            selected, index = item.split("=", 1)[1], index + 1
            continue
        rest.append(item)
        index += 1
    return selected, rest


def entry(description: str, choices: dict, flag: str = "--defense",
          default: str | None = None) -> None:
    """Select an implementation with one switch and forward the rest."""
    selected, rest = _split(sys.argv[1:], flag)
    if selected is None:
        selected = default
    if selected in choices:
        forward(choices[selected], rest)
        return
    name = pathlib.Path(sys.argv[0]).name
    options = "|".join(sorted(choices))
    print(f"{description}\n")
    print(f"usage: {name} {flag} {{{options}}} [implementation flags]\n")
    print(f"Add {flag} <choice> --help to see that implementation's own flags.")
    asked_for_help = {"-h", "--help"} & set(rest)
    raise SystemExit(0 if asked_for_help or selected is None else 2)
