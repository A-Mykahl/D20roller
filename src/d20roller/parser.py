"""Parse standard dice notation strings like '2d20+5', '4d6kh3', '1d8+1d6'."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DiceExpr:
    """A single dice group: NdS with optional keep-highest/keep-lowest."""

    count: int
    sides: int
    keep_highest: int | None = None
    keep_lowest: int | None = None

    def __post_init__(self):
        if self.count < 1:
            raise ValueError(f"Dice count must be >= 1, got {self.count}")
        if self.sides < 1:
            raise ValueError(f"Dice sides must be >= 1, got {self.sides}")
        if self.keep_highest is not None and (
            self.keep_highest < 1 or self.keep_highest > self.count
        ):
            raise ValueError(
                f"keep_highest must be between 1 and {self.count}, got {self.keep_highest}"
            )
        if self.keep_lowest is not None and (self.keep_lowest < 1 or self.keep_lowest > self.count):
            raise ValueError(
                f"keep_lowest must be between 1 and {self.count}, got {self.keep_lowest}"
            )


@dataclass(frozen=True)
class Term:
    """A term in a dice expression: either a dice group or a flat modifier."""

    dice: DiceExpr | None = None
    modifier: int | None = None
    sign: int = 1  # +1 or -1

    @property
    def is_dice(self) -> bool:
        return self.dice is not None


@dataclass(frozen=True)
class ParsedRoll:
    """The full parsed result of a dice notation string."""

    raw: str
    terms: list[Term]


# Regex for a single dice term: optional count, 'd', sides, optional keep suffix
_DICE_RE = re.compile(
    r"(\d+)?d(\d+)"
    r"(?:(kh|kl)(\d+))?",
    re.IGNORECASE,
)

# Regex to tokenize the full expression into sign + (dice_or_number)
_TOKEN_RE = re.compile(
    r"([+-])?\s*"
    r"((\d+)?d(\d+)(?:(?:kh|kl)\d+)?|\d+)",
    re.IGNORECASE,
)


def parse(notation: str) -> ParsedRoll:
    """Parse a dice notation string into a ParsedRoll.

    Supported formats:
        2d20        - roll 2 twenty-sided dice
        d6          - roll 1 six-sided die (count defaults to 1)
        4d6kh3      - roll 4d6, keep highest 3
        2d20kl1     - roll 2d20, keep lowest 1
        1d8+1d6+5   - compound expressions with multiple dice and modifiers
        2d6-1       - subtraction
    """
    notation = notation.strip()
    if not notation:
        raise ValueError("Empty dice notation")

    terms: list[Term] = []
    first = True

    for match in _TOKEN_RE.finditer(notation):
        sign_str = match.group(1)
        token = match.group(2)

        if first and sign_str is None:
            sign = 1
        elif sign_str == "-":
            sign = -1
        else:
            sign = 1
        first = False

        dice_match = _DICE_RE.fullmatch(token)
        if dice_match:
            count = int(dice_match.group(1)) if dice_match.group(1) else 1
            sides = int(dice_match.group(2))
            keep_type = dice_match.group(3)
            keep_val = int(dice_match.group(4)) if dice_match.group(4) else None

            kh = keep_val if keep_type and keep_type.lower() == "kh" else None
            kl = keep_val if keep_type and keep_type.lower() == "kl" else None

            terms.append(Term(dice=DiceExpr(count, sides, kh, kl), sign=sign))
        else:
            terms.append(Term(modifier=int(token), sign=sign))

    if not terms:
        raise ValueError(f"Invalid dice notation: {notation!r}")

    return ParsedRoll(raw=notation, terms=terms)
