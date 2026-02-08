"""Command-line interface for d20roller."""

from __future__ import annotations

import argparse
import sys

from d20roller.roller import roll


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="d20",
        description="Roll dice using standard tabletop RPG notation.",
        epilog="Examples: d20 2d20+5, d20 4d6kh3, d20 1d8+1d6-2",
    )
    parser.add_argument(
        "notation",
        nargs="+",
        help="Dice notation(s) to roll (e.g. 2d20+5, 4d6kh3)",
    )
    parser.add_argument(
        "-r",
        "--repeat",
        type=int,
        default=1,
        metavar="N",
        help="Repeat each roll N times (default: 1)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show individual die results",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    for notation in args.notation:
        for i in range(args.repeat):
            try:
                result = roll(notation)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

            if args.verbose:
                print(result)
            else:
                label = notation
                if args.repeat > 1:
                    label = f"{notation} [{i + 1}]"
                print(f"{label}: {result.total}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
