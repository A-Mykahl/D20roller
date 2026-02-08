"""Tests for the dice notation parser."""

import pytest

from d20roller.parser import DiceExpr, parse


class TestBasicNotation:
    def test_simple_die(self):
        result = parse("d20")
        assert len(result.terms) == 1
        assert result.terms[0].dice == DiceExpr(count=1, sides=20)

    def test_multiple_dice(self):
        result = parse("2d6")
        assert result.terms[0].dice == DiceExpr(count=2, sides=6)

    def test_large_count_and_sides(self):
        result = parse("10d100")
        assert result.terms[0].dice == DiceExpr(count=10, sides=100)


class TestKeepHighestLowest:
    def test_keep_highest(self):
        result = parse("4d6kh3")
        expr = result.terms[0].dice
        assert expr.count == 4
        assert expr.sides == 6
        assert expr.keep_highest == 3

    def test_keep_lowest(self):
        result = parse("2d20kl1")
        expr = result.terms[0].dice
        assert expr.count == 2
        assert expr.sides == 20
        assert expr.keep_lowest == 1


class TestCompoundExpressions:
    def test_dice_plus_modifier(self):
        result = parse("1d8+5")
        assert len(result.terms) == 2
        assert result.terms[0].is_dice
        assert result.terms[1].modifier == 5
        assert result.terms[1].sign == 1

    def test_dice_minus_modifier(self):
        result = parse("1d6-2")
        assert len(result.terms) == 2
        assert result.terms[1].modifier == 2
        assert result.terms[1].sign == -1

    def test_multiple_dice_groups(self):
        result = parse("1d8+1d6+3")
        assert len(result.terms) == 3
        assert result.terms[0].dice.sides == 8
        assert result.terms[1].dice.sides == 6
        assert result.terms[2].modifier == 3


class TestValidation:
    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Empty"):
            parse("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="Empty"):
            parse("   ")

    def test_invalid_notation_raises(self):
        with pytest.raises(ValueError, match="Invalid"):
            parse("abc")

    def test_keep_more_than_count_raises(self):
        with pytest.raises(ValueError, match="keep_highest"):
            parse("2d6kh5")

    def test_zero_sides_raises(self):
        with pytest.raises(ValueError, match="sides"):
            parse("1d0")

    def test_zero_count_raises(self):
        with pytest.raises(ValueError, match="count"):
            parse("0d6")
