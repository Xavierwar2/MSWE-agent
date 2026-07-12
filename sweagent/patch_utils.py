from __future__ import annotations

import re
from collections.abc import Iterable

from unidiff import PatchSet


_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+?) b/(.+)$")


def _normalize_patch_path(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        path = path[2:]
    return path.strip()


def _iter_file_diffs(patch: str) -> Iterable[tuple[set[str], list[str]]]:
    current_lines: list[str] = []
    current_paths: set[str] = set()

    for line in patch.splitlines(keepends=True):
        match = _DIFF_HEADER_RE.match(line.rstrip("\n"))
        if match:
            if current_lines:
                yield current_paths, current_lines
            current_paths = {_normalize_patch_path(match.group(1)), _normalize_patch_path(match.group(2))}
            current_lines = [line]
        elif current_lines:
            current_lines.append(line)

    if current_lines:
        yield current_paths, current_lines


def paths_from_patch(patch: str | None) -> set[str]:
    """Return normalized file paths touched by a unified diff."""
    if not patch:
        return set()
    try:
        return {_normalize_patch_path(file.path) for file in PatchSet(patch)}
    except Exception:
        paths: set[str] = set()
        for file_paths, _ in _iter_file_diffs(patch):
            paths.update(file_paths)
        return paths


def sanitize_model_patch(
    patch: str | None,
    *,
    exclude_paths: Iterable[str] = (),
    exclude_root_gitignore: bool = True,
) -> str | None:
    """Remove benchmark/environment-only file diffs from a model patch.

    Multi-SWE-Bench applies the benchmark test patch before the model fix patch.
    If the model patch also contains edits to those benchmark test files, git can
    fail before tests run. The harness can also mutate the root .gitignore during
    setup, which should not be submitted as part of a fix.
    """
    if patch is None:
        return None

    normalized_excludes = {_normalize_patch_path(path) for path in exclude_paths}
    kept_blocks: list[str] = []

    for file_paths, lines in _iter_file_diffs(patch.lstrip("\n")):
        if file_paths & normalized_excludes:
            continue
        if exclude_root_gitignore and ".gitignore" in file_paths:
            continue
        kept_blocks.append("".join(lines))

    sanitized = "".join(kept_blocks).lstrip("\n")
    return sanitized or None
