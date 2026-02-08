# D20roller

A dice roller supporting standard tabletop RPG notation.

## Installation

```bash
pip install -e .
```

## Usage

### Command line

```bash
# Roll a d20
d20 1d20

# Roll 2d6 + 3
d20 2d6+3

# Roll 4d6, keep highest 3 (classic stat generation)
d20 4d6kh3

# Roll with advantage (2d20, keep highest 1)
d20 2d20kh1

# Roll with disadvantage (2d20, keep lowest 1)
d20 2d20kl1

# Compound expressions
d20 1d8+1d6+5

# Repeat a roll 6 times
d20 4d6kh3 -r 6

# Verbose output (show individual dice)
d20 2d20+5 -v
```

### As a library

```python
from d20roller.roller import roll

result = roll("4d6kh3")
print(result.total)   # e.g. 14
print(result)          # e.g. 4d6kh3: 4d6kh3 [~1~, 4, 5, 5] = 14
```

## Dice Notation

| Notation   | Meaning                          |
|------------|----------------------------------|
| `d20`      | Roll 1 twenty-sided die          |
| `2d6`      | Roll 2 six-sided dice            |
| `4d6kh3`   | Roll 4d6, keep highest 3         |
| `2d20kl1`  | Roll 2d20, keep lowest 1         |
| `1d8+5`    | Roll 1d8 and add 5               |
| `1d8+1d6`  | Roll 1d8 and 1d6, sum them       |
| `2d6-1`    | Roll 2d6 and subtract 1          |

## Development

```bash
pip install -e .
pip install pytest ruff

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/

# Format check
ruff format --check src/ tests/
```

## License

MIT
