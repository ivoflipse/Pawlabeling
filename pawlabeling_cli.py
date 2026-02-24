"""Minimal command-line entry point for Pawlabeling."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import pathlib
import re
import sys


def _read_version_from_source() -> str:
    init_path = pathlib.Path(__file__).with_name("pawlabeling") / "__init__.py"
    if not init_path.exists():
        return "0.0.0"
    content = init_path.read_text(encoding="utf-8")
    match = re.search(r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", content, re.M)
    return match.group(1) if match else "0.0.0"


def get_version() -> str:
    try:
        return metadata.version("pawlabeling")
    except metadata.PackageNotFoundError:
        return _read_version_from_source()


def run_gui() -> int:
    try:
        from pawlabeling.widgets.mainwindow import main
    except Exception as exc:  # pragma: no cover - GUI path depends on optional deps
        print("Unable to start GUI:", exc, file=sys.stderr)
        return 1
    main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pawlabeling",
        description="Pawlabeling command-line entry point.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the GUI (requires optional dependencies).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(get_version())
        return 0

    if args.gui:
        return run_gui()

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
