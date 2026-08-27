"""
SKIP-filtering.

This module exists because of one confirmed bug: JEOL's SKIP-filtering
code removed items from a list while iterating over it
(`for x in items: if is_skip(x): items.remove(x)`), which silently lets a
SKIP'd entry survive when two or more SKIPs are adjacent — and, worse, can
leave one survivor behind even when every entry in a run is SKIP'd.

The fix is structural, not just "patch this one call site": build a new
list via a comprehension and never mutate the list you're iterating over.
Every source (Bruker, JEOL) should go through `filter_skip` here instead
of writing its own loop, so this mistake can't be reintroduced piecemeal.

Note the two SKIP semantics documented in the manifest are NOT the same
thing even though they're the identical string:
  - chosenSpectra SKIP = the user explicitly excluded this spectrum.
  - Bruker's exptIdentifiers SKIP = the auto-classifier couldn't recognize
    this raw experiment's type (nothing to do with user choice).
`filter_skip` is generic; callers decide what "is_skip" means for their
list via the predicate they pass in. exptIdentifiers should generally NOT
be filtered at all (see spectra.py) — it's meant to carry every entry,
SKIP included.
"""

from __future__ import annotations

from typing import Callable, Sequence, TypeVar

from .constants import SKIP_TOKEN

T = TypeVar("T")


def is_skip_string(entry: str, skip_token: str = SKIP_TOKEN) -> bool:
    """True if the last whitespace-delimited token of `entry` is SKIP.

    This matches the server's own parsing convention (s.split()[-1]) and
    the client-side construction convention (SKIP as the final token).
    """
    tokens = entry.split()
    return bool(tokens) and tokens[-1] == skip_token


def filter_skip(
    entries: Sequence[T],
    is_skip: Callable[[T], bool] = is_skip_string,
) -> list[T]:
    """
    Return a NEW list with SKIP'd entries removed.

    Deliberately a pure list comprehension: there is no way to express
    the original mutate-while-iterating bug through this function, by
    construction. Never call .remove() on `entries` here or anywhere
    downstream of this module.
    """
    return [e for e in entries if not is_skip(e)]
