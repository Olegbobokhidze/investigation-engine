"""Fails when the documentation names something that doesn't exist.

Checks every Markdown file in the repository (outside dependency folders) for:
- relative links, `[text](path)`, whose target file is missing;
- repository paths in backticks, like `apps/api/src/...` or `docs/...`;
- `make <target>` in code with no such target in the Makefile;
- `ADR-0007` with no matching file in docs/decisions/.

Run with `make docs-check` (CI does too). Standard library only, so it needs no install.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIPPED_DIRS = {"node_modules", ".venv", ".git", "dist", ".claude", "data"}
# Paths in backticks are checked when they start at one of these top-level folders.
PATH_ROOTS = ("apps/", "docs/", ".github/", "scripts/")
# Paths inside the backend package, as docs/requirements.md writes them.
PACKAGE = ROOT / "apps/api/src/investigation_engine"
PACKAGE_DIRS = {path.name + "/" for path in PACKAGE.iterdir() if path.is_dir()}

LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
CODE = re.compile(r"`([^`\n]+)`")
FENCED_BLOCK = re.compile(r"```.*?```", flags=re.DOTALL)
# A whole target name; "make api-*" is a wildcard, not a target.
MAKE_TARGET = re.compile(r"\bmake ([a-z][a-z-]*[a-z])\b(?![-*])")
ADR = re.compile(r"ADR-(\d{4})")


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if not SKIPPED_DIRS.intersection(path.relative_to(ROOT).parts)
    )


def make_targets() -> set[str]:
    makefile = (ROOT / "Makefile").read_text()
    return set(re.findall(r"^([a-z][a-z-]+):", makefile, flags=re.MULTILINE))


def adr_ids() -> set[str]:
    return {path.name[:4] for path in (ROOT / "docs/decisions").glob("[0-9]*.md")}


def is_git_ignored(path: str) -> bool:
    result = subprocess.run(["git", "check-ignore", "--quiet", path], cwd=ROOT, check=False)
    return result.returncode == 0


def code_path_exists(code: str) -> bool | None:
    """True or False for something that looks like a repository path, None otherwise."""
    path = code.rstrip("/").split(":")[0]  # "file.py:42" names a line in file.py
    if " " in code or "*" in code:
        return None
    if code.startswith(PATH_ROOTS):
        if is_git_ignored(path):
            # Local-only files (`apps/api/.env`) exist on a laptop but never in CI.
            return None
        return (ROOT / path).exists()
    if code.startswith(tuple(PACKAGE_DIRS)) and path.endswith(".py"):
        return (PACKAGE / path).exists()
    return None


def problems_in(path: Path, targets: set[str], adrs: set[str]) -> list[str]:
    text = path.read_text()
    found: list[str] = []
    for target in LINK.findall(text):
        if "://" not in target and not target.startswith("mailto:"):
            if not (path.parent / target).resolve().exists():
                found.append(f"broken link: {target}")
    code_spans = CODE.findall(FENCED_BLOCK.sub("", text))
    for code in code_spans:
        if code_path_exists(code) is False:
            found.append(f"missing path: {code}")
    code_text = "\n".join([*FENCED_BLOCK.findall(text), *code_spans])
    for target in MAKE_TARGET.findall(code_text):
        if target not in targets:
            found.append(f"unknown make target: make {target}")
    for adr in ADR.findall(text):
        if adr not in adrs:
            found.append(f"unknown decision: ADR-{adr}")
    return found


def main() -> int:
    targets, adrs = make_targets(), adr_ids()
    failures = 0
    for path in markdown_files():
        for problem in problems_in(path, targets, adrs):
            print(f"{path.relative_to(ROOT)}: {problem}")
            failures += 1
    if failures:
        print(f"\n{failures} stale reference(s) in the docs.")
        return 1
    print(f"Docs check passed ({len(markdown_files())} files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
