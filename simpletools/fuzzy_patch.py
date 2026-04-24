"""
Multi-strategy fuzzy find/replace for file patches.

Behavior matches the Hermes/OpenCode-style eight-strategy chain:
exact → line-trimmed → whitespace-normalized → indentation-flexible
→ escape-normalized → trimmed-boundary → block-anchor → context-aware.

Returns (new_text, replacement_count, error_message_or_None).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from difflib import SequenceMatcher

# Smart quotes and invisible-ish characters → ASCII-ish (same mapping idea as Hermes)
_UNICODE_REPLACEMENTS: dict[str, str] = {
    "\u201c": '"',
    "\u201d": '"',
    "\u2018": "'",
    "\u2019": "'",
    "\u2014": "--",
    "\u2013": "-",
    "\u2026": "...",
    "\u00a0": " ",
}


def _normalize_unicode(text: str) -> str:
    for u, asc in _UNICODE_REPLACEMENTS.items():
        text = text.replace(u, asc)
    return text


def _char_span_for_lines(
    lines: list[str], start_line: int, end_line_exclusive: int, total_len: int
) -> tuple[int, int]:
    start_pos = sum(len(line) + 1 for line in lines[:start_line])
    end_pos = sum(len(line) + 1 for line in lines[:end_line_exclusive]) - 1
    end_pos = min(total_len, end_pos)
    return start_pos, end_pos


def _matches_exact(text: str, needle: str) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    pos = 0
    while True:
        i = text.find(needle, pos)
        if i < 0:
            break
        out.append((i, i + len(needle)))
        pos = i + 1
    return out


def _matches_line_trimmed(full: str, needle: str) -> list[tuple[int, int]]:
    full_lines = full.split("\n")
    needle_lines = [ln.strip() for ln in needle.split("\n")]
    needle_norm = "\n".join(needle_lines)
    norm_lines = [ln.strip() for ln in full_lines]
    return _sliding_block_match(full, full_lines, norm_lines, needle_norm)


def _sliding_block_match(
    full: str,
    orig_lines: list[str],
    norm_lines: list[str],
    needle_norm: str,
) -> list[tuple[int, int]]:
    n = len(needle_norm.split("\n"))
    hits: list[tuple[int, int]] = []
    for i in range(len(norm_lines) - n + 1):
        block = "\n".join(norm_lines[i : i + n])
        if block == needle_norm:
            s, e = _char_span_for_lines(orig_lines, i, i + n, len(full))
            hits.append((s, e))
    return hits


def _matches_ws_collapsed(full: str, needle: str) -> list[tuple[int, int]]:

    def collapse(s: str) -> str:
        return re.sub(r"[ \t]+", " ", s)

    nf = collapse(full)
    nn = collapse(needle)
    raw_hits = _matches_exact(nf, nn)
    if not raw_hits:
        return []
    return _map_ws_collapsed_positions(full, nf, raw_hits)


def _map_ws_collapsed_positions(
    original: str, normalized: str, hits: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    o2n: list[int] = []
    oi = ni = 0
    while oi < len(original) and ni < len(normalized):
        if original[oi] == normalized[ni]:
            o2n.append(ni)
            oi += 1
            ni += 1
        elif original[oi] in " \t" and normalized[ni] == " ":
            o2n.append(ni)
            oi += 1
            if oi >= len(original) or original[oi] not in " \t":
                ni += 1
        elif original[oi] in " \t":
            o2n.append(ni)
            oi += 1
        else:
            o2n.append(ni)
            oi += 1
    while oi < len(original):
        o2n.append(len(normalized))
        oi += 1
    norm_to_start: dict[int, int] = {}
    norm_to_end: dict[int, int] = {}
    for op, np in enumerate(o2n):
        norm_to_start.setdefault(np, op)
        norm_to_end[np] = op
    mapped: list[tuple[int, int]] = []
    for ns, ne in hits:
        os_ = norm_to_start.get(ns, min(i for i, n in enumerate(o2n) if n >= ns))
        if ne - 1 in norm_to_end:
            oe = norm_to_end[ne - 1] + 1
        else:
            oe = os_ + max(1, ne - ns)
        while oe < len(original) and original[oe] in " \t":
            oe += 1
        mapped.append((os_, min(oe, len(original))))
    return mapped


def _matches_indent_flex(full: str, needle: str) -> list[tuple[int, int]]:
    full_lines = full.split("\n")
    norm_lines = [ln.lstrip() for ln in full_lines]
    needle_norm = "\n".join(ln.lstrip() for ln in needle.split("\n"))
    return _sliding_block_match(full, full_lines, norm_lines, needle_norm)


def _matches_escape_literal(full: str, needle: str) -> list[tuple[int, int]]:
    unescaped = needle.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
    if unescaped == needle:
        return []
    return _matches_exact(full, unescaped)


def _matches_trimmed_ends(full: str, needle: str) -> list[tuple[int, int]]:
    pl = needle.split("\n")
    if not pl:
        return []
    pl[0] = pl[0].strip()
    if len(pl) > 1:
        pl[-1] = pl[-1].strip()
    mod = "\n".join(pl)
    fl = full.split("\n")
    hits: list[tuple[int, int]] = []
    k = len(pl)
    for i in range(len(fl) - k + 1):
        block = fl[i : i + k]
        bl = block.copy()
        bl[0] = bl[0].strip()
        if len(bl) > 1:
            bl[-1] = bl[-1].strip()
        if "\n".join(bl) == mod:
            s, e = _char_span_for_lines(fl, i, i + k, len(full))
            hits.append((s, e))
    return hits


def _matches_block_anchor(full: str, needle: str) -> list[tuple[int, int]]:
    pn = _normalize_unicode(needle)
    cn = _normalize_unicode(full)
    pl = pn.split("\n")
    if len(pl) < 2:
        return []
    first, last = pl[0].strip(), pl[-1].strip()
    nlines = pl
    cn_lines = cn.split("\n")
    o_lines = full.split("\n")
    k = len(nlines)
    candidates = [
        i
        for i in range(len(cn_lines) - k + 1)
        if cn_lines[i].strip() == first and cn_lines[i + k - 1].strip() == last
    ]
    mult = len(candidates)
    threshold = 0.10 if mult == 1 else 0.30
    hits: list[tuple[int, int]] = []
    for i in candidates:
        if k <= 2:
            sim = 1.0
        else:
            mid_c = "\n".join(cn_lines[i + 1 : i + k - 1])
            mid_p = "\n".join(nlines[1:-1])
            sim = SequenceMatcher(None, mid_c, mid_p).ratio()
        if sim >= threshold:
            s, e = _char_span_for_lines(o_lines, i, i + k, len(full))
            hits.append((s, e))
    return hits


def _matches_context_lines(full: str, needle: str) -> list[tuple[int, int]]:
    pl = needle.split("\n")
    fl = full.split("\n")
    if not pl:
        return []
    k = len(pl)
    hits: list[tuple[int, int]] = []
    for i in range(len(fl) - k + 1):
        block = fl[i : i + k]
        hi = 0
        for a, b in zip(pl, block, strict=True):
            if SequenceMatcher(None, a.strip(), b.strip()).ratio() >= 0.80:
                hi += 1
        if hi >= len(pl) * 0.5:
            s, e = _char_span_for_lines(fl, i, i + k, len(full))
            hits.append((s, e))
    return hits


def _apply_at_spans(text: str, spans: Sequence[tuple[int, int]], replacement: str) -> str:
    out = text
    for start, end in sorted(spans, key=lambda x: x[0], reverse=True):
        out = out[:start] + replacement + out[end:]
    return out


_STRATEGIES: list[tuple[str, Callable[[str, str], list[tuple[int, int]]]]] = [
    ("exact", _matches_exact),
    ("line_trimmed", _matches_line_trimmed),
    ("whitespace_normalized", _matches_ws_collapsed),
    ("indentation_flexible", _matches_indent_flex),
    ("escape_normalized", _matches_escape_literal),
    ("trimmed_boundary", _matches_trimmed_ends),
    ("block_anchor", _matches_block_anchor),
    ("context_aware", _matches_context_lines),
]


def fuzzy_find_and_replace(
    content: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> tuple[str, int, str | None]:
    if not old_string:
        return content, 0, "old_string cannot be empty"
    if old_string == new_string:
        return content, 0, "old_string and new_string are identical"

    for _name, strat in _STRATEGIES:
        spans = strat(content, old_string)
        if not spans:
            continue
        if len(spans) > 1 and not replace_all:
            return (
                content,
                0,
                (
                    f"Found {len(spans)} matches for old_string. "
                    "Add more surrounding context or set replace_all=True."
                ),
            )
        new_content = _apply_at_spans(content, spans, new_string)
        return new_content, len(spans), None

    return content, 0, "Could not find a match for old_string in the file"
