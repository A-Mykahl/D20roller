"""Tests for the dice roller."""

from d20roller.roller import DiceGroupResult, roll


class TestBasicRolls:
    def test_single_die_in_range(self):
        for _ in range(100):
            result = roll("1d6")
            assert 1 <= result.total <= 6

    def test_multiple_dice_in_range(self):
        for _ in range(100):
            result = roll("3d6")
            assert 3 <= result.total <= 18

    def test_d20_in_range(self):
        for _ in range(100):
            result = roll("1d20")
            assert 1 <= result.total <= 20


class TestSeedReproducibility:
    def test_same_seed_same_result(self):
        r1 = roll("2d20+5", seed=42)
        r2 = roll("2d20+5", seed=42)
        assert r1.total == r2.total

    def test_different_seed_likely_different(self):
        results = {roll("1d100", seed=i).total for i in range(20)}
        assert len(results) > 1  # extremely unlikely all 20 seeds produce the same roll


class TestModifiers:
    def test_positive_modifier(self):
        result = roll("1d1+5")  # 1d1 always rolls 1
        assert result.total == 6

    def test_negative_modifier(self):
        result = roll("1d1-3")
        assert result.total == -2

    def test_multiple_modifiers(self):
        result = roll("1d1+3+2")
        assert result.total == 6


class TestKeepHighestLowest:
    def test_keep_highest(self):
        result = roll("4d6kh3", seed=0)
        dice_part = result.parts[0]
        assert isinstance(dice_part, DiceGroupResult)
        assert len(dice_part.rolls) == 4
        assert len(dice_part.kept) == 3
        assert dice_part.kept == sorted(dice_part.rolls, reverse=True)[:3]

    def test_keep_lowest(self):
        result = roll("2d20kl1", seed=0)
        dice_part = result.parts[0]
        assert isinstance(dice_part, DiceGroupResult)
        assert len(dice_part.rolls) == 2
        assert len(dice_part.kept) == 1
        assert dice_part.kept[0] == min(dice_part.rolls)


class TestCompoundExpressions:
    def test_two_dice_groups_plus_modifier(self):
        result = roll("1d1+1d1+2")
        assert result.total == 4  # 1 + 1 + 2

    def test_subtraction_of_dice(self):
        result = roll("1d1-1d1")
        assert result.total == 0


class TestStringOutput:
    def test_str_contains_total(self):
        result = roll("2d6+3", seed=1)
        output = str(result)
        assert str(result.total) in output
        assert "2d6+3" in output
