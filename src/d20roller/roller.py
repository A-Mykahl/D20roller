"""Roll dice based on parsed expressions and return structured results."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from d20roller.parser import DiceExpr, ParsedRoll, Term, parse


@dataclass
class DiceGroupResult:
    """Result of rolling a single dice group (e.g. 4d6kh3)."""

    expr: DiceExpr
    rolls: list[int]
    kept: list[int]
    sign: int

    @property
    def total(self) -> int:
        return self.sign * sum(self.kept)

    def __str__(self) -> str:
        sign = "-" if self.sign < 0 else ""
        notation = f"{self.expr.count}d{self.expr.sides}"
        if self.expr.keep_highest:
            notation += f"kh{self.expr.keep_highest}"
        elif self.expr.keep_lowest:
            notation += f"kl{self.expr.keep_lowest}"

        if self.rolls != self.kept:
            dropped = sorted(set(range(len(self.rolls))) - set(self._kept_indices()))
            parts = []
            for i, r in enumerate(self.rolls):
                if i in dropped:
                    parts.append(f"~{r}~")
                else:
                    parts.append(str(r))
            return f"{sign}{notation} [{', '.join(parts)}]"
        return f"{sign}{notation} {self.rolls}"

    def _kept_indices(self) -> list[int]:
        indexed = sorted(enumerate(self.rolls), key=lambda x: x[1], reverse=True)
        keep = self.expr.keep_highest or self.expr.keep_lowest or self.expr.count
        if self.expr.keep_lowest:
            indexed = sorted(enumerate(self.rolls), key=lambda x: x[1])
        return sorted(i for i, _ in indexed[:keep])


@dataclass
class ModifierResult:
    """Result of a flat modifier term."""

    value: int
    sign: int

    @property
    def total(self) -> int:
        return self.sign * self.value

    def __str__(self) -> str:
        return str(self.total)


@dataclass
class RollResult:
    """Complete result of evaluating a dice notation string."""

    parsed: ParsedRoll
    parts: list[DiceGroupResult | ModifierResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(p.total for p in self.parts)

    def __str__(self) -> str:
        detail_parts = []
        for i, part in enumerate(self.parts):
            s = str(part)
            if i > 0 and not s.startswith("-"):
                s = f"+ {s}"
            elif i > 0:
                s = f"- {s.lstrip('-')}"
            detail_parts.append(s)
        detail = " ".join(detail_parts)
        return f"{self.parsed.raw}: {detail} = {self.total}"


def _roll_dice_group(term: Term, rng: random.Random) -> DiceGroupResult:
    expr = term.dice
    rolls = [rng.randint(1, expr.sides) for _ in range(expr.count)]

    if expr.keep_highest:
        kept = sorted(rolls, reverse=True)[: expr.keep_highest]
    elif expr.keep_lowest:
        kept = sorted(rolls)[: expr.keep_lowest]
    else:
        kept = list(rolls)

    return DiceGroupResult(expr=expr, rolls=rolls, kept=kept, sign=term.sign)


def roll(notation: str, *, seed: int | None = None) -> RollResult:
    """Parse and roll a dice notation string.

    Args:
        notation: A dice notation string like '2d20+5'.
        seed: Optional RNG seed for reproducible results (useful in tests).

    Returns:
        A RollResult with individual rolls and the total.
    """
    parsed = parse(notation)
    rng = random.Random(seed)
    result = RollResult(parsed=parsed)

    for term in parsed.terms:
        if term.is_dice:
            result.parts.append(_roll_dice_group(term, rng))
        else:
            result.parts.append(ModifierResult(value=term.modifier, sign=term.sign))

    return result
