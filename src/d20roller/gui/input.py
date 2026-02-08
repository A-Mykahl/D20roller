"""Press-and-hold + mouse shake detection for triggering dice rolls."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ShakeDetector:
    """Track mouse motion while pressed and detect shake gestures.

    Usage:
        detector = ShakeDetector()
        # On mouse button press:
        detector.press()
        # On mouse motion while pressed:
        if detector.feed(x, y):
            do_roll()
        # On mouse button release:
        detector.release()
    """

    threshold: float = 300.0  # cumulative px movement over the window to trigger
    window_sec: float = 0.3  # time window for energy accumulation
    cooldown_sec: float = 0.7  # minimum gap between shake-triggered rolls

    _pressed: bool = field(default=False, init=False)
    _samples: list[tuple[float, float, float]] = field(default_factory=list, init=False)
    _last_trigger: float = field(default=0.0, init=False)

    def press(self) -> None:
        """Call when the mouse button is pressed down."""
        self._pressed = True
        self._samples.clear()

    def release(self) -> None:
        """Call when the mouse button is released."""
        self._pressed = False
        self._samples.clear()

    @property
    def is_pressed(self) -> bool:
        return self._pressed

    def feed(self, x: float, y: float) -> bool:
        """Feed a mouse-motion sample. Returns True if a shake roll should trigger.

        Should be called on every <Motion> event while the button is held.
        """
        if not self._pressed:
            return False

        now = time.monotonic()
        self._samples.append((now, x, y))

        # Prune samples outside the time window
        cutoff = now - self.window_sec
        self._samples = [(t, sx, sy) for t, sx, sy in self._samples if t >= cutoff]

        if len(self._samples) < 3:
            return False

        energy = self._compute_energy()

        if energy >= self.threshold and (now - self._last_trigger) >= self.cooldown_sec:
            self._last_trigger = now
            self._samples.clear()
            return True

        return False

    def _compute_energy(self) -> float:
        """Sum of absolute deltas across recent samples."""
        total = 0.0
        for i in range(1, len(self._samples)):
            _, x0, y0 = self._samples[i - 1]
            _, x1, y1 = self._samples[i]
            total += abs(x1 - x0) + abs(y1 - y0)
        return total

    def reset(self) -> None:
        """Fully reset state."""
        self._pressed = False
        self._samples.clear()
        self._last_trigger = 0.0
