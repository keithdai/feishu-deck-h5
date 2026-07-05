#!/usr/bin/env python3
"""Preflight checks for the deck-library skill."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def default_renderer_root() -> Path:
    return Path(__file__).resolve().parents[2] / "feishu-deck-h5"


def build_report(renderer_root: Path) -> dict[str, object]:
    render_deck = renderer_root / "deck-json" / "render-deck.py"
    deck_cli = renderer_root / "deck-json" / "deck-cli.py"
    validator = renderer_root / "assets" / "validate.py"
    lark_cli = shutil.which("lark-cli")

    required = {
        "renderer_root": renderer_root,
        "render_deck": render_deck,
        "deck_cli": deck_cli,
        "validator": validator,
    }
    missing = [name for name, path in required.items() if not Path(path).exists()]

    return {
        "ok": not missing,
        "missing": missing,
        "paths": {name: str(path) for name, path in required.items()},
        "optional": {
            "lark_cli": lark_cli,
            "lark_cli_available": bool(lark_cli),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check deck-library local dependencies.")
    parser.add_argument(
        "--renderer-root",
        type=Path,
        default=default_renderer_root(),
        help="Path to skills/feishu-deck-h5. Defaults to sibling skill directory.",
    )
    args = parser.parse_args()

    report = build_report(args.renderer_root.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
